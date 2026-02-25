BLOCKLIST = {"racial slur", "kill yourself"}


class SafetyResult:
    def __init__(self, blocked: bool, flags: list[str] | None = None):
        self.blocked = blocked
        self.flags = flags or []


def evaluate_message(message: str) -> SafetyResult:
    lowered = message.lower()
    matched = [term for term in BLOCKLIST if term in lowered]
    return SafetyResult(blocked=bool(matched), flags=matched)


def safe_refusal() -> str:
    return "A.E.T.H.E.R cannot assist with that request. Try a survival, exploration, anomaly, power, combat, or lore question."
