from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Subsystem(str, Enum):
    AEGIS = "Aegis"
    ECLIPSE = "Eclipse"
    TERRA = "Terra"
    HELIOS = "Helios"
    ENFORCER = "Enforcer"
    REQUIEM = "Requiem"
    AUTO = "Auto"


class GenerateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    subsystem: Subsystem = Subsystem.AUTO
    player_context: dict = Field(default_factory=dict)
    world_context: dict = Field(default_factory=dict)
    session_id: str = Field(min_length=1)


class GenerateResponse(BaseModel):
    text: str
    subsystem_used: Subsystem
    subsystem_alerts: dict[str, list[str]] = Field(default_factory=dict)
    safety_flags: list[str] = Field(default_factory=list)
    latency_ms: int


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model_backend: str
    model_name: str


class VersionResponse(BaseModel):
    service: str = "aether-sidecar"
    version: str
    model_name: str
