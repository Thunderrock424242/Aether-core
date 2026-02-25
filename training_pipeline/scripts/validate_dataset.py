#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training_pipeline.src.data_utils import load_jsonl, validate_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate A.E.T.H.E.R JSONL training dataset")
    parser.add_argument("dataset", help="Path to JSONL dataset")
    args = parser.parse_args()

    rows = load_jsonl(args.dataset)
    validate_rows(rows)
    print(f"Dataset valid: {len(rows)} rows")


if __name__ == "__main__":
    main()
