from collections import defaultdict


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
    def __init__(self, lesson_limit: int = 16):
        self.lesson_limit = lesson_limit
        self._lessons = defaultdict(list)

    def teach(self, session_id: str, lesson: str) -> None:
        self._lessons[session_id].append(lesson)
        if len(self._lessons[session_id]) > self.lesson_limit:
            self._lessons[session_id] = self._lessons[session_id][-self.lesson_limit :]

    def lessons(self, session_id: str) -> list[str]:
        return list(self._lessons[session_id])
