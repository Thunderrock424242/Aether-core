import httpx

from .models import Subsystem

SYSTEM_PROMPTS = {
    Subsystem.AEGIS: "You are Aegis, focused on safety and hazard prevention in Minecraft.",
    Subsystem.ECLIPSE: "You are Eclipse, focused on anomaly and rift risk interpretation.",
    Subsystem.TERRA: "You are Terra, focused on terrain, scouting, and restoration.",
    Subsystem.HELIOS: "You are Helios, focused on power systems and atmosphere stability.",
    Subsystem.ENFORCER: "You are Enforcer, focused on combat readiness and security.",
    Subsystem.REQUIEM: "You are Requiem, focused on lore, archives, and continuity.",
}


class BaseBackend:
    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str]:
        raise NotImplementedError


class TemplateBackend(BaseBackend):
    def __init__(self, default_model_name: str, subsystem_models: dict[Subsystem, str] | None = None):
        self.default_model_name = default_model_name
        self.subsystem_models = subsystem_models or {}

    def model_for_subsystem(self, subsystem: Subsystem) -> str:
        return self.subsystem_models.get(subsystem, self.default_model_name)

    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str]:
        model_name = self.model_for_subsystem(subsystem)
        text = (
            f"[{subsystem.value}/{model_name}] A.E.T.H.E.R response: {prompt[:180]}\n"
            "Actionable next step: gather resources, check hazards, and proceed with caution."
        )
        return text, model_name


class OllamaBackend(BaseBackend):
    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float = 20.0,
        subsystem_models: dict[Subsystem, str] | None = None,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.subsystem_models = subsystem_models or {}

    def model_for_subsystem(self, subsystem: Subsystem) -> str:
        return self.subsystem_models.get(subsystem, self.model_name)

    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str]:
        model_name = self.model_for_subsystem(subsystem)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(self.base_url, json={
                "model": model_name,
                "prompt": f"{SYSTEM_PROMPTS.get(subsystem, SYSTEM_PROMPTS[Subsystem.AEGIS])}\n\nUser request:\n{prompt}",
                "stream": False,
            })
            resp.raise_for_status()
            data = resp.json()
            text = (data.get("response") or "").strip() or "No model response."
            return text, model_name
