from .models import Subsystem

KEYWORDS = {
    Subsystem.AEGIS: ["health", "heal", "safe", "danger", "hazard", "protection"],
    Subsystem.ECLIPSE: ["rift", "anomaly", "portal", "corruption", "instability"],
    Subsystem.TERRA: ["biome", "terrain", "explore", "map", "resource", "restoration"],
    Subsystem.HELIOS: ["energy", "power", "machine", "generator", "atmosphere"],
    Subsystem.ENFORCER: ["fight", "combat", "enemy", "defense", "security", "weapon"],
    Subsystem.REQUIEM: ["lore", "history", "archive", "memory", "record", "story"],
}


def pick_subsystem(message: str) -> Subsystem:
    lowered = message.lower()
    scores = {k: 0 for k in KEYWORDS}
    for subsystem, words in KEYWORDS.items():
        for word in words:
            if word in lowered:
                scores[subsystem] += 1
    winner = max(scores, key=scores.get)
    return winner if scores[winner] > 0 else Subsystem.AEGIS
