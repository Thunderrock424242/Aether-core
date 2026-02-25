import json
from pathlib import Path

REQUIRED_FIELDS = {
    "subsystem",
    "player_state",
    "world_state",
    "prompt",
    "ideal_response",
    "safety_label",
}


def load_jsonl(path: str) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            rows.append(obj)
    return rows


def validate_rows(rows: list[dict]) -> None:
    for idx, row in enumerate(rows, start=1):
        missing = REQUIRED_FIELDS - set(row.keys())
        if missing:
            raise ValueError(f"Row {idx} missing required fields: {sorted(missing)}")


def to_instruction_text(row: dict) -> str:
    return (
        f"Subsystem: {row['subsystem']}\n"
        f"Player state: {row['player_state']}\n"
        f"World state: {row['world_state']}\n"
        f"User: {row['prompt']}\n"
        f"Assistant: {row['ideal_response']}"
    )
