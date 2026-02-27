import os

from pydantic import Field

from .models import Subsystem
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AETHER_", env_file=".env", extra="ignore")
    host: str = "127.0.0.1"
    port: int = 8765
    model_backend: str = "ollama"
    model_name: str = "llama3.1:8b"
    model_auto_select: bool = False
    model_auto_profile: str = "auto"
    model_auto_candidates: str = "high:qwen2.5-coder:14b,mid:qwen2.5-coder:7b,low:llama3.1:8b"
    model_auto_ram_gb_high: float = 24.0
    model_auto_ram_gb_mid: float = 12.0
    request_timeout_seconds: float = 20.0
    max_message_chars: int = 800
    memory_turn_limit: int = 6
    learning_lesson_limit: int = 16
    learning_log_path: str | None = None
    safety_enabled: bool = True
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
    ollama_fallback_urls: str = ""
    ollama_keep_alive: str = "15m"
    app_version: str = Field(default="0.1.0")
    activation_hook_enabled: bool = False
    activation_hook_token: str | None = None
    subsystem_models: str = ""
    dev_playground_enabled: bool = False
    dev_playground_token: str | None = None


settings = Settings()



def parse_subsystem_models(raw: str) -> dict[Subsystem, str]:
    mapping: dict[Subsystem, str] = {}
    if not raw.strip():
        return mapping

    by_name: dict[str, Subsystem] = {}
    for subsystem in Subsystem:
        if subsystem == Subsystem.AUTO:
            continue
        by_name[subsystem.value.lower()] = subsystem
        by_name[subsystem.name.lower()] = subsystem

    by_name["aether-core"] = Subsystem.CORE
    by_name["aethercore"] = Subsystem.CORE
    by_name["discord"] = Subsystem.DISCORD
    by_name["discord-bot"] = Subsystem.DISCORD
    for token in raw.split(","):
        entry = token.strip()
        if not entry:
            continue

        if ":" not in entry:
            continue

        subsystem_key, model_name = entry.split(":", 1)
        subsystem = by_name.get(subsystem_key.strip().lower())
        model_name = model_name.strip()
        if subsystem and model_name:
            mapping[subsystem] = model_name

    return mapping


def parse_ollama_fallback_urls(raw: str) -> list[str]:
    if not raw.strip():
        return []

    deduped: list[str] = []
    for token in raw.split(","):
        entry = token.strip()
        if entry and entry not in deduped:
            deduped.append(entry)

    return deduped


def parse_model_auto_candidates(raw: str) -> dict[str, str]:
    if not raw.strip():
        return {}

    mapping: dict[str, str] = {}
    for token in raw.split(","):
        entry = token.strip()
        if not entry or ":" not in entry:
            continue

        tier, model_name = entry.split(":", 1)
        key = tier.strip().lower()
        value = model_name.strip()
        if key in {"low", "mid", "high"} and value:
            mapping[key] = value

    return mapping


def detect_system_memory_gb() -> float | None:
    if not hasattr(os, "sysconf"):
        return None

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
    except (OSError, ValueError):
        return None

    if not isinstance(page_size, int) or not isinstance(phys_pages, int) or page_size <= 0 or phys_pages <= 0:
        return None

    return (page_size * phys_pages) / (1024**3)


def resolve_model_name(current_settings: Settings, memory_gb: float | None = None) -> str:
    if not current_settings.model_auto_select:
        return current_settings.model_name

    candidates = parse_model_auto_candidates(current_settings.model_auto_candidates)
    profile = current_settings.model_auto_profile.strip().lower()

    if profile in {"low", "mid", "high"}:
        return candidates.get(profile, current_settings.model_name)

    measured_memory = memory_gb if memory_gb is not None else detect_system_memory_gb()
    if measured_memory is None:
        return current_settings.model_name

    if measured_memory >= current_settings.model_auto_ram_gb_high:
        return candidates.get("high", current_settings.model_name)

    if measured_memory >= current_settings.model_auto_ram_gb_mid:
        return candidates.get("mid", current_settings.model_name)

    return candidates.get("low", current_settings.model_name)
