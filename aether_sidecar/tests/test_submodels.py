import asyncio

from aether_sidecar.backends import TemplateBackend
from aether_sidecar.config import parse_subsystem_models
from aether_sidecar.models import Subsystem


def test_parse_subsystem_models_valid_entries_only():
    parsed = parse_subsystem_models(
        "Eclipse:eclipse-model, terra : terra-model , invalid, Auto:auto-model,Helios:"
    )

    assert parsed == {
        Subsystem.ECLIPSE: "eclipse-model",
        Subsystem.TERRA: "terra-model",
    }


def test_template_backend_uses_subsystem_model_override():
    backend = TemplateBackend(
        "aether-default",
        subsystem_models={Subsystem.REQUIEM: "requiem-specialist"},
    )

    text, model_used = asyncio.run(backend.generate("Need archive lookup", Subsystem.REQUIEM))

    assert model_used == "requiem-specialist"
    assert "requiem-specialist" in text
