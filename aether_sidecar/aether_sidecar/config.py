from pydantic import Field

from .models import Subsystem
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AETHER_", env_file=".env", extra="ignore")
    host: str = "127.0.0.1"
    port: int = 8765
    model_backend: str = "ollama"
    model_name: str = "llama3.1:8b"
    request_timeout_seconds: float = 20.0
    max_message_chars: int = 800
    memory_turn_limit: int = 6
    learning_lesson_limit: int = 16
    learning_log_path: str | None = None
    safety_enabled: bool = True
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
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

    by_name = {subsystem.value.lower(): subsystem for subsystem in Subsystem if subsystem != Subsystem.AUTO}
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
