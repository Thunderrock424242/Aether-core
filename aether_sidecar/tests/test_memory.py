from pathlib import Path

from aether_sidecar.memory import SessionLearning


def test_session_learning_persists_lessons_to_jsonl(tmp_path: Path):
    log_path = tmp_path / "learning.jsonl"
    learning = SessionLearning(lesson_limit=3, log_path=str(log_path))

    learning.teach("session-1", "Prefer concise responses")
    learning.teach("session-1", "Use NeoForge examples")

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_session_learning_loads_prior_lessons_from_jsonl(tmp_path: Path):
    log_path = tmp_path / "learning.jsonl"
    writer = SessionLearning(lesson_limit=3, log_path=str(log_path))
    writer.teach("session-2", "Keep build.gradle organized")
    writer.teach("session-2", "Use event bus lifecycle hooks")

    reloaded = SessionLearning(lesson_limit=3, log_path=str(log_path))
    assert reloaded.lessons("session-2") == [
        "Keep build.gradle organized",
        "Use event bus lifecycle hooks",
    ]
