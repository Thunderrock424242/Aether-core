from aether_sidecar.config import parse_ollama_fallback_urls, parse_subsystem_models
from aether_sidecar.models import Subsystem


def test_parse_subsystem_models_valid_entries_only():
    parsed = parse_subsystem_models(
        "Eclipse:eclipse-model, terra : terra-model , invalid, Auto:auto-model,Helios:"
    )

    assert parsed == {
        Subsystem.ECLIPSE: "eclipse-model",
        Subsystem.TERRA: "terra-model",
    }


def test_parse_ollama_fallback_urls_dedupes_and_skips_empty_entries():
    parsed = parse_ollama_fallback_urls(" http://a:11434/api/generate, ,http://b:11434/api/generate,http://a:11434/api/generate ")

    assert parsed == [
        "http://a:11434/api/generate",
        "http://b:11434/api/generate",
    ]
