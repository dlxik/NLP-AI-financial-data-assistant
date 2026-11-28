"""CLI chấm một file kết quả theo Gold.

Ví dụ: python scripts/score_results.py --gold gold.json --pred predictions.jsonl
"""

from __future__ import annotations

import argparse
import json

from fin_assistant.evaluation import score_batch
from fin_assistant.evaluation.io import load_gold, load_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Chấm kết quả Financial Data Assistant")
    parser.add_argument("--gold", required=True, help="Gold JSON/JSONL")
    parser.add_argument("--pred", required=True, help="Prediction JSON/JSONL")
    parser.add_argument("--output", help="Ghi báo cáo JSON; mặc định in stdout")
    args = parser.parse_args()

    report = score_batch(load_gold(args.gold), load_records(args.pred)).to_dict()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
