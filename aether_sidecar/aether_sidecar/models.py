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


class HookAction(str, Enum):
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"


class ModLifecycleHookRequest(BaseModel):
    action: HookAction
    mod_id: str = Field(min_length=1, max_length=128)
    mod_version: str = Field(min_length=1, max_length=64)
    instance_id: str = Field(default="default", min_length=1, max_length=128)
    token: str | None = None


class ModLifecycleHookResponse(BaseModel):
    active_instances: list[str] = Field(default_factory=list)
    activation_required: bool


class HookStatusResponse(BaseModel):
    activation_required: bool
    active_instances: list[str] = Field(default_factory=list)


class TeachRequest(BaseModel):
    lesson: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(min_length=1)


class TeachResponse(BaseModel):
    saved: bool = True
    lessons_count: int


class LearningStatusResponse(BaseModel):
    session_id: str
    lessons: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    subsystem: Subsystem = Subsystem.AUTO
    player_context: dict = Field(default_factory=dict)
    world_context: dict = Field(default_factory=dict)
    session_id: str = Field(min_length=1)


class GenerateResponse(BaseModel):
    text: str
    subsystem_used: Subsystem
    model_used: str
    subsystem_alerts: dict[str, list[str]] = Field(default_factory=dict)
    safety_flags: list[str] = Field(default_factory=list)
    learned_context: list[str] = Field(default_factory=list)
    latency_ms: int




class DevPlaygroundAuthRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class DevPlaygroundAuthResponse(BaseModel):
    ok: bool = True


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model_backend: str
    model_name: str
    keep_alive: str


class ModelStatusResponse(BaseModel):
    status: Literal["online", "offline"]
    detail: str | None = None
    checked_model: str
    latency_ms: int | None = None
    attempted_urls: list[str] = Field(default_factory=list)


class StatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model_backend: str
    model_name: str
    keep_alive: str
    uptime_seconds: int
    activation_required: bool
    active_instances: list[str] = Field(default_factory=list)
    model: ModelStatusResponse


class WarmupResponse(BaseModel):
    status: Literal["ready"] = "ready"
    model_name: str
    subsystem: Subsystem


class VersionResponse(BaseModel):
    service: str = "aether-sidecar"
    version: str
    model_name: str
