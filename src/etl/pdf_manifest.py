"""Generate the required original PDF financial statement checklist for Pilot tickers."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .pilot_etl import DEFAULT_VN30_PATH, get_pilot_tickers, load_vn30_reference

IR_PORTALS: dict[str, str] = {
    "FPT": "https://fpt.com.vn/en/investor/reports/financial-report",
    "HPG": "https://www.hoaphat.com.vn/bao-cao-tai-chinh",
    "MWG": "https://mwg.vn",
    "VCB": "https://www.vietcombank.com.vn",
    "TCB": "https://techcombank.com",
}


def _expected_report_kind(fiscal_quarter: int) -> tuple[str, str]:
    """Return `(period_code, expected_assurance)` for Vietnamese listed reports."""
    if fiscal_quarter == 2:
        return "Q2_6M", "reviewed"
    if fiscal_quarter == 4:
        return "Q4_AND_FY", "audited_or_original"
    return f"Q{fiscal_quarter}", "original"


def generate_pilot_pdf_manifest(
    tickers: list[str],
    start_year: int = 2021,
    end_year: int = 2026,
    max_quarter_end_year: int = 3,
) -> pd.DataFrame:
    """Build a checklist DataFrame of consolidated PDF reports for pilot cross-checking."""
    rows: list[dict[str, object]] = []
    for ticker in sorted(tickers):
        ir_url = IR_PORTALS.get(ticker, "")
        for year in range(start_year, end_year + 1):
            max_q = max_quarter_end_year if year == end_year else 4
            for quarter in range(1, max_q + 1):
                period_code, assurance = _expected_report_kind(quarter)
                report_id = f"{ticker}_{year}Q{quarter}_CONSOL"
                expected_filename = f"{report_id}.pdf"
                rows.append(
                    {
                        "ticker": ticker,
                        "fiscal_year": year,
                        "fiscal_quarter": quarter,
                        "period_code": period_code,
                        "consolidation_scope": "consolidated",
                        "expected_assurance": assurance,
                        "source_report_id": report_id,
                        "local_pdf_path": f"data/raw_pdfs/{ticker}/{expected_filename}",
                        "ir_portal_url": ir_url,
                        "status": "PENDING",
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Pilot PDF collection manifest")
    parser.add_argument("--vn30-csv", type=Path, default=DEFAULT_VN30_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/pilot_pdf_manifest_2021_2026.csv"),
    )
    args = parser.parse_args()

    vn30_df = load_vn30_reference(args.vn30_csv)
    pilots = get_pilot_tickers(vn30_df)
    manifest_df = generate_pilot_pdf_manifest(pilots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest_df.to_csv(args.output, index=False, encoding="utf-8")
    print(f"Wrote {len(manifest_df)} expected PDF entries for {pilots} -> {args.output}")


if __name__ == "__main__":
    main()
