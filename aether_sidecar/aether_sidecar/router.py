import re

from .models import Subsystem

SUBSYSTEM_PROFILES = {
    Subsystem.CORE: {
        "purpose": "main Aether Core orchestration and general AI assistance",
        "keywords": ["aether", "core", "general", "assistant", "chat"],
    },
    Subsystem.JAVA: {
        "purpose": "java integration and Minecraft modding workflows",
        "keywords": ["java", "neoforge", "gradle", "mod", "modding", "forge"],
    },
    Subsystem.DISCORD: {
        "purpose": "Discord bot integration, commands, and automations",
        "keywords": ["discord", "bot", "guild", "slash command", "moderation"],
    },
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

MINECRAFT_SUBSYSTEMS = {
    Subsystem.JAVA,
    Subsystem.AEGIS,
    Subsystem.ECLIPSE,
    Subsystem.TERRA,
    Subsystem.HELIOS,
    Subsystem.ENFORCER,
    Subsystem.REQUIEM,
}

MINECRAFT_CONTEXT_KEYWORDS = {
    "minecraft",
    "neoforge",
    "mod",
    "modding",
    "craft",
    "creeper",
    "nether",
    "enderman",
    "redstone",
    "block",
    "biome",
    "survival",
}


def _message_contains_keyword(message: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in message
    return re.search(rf"\b{re.escape(keyword)}\b", message) is not None


def subsystem_teaching_context(subsystem: Subsystem) -> str:
    profile = SUBSYSTEM_PROFILES[subsystem]
    keywords = ", ".join(profile["keywords"])
    return f"{subsystem.value} focus: {profile['purpose']}. Routing keywords to watch: {keywords}."


def detect_subsystem_alerts(message: str) -> dict[Subsystem, list[str]]:
    lowered = message.lower()
    alerts: dict[Subsystem, list[str]] = {}
    for subsystem, words in KEYWORDS.items():
        matches = [word for word in words if _message_contains_keyword(lowered, word)]
        if matches:
            alerts[subsystem] = matches
    return alerts


def pick_subsystem(message: str) -> Subsystem:
    alerts = detect_subsystem_alerts(message)
    if not alerts:
        return Subsystem.CORE

    winner = max(alerts, key=lambda subsystem: len(alerts[subsystem]))
    return winner


def is_minecraft_related(message: str) -> bool:
    lowered = message.lower()
    subsystem_keyword_match = any(
        _message_contains_keyword(lowered, word)
        for subsystem, words in KEYWORDS.items()
        if subsystem in MINECRAFT_SUBSYSTEMS
        for word in words
    )
    return subsystem_keyword_match or any(
        _message_contains_keyword(lowered, keyword) for keyword in MINECRAFT_CONTEXT_KEYWORDS
    )


def assistant_name_for_subsystem(subsystem: Subsystem) -> str:
    names = {
        Subsystem.CORE: "Aether Core",
        Subsystem.JAVA: "Java",
        Subsystem.DISCORD: "Discord Bot",
        Subsystem.AEGIS: "Aegis",
        Subsystem.ECLIPSE: "Eclipse",
        Subsystem.TERRA: "Terra",
        Subsystem.HELIOS: "Helios",
        Subsystem.ENFORCER: "Enforcer",
        Subsystem.REQUIEM: "Requiem",
    }
    return names[subsystem]
