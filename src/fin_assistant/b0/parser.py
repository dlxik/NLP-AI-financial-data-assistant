"""Bộ phân tích quy tắc B0: câu hỏi tiếng Việt → :class:`~fin_assistant.semantic.Query`.

Trình tự (mỗi bước "tiêu thụ" đoạn đã khớp để bước sau không khớp lại):

1. Mã cổ phiếu (viết hoa / mã đã biết / tên gọi trong bảng công ty).
2. Số lượng top-N; nhóm mã (ngân hàng, VN30…).
3. Kỳ: TTM, lũy kế (n tháng, bán niên), quý–năm, quý không năm, năm, "gần nhất".
4. Điều kiện lọc (so sánh + số + đơn vị) và dấu (âm/dương).
5. Phép so sánh thời gian (QoQ / YoY / "tăng trưởng"), điểm % vs %.
6. Chỉ số (từ vựng quy tắc; mơ hồ → mặc định hoặc hỏi làm rõ theo chính sách).
7. Xếp hạng (cao nhất / thấp nhất / top-N / xếp hạng).

Nguyên tắc: **không đoán khi không hiểu** — câu có chỉ số ngoài danh mục, nhiều chỉ số, nhiều kỳ
không quy được về YoY/QoQ, hoặc không xác định được mã → B0 từ chối có lý do (``NOT_APPLICABLE``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from ..semantic.catalog import METRICS, MetricDef
from ..semantic.periods import LATEST, Period, to_date
from ..semantic.query import Query
from ..semantic.result import Status
from ..semantic.store import FactStore
from . import lexicon as lx
from .normalize import normalize, parse_number

POLICIES = ("default", "clarify")


class _Unsupported(Exception):
    """B0 không biểu đạt được câu hỏi."""


@dataclass
class ParseResult:
    question: str
    query: Query | None = None
    status: Status | None = None  # None = có truy vấn để chạy; khác None = dừng ở lớp hiểu câu
    reason: str | None = None
    candidates: tuple[str, ...] = ()
    assumptions: list[str] = field(default_factory=list)
    trace: dict = field(default_factory=dict)


class _Buffer:
    """Văn bản đã chuẩn hóa; đoạn đã khớp được thay bằng khoảng trắng (giữ nguyên vị trí)."""

    def __init__(self, text: str) -> None:
        self.text = text

    def take(self, pattern: re.Pattern[str]) -> list[re.Match[str]]:
        matches = list(pattern.finditer(self.text))
        for m in matches:
            self.text = self.text[: m.start()] + " " * (m.end() - m.start()) + self.text[m.end():]
        return matches

    def first(self, pattern: re.Pattern[str]) -> re.Match[str] | None:
        found = self.take(pattern)
        return found[0] if found else None


@dataclass
class _PeriodSpec:
    kind: str = "implicit_latest"  # implicit_latest | latest | quarter | ytd | fy | ttm
    year: int | None = None
    quarter: int | None = None
    extra: list[Period] = field(default_factory=list)  # kỳ thứ hai (vd "Q3/2024 so với Q3/2023")
    ttm: bool = False


def _quarter(token: str) -> int:
    return int(token) if token.isdigit() else lx.ROMAN[token]


class B0Parser:
    def __init__(self, store: FactStore, policy: str = "default") -> None:
        if policy not in POLICIES:
            raise ValueError(f"policy phải thuộc {POLICIES}")
        self.store = store
        self.policy = policy
        self._known = store.tickers()
        self._aliases = sorted(((normalize(a), t) for a, t in store.aliases().items()),
                               key=lambda x: -len(x[0]))

    # ------------------------------------------------------------------ API
    def parse(self, question: str, question_date: date | str | None = None) -> ParseResult:
        out = ParseResult(question=question)
        as_of = to_date(question_date)
        buf = _Buffer(normalize(question))
        try:
            tickers = self._tickers(question, buf)
            top_n = self._top_n(buf)
            universe = self._universe(buf)
            pspec = self._periods(buf)
            cmp_, threshold_raw = self._screen(buf, normalize(question))
            change, pp, percent_word = self._change(buf, pspec)
            metric = self._metric(question, buf, out)
            if metric is None:
                return out  # hỏi làm rõ chỉ số
            order, is_rank, rank_all = self._rank(buf, top_n)
            mdef = METRICS[metric]
            out.trace.update(tickers=tickers, universe=universe, metric=metric, period=pspec.__dict__,
                             change=change, cmp=cmp_, rank=is_rank)

            window, period = self._resolve_period(mdef, pspec, tickers, as_of, out)
            transform = self._transform(mdef, window, change, pp, percent_word, out)

            if cmp_ is not None:
                op = "screen"
            elif is_rank:
                op = "rank"
            else:
                op = "lookup"
            if not tickers and universe is None:
                if op == "lookup":
                    raise _Unsupported("không xác định được mã cổ phiếu trong câu hỏi")
                universe = "all"
                out.assumptions.append("xét toàn bộ các mã trong danh mục VN30 của dữ liệu")
            threshold = None
            if cmp_ is not None:
                threshold = self._threshold(mdef, transform, threshold_raw, out)

            out.query = Query(
                op=op,
                metric=metric,
                tickers=tuple(tickers),
                universe=None if tickers else universe,
                period=period,
                transform=transform,
                order=order,
                top_n=(top_n or (None if rank_all else 1)) if op == "rank" else None,
                cmp=cmp_,
                threshold=threshold,
                as_of=as_of.isoformat() if as_of else None,
                assumptions=tuple(out.assumptions),
            )
            out.query.validate()
        except _Unsupported as exc:
            out.query = None
            out.status = Status.NOT_APPLICABLE
            out.reason = str(exc)
        return out

    # ------------------------------------------------------------------ bước 1–2
    def _tickers(self, question: str, buf: _Buffer) -> list[str]:
        """Mã viết hoa trong câu (kể cả mã ngoài danh mục → sẽ bị từ chối có lý do); mã viết thường
        chỉ nhận khi cả câu viết thường (tránh "nhà" → NHA); tên gọi lấy từ cột aliases."""
        found: list[tuple[int, str]] = []
        candidates = {t for t in lx.TICKER_RE.findall(question) if t not in lx.NOT_TICKERS}
        if question == question.lower():
            candidates |= set(self._known)
        for t in sorted(candidates):
            pattern = re.compile(rf"(?<![a-z0-9]){re.escape(t.lower())}(?![a-z0-9])")
            found += [(m.start(), t) for m in buf.take(pattern)]
        for alias, t in self._aliases:
            for m in buf.take(re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])")):
                found.append((m.start(), t))
        ordered: list[str] = []
        for _, t in sorted(found):
            if t not in ordered:
                ordered.append(t)
        return ordered

    @staticmethod
    def _top_n(buf: _Buffer) -> int | None:
        m = buf.first(lx.TOP_N_RE)
        if not m:
            return None
        n = int(m.group(1) or m.group(2))
        return n if n >= 1 else None

    @staticmethod
    def _universe(buf: _Buffer) -> str | None:
        for pattern, name in lx.UNIVERSE_PATTERNS:
            if buf.take(pattern):
                return name
        return None

    # ------------------------------------------------------------------ bước 3: kỳ
    @staticmethod
    def _periods(buf: _Buffer) -> _PeriodSpec:
        spec = _PeriodSpec()
        spec.ttm = bool(buf.take(lx.TTM_RE))
        ytd_word = bool(buf.take(lx.YTD_WORD_RE))

        half = buf.first(lx.HALF_YEAR_RE)
        months = None if half else buf.first(lx.YTD_MONTHS_RE)
        quarters = [Period(int(m.group(2)), _quarter(m.group(1))) for m in buf.take(lx.QUARTER_YEAR_RE)]
        quarters += [Period(int(m.group(1)), int(m.group(2))) for m in buf.take(lx.YEAR_QUARTER_RE)]
        q_only = buf.first(lx.QUARTER_ONLY_RE)
        years = [int(m.group(1)) for m in buf.take(lx.YEAR_RE)] or [int(m.group(1)) for m in buf.take(lx.BARE_YEAR_RE)]
        latest = bool(buf.take(lx.LATEST_RE))

        if half or months:
            spec.kind = "ytd"
            if half:
                spec.quarter, y = 2, half.group(1)
            else:
                assert months is not None
                token = months.group(1)
                spec.quarter = (int(token) if token.isdigit() else lx.MONTHS_WORDS[token]) // 3
                y = months.group(2)
            spec.year = int(y) if y else (years[0] if years else None)
        elif quarters:
            quarters = sorted(set(quarters), reverse=True)
            spec.kind = "ytd" if ytd_word else "quarter"
            spec.year, spec.quarter = quarters[0].year, quarters[0].quarter
            spec.extra = quarters[1:]
        elif q_only:
            spec.kind = "ytd" if ytd_word else "quarter"
            spec.quarter = _quarter(q_only.group(1))
            spec.year = years[0] if years else None
        elif years:
            spec.kind = "fy"
            spec.year, spec.quarter = years[0], 4
            spec.extra = [Period(y, 4) for y in sorted(set(years[1:]), reverse=True)]
        elif spec.ttm:
            spec.kind = "ttm"
        elif latest:
            spec.kind = "latest"
        return spec

    # ------------------------------------------------------------------ bước 4: lọc
    @staticmethod
    def _screen(buf: _Buffer, full_text: str) -> tuple[str | None, tuple[float, str | None] | None]:
        m = buf.first(lx.COMP_RE)
        if m:
            return lx.COMP_OPS[m.group("op")], (parse_number(m.group("num")), m.group("unit"))
        if lx.SCREEN_CUE_RE.search(full_text):  # từ gợi ý có thể đã bị bước nhóm mã tiêu thụ
            sign = buf.first(lx.SIGN_RE)
            if sign:
                return ("<" if sign.group(1) == "am" else ">"), (0.0, "sign")
        return None, None

    # ------------------------------------------------------------------ bước 5: so sánh
    @staticmethod
    def _change(buf: _Buffer, pspec: _PeriodSpec) -> tuple[str | None, bool, bool]:
        pp = bool(buf.take(lx.PP_RE))
        percent_word = bool(buf.take(lx.PERCENT_WORD_RE))
        if buf.take(lx.QOQ_RE):
            change = "qoq"
        elif buf.take(lx.YOY_RE):
            change = "yoy"
        elif buf.take(lx.CHANGE_RE):
            change = "generic"
        else:
            change = None
        if pspec.extra:  # hai kỳ: quy về YoY / QoQ nếu đúng độ lệch
            main = Period(pspec.year, pspec.quarter)  # type: ignore[arg-type]
            other = pspec.extra[0]
            lag = main.index - other.index
            if len(pspec.extra) > 1 or lag not in (1, 4):
                raise _Unsupported("B0 chỉ so sánh hai kỳ liền kề (QoQ) hoặc cùng kỳ năm trước (YoY)")
            if pspec.kind == "ytd" and lag == 1:
                raise _Unsupported("lũy kế chỉ so sánh với cùng kỳ năm trước")
            change = "qoq" if lag == 1 else "yoy"
        return change, pp, percent_word

    # ------------------------------------------------------------------ bước 6: chỉ số
    def _metric(self, question: str, buf: _Buffer, out: ParseResult) -> str | None:
        hits: list[tuple[int, lx.MetricPattern | str]] = []
        for pattern, target in lx.CASE_SENSITIVE_METRICS:
            for m in pattern.finditer(question):
                hits.append((m.start(), target))
        for mp in lx.METRIC_PATTERNS:
            for m in buf.take(mp.pattern):
                hits.append((m.start(), mp))
        targets: list[lx.MetricPattern | str] = []
        for _, h in sorted(hits, key=lambda x: x[0]):
            key = h if isinstance(h, str) else h.target
            if key not in [t if isinstance(t, str) else t.target for t in targets]:
                targets.append(h)
        if not targets:
            raise _Unsupported("không nhận diện được chỉ số trong danh mục")
        unsupported = [t for t in targets if not isinstance(t, str) and t.target == lx.UNSUPPORTED]
        if unsupported:
            raise _Unsupported(f"câu hỏi về {unsupported[0].label} — B0 chỉ hỗ trợ các chỉ số trong danh mục")
        if len(targets) > 1:
            names = ", ".join(t if isinstance(t, str) else t.target for t in targets)
            raise _Unsupported(f"B0 chỉ hỗ trợ một chỉ số mỗi câu (nhận diện được: {names})")
        hit = targets[0]
        if isinstance(hit, str):
            return hit
        if hit.target in lx.AMBIGUITIES:
            amb = lx.AMBIGUITIES[hit.target]
            if amb["default"] is None or self.policy == "clarify":
                out.status = Status.NEEDS_CLARIFICATION
                out.candidates = tuple(amb["candidates"])
                out.reason = amb["question"]
                return None
            out.assumptions.append(amb["assumption"])
            return amb["default"]
        if hit.assumption:
            out.assumptions.append(hit.assumption)
        return hit.target

    # ------------------------------------------------------------------ bước 7: xếp hạng
    @staticmethod
    def _rank(buf: _Buffer, top_n: int | None) -> tuple[str, bool, bool]:
        """(thứ tự, có xếp hạng?, xếp hạng toàn bộ?)."""
        rank_all = bool(buf.take(lx.RANK_ALL_RE))
        if buf.take(lx.ASC_RE):
            return "asc", True, rank_all
        if buf.take(lx.DESC_RE):
            return "desc", True, rank_all
        return "desc", rank_all or top_n is not None, rank_all

    # ------------------------------------------------------------------ dựng truy vấn
    def _resolve_year(self, quarter: int, tickers: list[str], as_of: date | None, out: ParseResult) -> int:
        pool = tickers or self._known
        years = [p.year for t in pool for p in self.store.published_periods(t, as_of) if p.quarter == quarter]
        if years:
            year = max(years)
        else:
            ref = as_of or date.today()
            year = ref.year if Period(ref.year, quarter).end_date() < ref else ref.year - 1
        out.assumptions.append(f"câu hỏi không nêu năm — hiểu là quý {quarter}/{year} (gần nhất đã công bố)")
        return year

    def _resolve_period(self, mdef: MetricDef, spec: _PeriodSpec, tickers: list[str],
                        as_of: date | None, out: ParseResult) -> tuple[str, str]:
        """Trả (cửa sổ, kỳ) phù hợp với loại chỉ số."""
        if spec.kind in ("quarter", "ytd") and spec.year is None:
            spec.year = self._resolve_year(spec.quarter or 4, tickers, as_of, out)
        period = LATEST if spec.kind in ("implicit_latest", "latest", "ttm") else str(Period(spec.year, spec.quarter))  # type: ignore[arg-type]
        if spec.kind == "implicit_latest":
            out.assumptions.append("câu hỏi không nêu kỳ — dùng kỳ gần nhất đã công bố tại ngày hỏi")

        kind = mdef.kind
        if spec.ttm or spec.kind == "ttm":
            if kind in ("flow", "ratio_window"):
                return "ttm", period
            if kind == "ratio_ttm":
                return "q", period
            raise _Unsupported(f"'{mdef.name_vi}' là số dư cuối kỳ, không có phép cộng 4 quý")
        if spec.kind == "fy":
            if kind in ("flow", "ratio_window"):
                out.assumptions.append(f"'năm {spec.year}' = lũy kế 12 tháng (Q1–Q4/{spec.year})")
                return "ytd", period
            if kind == "ratio_ttm":
                out.assumptions.append(f"'{mdef.name_vi.split(' ')[0]} năm {spec.year}' = giá trị TTM tại Q4/{spec.year}")
            else:
                out.assumptions.append(f"số dư cuối năm {spec.year} (cuối Q4)")
            return "q", period
        if spec.kind == "ytd":
            if kind in ("flow", "ratio_window"):
                return "ytd", period
            if kind == "ratio_ttm":
                raise _Unsupported(f"'{mdef.name_vi}' chỉ tính theo 4 quý (TTM), không tính lũy kế n tháng")
            out.assumptions.append(f"số dư cuối kỳ Q{spec.quarter}/{spec.year}")
            return "q", period
        if spec.kind == "quarter" and kind == "ratio_ttm":
            out.assumptions.append(f"{mdef.name_vi.split(' ')[0]} tính trên 4 quý đến Q{spec.quarter}/{spec.year}")
        return "q", period

    @staticmethod
    def _transform(mdef: MetricDef, window: str, change: str | None, pp: bool, percent_word: bool,
                   out: ParseResult) -> str | None:
        parts: list[str] = []
        if window != "q":
            parts.append(window)
        if change is not None:
            if mdef.unit == "times":
                raise _Unsupported(f"B0 chưa hỗ trợ phép so sánh cho '{mdef.name_vi}'")
            if change == "generic":
                change = "yoy"
                out.assumptions.append("'tăng trưởng/thay đổi' không nêu kỳ gốc — so với cùng kỳ năm trước")
            if window == "ytd" and change == "qoq":
                raise _Unsupported("lũy kế chỉ so sánh với cùng kỳ năm trước")
            parts.append(change)
            if mdef.unit == "ratio":
                parts.append("pp")
                if percent_word and not pp:
                    out.assumptions.append(f"'{mdef.name_vi}' là tỷ lệ — hiểu mức thay đổi là điểm phần trăm")
        return "_".join(parts) or None

    @staticmethod
    def _threshold(mdef: MetricDef, transform: str | None, raw: tuple[float, str | None] | None,
                   out: ParseResult) -> float:
        assert raw is not None
        number, unit = raw
        if unit == "sign":
            return 0.0
        result_unit = mdef.unit
        if transform and ("yoy" in transform or "qoq" in transform):
            result_unit = "pp" if transform.endswith("_pp") else "ratio"
        if unit in ("%", "phan tram"):
            return number / 100
        scale = {"nghin ty": 1e12, "ngan ty": 1e12, "ty": 1e9, "ty dong": 1e9, "trieu": 1e6, "trieu dong": 1e6}
        if unit in scale:
            return number * scale[unit]
        if unit == "lan":
            return number
        if result_unit in ("ratio", "pp"):
            if abs(number) > 1:
                out.assumptions.append(f"ngưỡng {number:g} hiểu là {number:g}%")
                return number / 100
            return number
        if result_unit == "VND":
            out.assumptions.append(f"ngưỡng {number:g} hiểu là {number:g} tỷ đồng")
            return number * 1e9
        return number
