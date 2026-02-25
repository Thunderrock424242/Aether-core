from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AETHER_", env_file=".env", extra="ignore")
    host: str = "127.0.0.1"
    port: int = 8765
    model_backend: str = "template"
    model_name: str = "aether-template-v1"
    request_timeout_seconds: float = 20.0
    max_message_chars: int = 800
    memory_turn_limit: int = 6
    safety_enabled: bool = True
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
    app_version: str = Field(default="0.1.0")
    activation_hook_enabled: bool = False
    activation_hook_token: str | None = None


settings = Settings()
