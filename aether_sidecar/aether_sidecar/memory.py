import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


class SessionMemory:
    def __init__(self, turn_limit: int = 6):
        self.turn_limit = turn_limit
        self._turns = defaultdict(list)

    def append(self, session_id: str, role: str, text: str) -> None:
        self._turns[session_id].append({"role": role, "text": text})
        if len(self._turns[session_id]) > self.turn_limit * 2:
            self._turns[session_id] = self._turns[session_id][-self.turn_limit * 2 :]

    def history(self, session_id: str) -> list[dict[str, str]]:
        return list(self._turns[session_id])


class SessionLearning:
    def __init__(self, lesson_limit: int = 16, log_path: str | None = None):
        self.lesson_limit = lesson_limit
        self._lessons = defaultdict(list)
        self._log_path = Path(log_path) if log_path else None
        self._load_from_log()

    def _load_from_log(self) -> None:
        if not self._log_path or not self._log_path.exists():
            return

        for line in self._log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            session_id = str(row.get("session_id") or "").strip()
            lesson = str(row.get("lesson") or "").strip()
            if session_id and lesson:
                self._append_lesson(session_id, lesson)

    def _append_lesson(self, session_id: str, lesson: str) -> None:
        self._lessons[session_id].append(lesson)
        if len(self._lessons[session_id]) > self.lesson_limit:
            self._lessons[session_id] = self._lessons[session_id][-self.lesson_limit :]

    def _append_to_log(self, session_id: str, lesson: str) -> None:
        if not self._log_path:
            return

        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": session_id,
            "lesson": lesson,
        }
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def teach(self, session_id: str, lesson: str) -> None:
        self._append_lesson(session_id, lesson)
        self._append_to_log(session_id, lesson)

    def lessons(self, session_id: str) -> list[str]:
        return list(self._lessons[session_id])
