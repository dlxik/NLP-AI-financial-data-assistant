"""Pilot ETL utilities for VN30 filtering, YTD->Q derivation, and snapshot export."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from .schema import (
    FACT_FINANCIALS_COLUMNS,
    FactFinancialRecord,
    records_to_dataframe,
    validate_fact_dataframe,
)

DEFAULT_VN30_PATH = Path("data/reference/vn30_constituents_2026-11-27.csv")

# Version compatibility matrix: pairs considered directly comparable without
# raising a restatement/audit mismatch guard during YTD->Q subtraction.
COMPATIBLE_VERSION_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("original", "original"),
        ("reviewed", "reviewed"),
        ("audited", "audited"),
        ("restated", "restated"),
        ("reviewed", "original"),
        ("original", "reviewed"),
        ("audited", "reviewed"),
        ("audited", "original"),
    }
)


def load_vn30_reference(path: Path | str = DEFAULT_VN30_PATH) -> pd.DataFrame:
    """Load the frozen VN30 constituent classification CSV."""
    df = pd.read_csv(path, dtype={"ticker": str})
    df["eligible_5y"] = df["eligible_5y"].astype(str).str.lower() == "true"
    df["is_pilot"] = df["is_pilot"].astype(str).str.lower() == "true"
    return df


def get_pilot_tickers(vn30_df: pd.DataFrame) -> list[str]:
    """Return sorted pilot tickers flagged in the VN30 reference table."""
    pilots = vn30_df.loc[vn30_df["is_pilot"] & (vn30_df["keep_status"] == "KEEP"), "ticker"]
    return sorted(pilots.tolist())


def _quarter_date_bounds(fiscal_year: int, fiscal_quarter: int) -> tuple[str, str]:
    """Return ISO `(period_start, period_end)` for standard calendar fiscal year."""
    bounds = {
        1: (f"{fiscal_year}-01-01", f"{fiscal_year}-03-31"),
        2: (f"{fiscal_year}-04-01", f"{fiscal_year}-06-30"),
        3: (f"{fiscal_year}-07-01", f"{fiscal_year}-09-30"),
        4: (f"{fiscal_year}-10-01", f"{fiscal_year}-12-31"),
    }
    if fiscal_quarter not in bounds:
        raise ValueError(f"Invalid fiscal_quarter: {fiscal_quarter}")
    return bounds[fiscal_quarter]


def _pick_best_cumulative(group: pd.DataFrame, target_period_type: str, target_quarter: int) -> pd.Series | None:
    """Select the highest-assurance cumulative row for a given period_type & quarter."""
    priority = {"restated": 4, "audited": 3, "reviewed": 2, "original": 1}
    sub = group[
        (group["period_type"] == target_period_type) & (group["fiscal_quarter"] == target_quarter)
    ].copy()
    if sub.empty:
        return None
    sub["_prio"] = sub["report_version"].map(lambda v: priority.get(v, 0))
    sub = sub.sort_values(["_prio", "as_of_date"], ascending=[False, False])
    return sub.iloc[0]


def derive_single_quarter_from_ytd(df: pd.DataFrame) -> pd.DataFrame:
    """Derive single-quarter (`Q`) flow observations from `YTD`/`FY` when missing.

    Rules enforced:
    1. Only applies to `item_type == "flow"` (never subtracts `stock` items).
    2. Groups strictly by `(ticker, entity_group, statement_type, item_code, fiscal_year, consolidation_scope, unit)`.
    3. Verifies `report_version` compatibility and records `derived_from` lineage JSON.
    4. Never overwrites an already-present direct `Q` row with the same `report_version`.
    """
    if df.empty:
        return df.copy()

    errors = validate_fact_dataframe(df)
    if errors:
        raise ValueError(f"Input fact_financials failed validation: {errors}")

    flow_df = df[df["item_type"] == "flow"].copy()
    if flow_df.empty:
        return df.copy()

    group_cols = [
        "ticker",
        "entity_group",
        "statement_type",
        "item_code",
        "fiscal_year",
        "consolidation_scope",
        "unit",
    ]

    derived_records: list[FactFinancialRecord] = []
    existing_keys = set(
        zip(
            df["ticker"],
            df["statement_type"],
            df["item_code"],
            df["fiscal_year"],
            df["fiscal_quarter"],
            df["period_type"],
            df["consolidation_scope"],
        )
    )

    # Quarter derivation map: target_q -> ((end_ptype, end_q), (prev_ptype, prev_q), formula_label)
    derivations = (
        (1, ("YTD", 1), None, "YTD_Q1"),
        (2, ("YTD", 2), ("YTD", 1), "YTD_6M - YTD_Q1"),
        (3, ("YTD", 3), ("YTD", 2), "YTD_9M - YTD_6M"),
        (4, ("FY", 0), ("YTD", 3), "FY - YTD_9M"),
    )

    for key_vals, grp in flow_df.groupby(group_cols, sort=False):
        ticker, entity_group, stmt_type, item_code, fiscal_year, scope, unit = key_vals
        for target_q, end_spec, prev_spec, formula_label in derivations:
            check_key = (ticker, stmt_type, item_code, int(fiscal_year), target_q, "Q", scope)
            if check_key in existing_keys:
                continue

            end_row = _pick_best_cumulative(grp, end_spec[0], end_spec[1])
            if end_row is None:
                continue

            if prev_spec is None:
                val = float(end_row["value"])
                inputs = [str(end_row["fact_id"])]
                version_pair = [str(end_row["report_version"])]
                derived_ver = str(end_row["report_version"])
                is_restated = bool(end_row["is_restated"])
                as_of_date = str(end_row["as_of_date"])
                source_report_id = str(end_row["source_report_id"])
            else:
                prev_row = _pick_best_cumulative(grp, prev_spec[0], prev_spec[1])
                if prev_row is None:
                    # Fallback for Q2/Q3 if Q1/Q2 was stored directly as Q rather than YTD
                    if prev_spec == ("YTD", 1):
                        prev_row = _pick_best_cumulative(grp, "Q", 1)
                    if prev_row is None:
                        continue

                ver_pair = (str(end_row["report_version"]), str(prev_row["report_version"]))
                if ver_pair not in COMPATIBLE_VERSION_PAIRS:
                    continue

                val = float(end_row["value"]) - float(prev_row["value"])
                inputs = [str(end_row["fact_id"]), str(prev_row["fact_id"])]
                version_pair = list(ver_pair)
                derived_ver = str(end_row["report_version"])
                is_restated = bool(end_row["is_restated"]) or bool(prev_row["is_restated"])
                as_of_date = max(str(end_row["as_of_date"]), str(prev_row["as_of_date"]))
                source_report_id = f"{end_row['source_report_id']}-{prev_row['source_report_id']}"

            p_start, p_end = _quarter_date_bounds(int(fiscal_year), target_q)
            lineage = json.dumps(
                {
                    "formula": formula_label,
                    "inputs": inputs,
                    "version_pair": version_pair,
                },
                ensure_ascii=False,
            )

            derived_records.append(
                FactFinancialRecord(
                    ticker=str(ticker),
                    entity_group=str(entity_group),
                    statement_type=str(stmt_type),
                    item_code=str(item_code),
                    item_name_vi=str(end_row["item_name_vi"]),
                    item_type="flow",
                    fiscal_year=int(fiscal_year),
                    fiscal_quarter=target_q,
                    period_type="Q",
                    period_start=p_start,
                    period_end=p_end,
                    value=val,
                    unit=str(unit),
                    consolidation_scope=str(scope),
                    as_of_date=as_of_date,
                    report_version=derived_ver,
                    is_restated=is_restated,
                    source_report_id=source_report_id,
                    source_ref=f"derived:{formula_label}",
                    derived_from=lineage,
                ).finalize()
            )
            existing_keys.add(check_key)

    if not derived_records:
        return df.copy()

    derived_df = records_to_dataframe(derived_records)
    combined = pd.concat([df.loc[:, list(FACT_FINANCIALS_COLUMNS)], derived_df], ignore_index=True)
    return combined


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def export_snapshot(
    df: pd.DataFrame,
    output_dir: Path | str,
    snapshot_tag: str = "pilot_v0.1",
) -> dict[str, str]:
    """Validate and export `fact_financials` snapshot with SHA-256 integrity manifest."""
    errors = validate_fact_dataframe(df)
    if errors:
        raise ValueError(f"Cannot export invalid snapshot: {errors}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    csv_path = out_path / f"fact_financials_{snapshot_tag}.csv"
    df_sorted = df.sort_values(
        ["ticker", "statement_type", "item_code", "fiscal_year", "fiscal_quarter", "period_type"]
    ).reset_index(drop=True)
    df_sorted.to_csv(csv_path, index=False, encoding="utf-8")

    manifest = {
        "snapshot_tag": snapshot_tag,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "row_count": int(len(df_sorted)),
        "tickers": sorted(df_sorted["ticker"].unique().tolist()) if not df_sorted.empty else [],
        "files": {
            csv_path.name: {
                "sha256": _sha256_file(csv_path),
                "bytes": csv_path.stat().st_size,
            }
        },
    }
    manifest_path = out_path / f"manifest_{snapshot_tag}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"csv": str(csv_path), "manifest": str(manifest_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="TV1 Pilot ETL verification CLI")
    parser.add_argument("--vn30-csv", type=Path, default=DEFAULT_VN30_PATH)
    args = parser.parse_args()

    vn30 = load_vn30_reference(args.vn30_csv)
    kept = vn30[vn30["keep_status"] == "KEEP"]
    excluded = vn30[vn30["keep_status"] == "EXCLUDE"]
    pilots = get_pilot_tickers(vn30)

    print(f"VN30 freeze file: {args.vn30_csv} (as of {date.today().isoformat()})")
    print(f"Total: {len(vn30)} | KEEP: {len(kept)} | EXCLUDE: {len(excluded)}")
    print(f"Pilot tickers ({len(pilots)}): {', '.join(pilots)}")


if __name__ == "__main__":
    main()
