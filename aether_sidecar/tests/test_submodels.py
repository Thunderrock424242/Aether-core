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
