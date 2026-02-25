from .models import Subsystem

KEYWORDS = {
    Subsystem.AEGIS: ["health", "heal", "safe", "danger", "hazard", "protection"],
    Subsystem.ECLIPSE: ["rift", "anomaly", "portal", "corruption", "instability"],
    Subsystem.TERRA: ["biome", "terrain", "explore", "map", "resource", "restoration"],
    Subsystem.HELIOS: ["energy", "power", "machine", "generator", "atmosphere"],
    Subsystem.ENFORCER: ["fight", "combat", "enemy", "defense", "security", "weapon"],
    Subsystem.REQUIEM: ["lore", "history", "archive", "memory", "record", "story"],
}


def detect_subsystem_alerts(message: str) -> dict[Subsystem, list[str]]:
    lowered = message.lower()
    alerts: dict[Subsystem, list[str]] = {}
    for subsystem, words in KEYWORDS.items():
        matches = [word for word in words if word in lowered]
        if matches:
            alerts[subsystem] = matches
    return alerts


def pick_subsystem(message: str) -> Subsystem:
    alerts = detect_subsystem_alerts(message)
    if not alerts:
        return Subsystem.AEGIS

    winner = max(alerts, key=lambda subsystem: len(alerts[subsystem]))
    return winner
