from .models import Subsystem

SUBSYSTEM_PROFILES = {
    Subsystem.AEGIS: {
        "purpose": "safety, hazard prevention, and health stabilization",
        "keywords": ["health", "heal", "safe", "danger", "hazard", "protection"],
    },
    Subsystem.ECLIPSE: {
        "purpose": "anomaly, rift, and corruption interpretation",
        "keywords": ["rift", "anomaly", "portal", "corruption", "instability"],
    },
    Subsystem.TERRA: {
        "purpose": "terrain analysis, scouting, and restoration planning",
        "keywords": ["biome", "terrain", "explore", "map", "resource", "restoration"],
    },
    Subsystem.HELIOS: {
        "purpose": "energy systems, machines, and atmosphere stability",
        "keywords": ["energy", "power", "machine", "generator", "atmosphere"],
    },
    Subsystem.ENFORCER: {
        "purpose": "combat readiness, defense, and security",
        "keywords": ["fight", "combat", "enemy", "defense", "security", "weapon"],
    },
    Subsystem.REQUIEM: {
        "purpose": "lore, archives, and continuity",
        "keywords": ["lore", "history", "archive", "memory", "record", "story"],
    },
}

KEYWORDS = {subsystem: profile["keywords"] for subsystem, profile in SUBSYSTEM_PROFILES.items()}


def subsystem_teaching_context(subsystem: Subsystem) -> str:
    profile = SUBSYSTEM_PROFILES[subsystem]
    keywords = ", ".join(profile["keywords"])
    return (
        f"{subsystem.value} focus: {profile['purpose']}. "
        f"Routing keywords to watch: {keywords}."
    )


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
