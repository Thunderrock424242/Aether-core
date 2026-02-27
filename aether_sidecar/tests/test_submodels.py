from aether_sidecar.config import (
    parse_model_auto_candidates,
    parse_ollama_fallback_urls,
    parse_subsystem_models,
    resolve_model_name,
)
from aether_sidecar.models import Subsystem


class DummySettings:
    def __init__(self):
        self.model_name = "llama3.1:8b"
        self.model_auto_select = True
        self.model_auto_profile = "auto"
        self.model_auto_candidates = "high:qwen2.5-coder:14b,mid:qwen2.5-coder:7b,low:llama3.1:8b"
        self.model_auto_ram_gb_high = 24.0
        self.model_auto_ram_gb_mid = 12.0


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


def test_parse_model_auto_candidates_valid_tiers_only():
    parsed = parse_model_auto_candidates("high:qwen2.5-coder:14b,mid:qwen2.5-coder:7b,low:llama3.1:8b,invalid:x")

    assert parsed == {
        "high": "qwen2.5-coder:14b",
        "mid": "qwen2.5-coder:7b",
        "low": "llama3.1:8b",
    }


def test_resolve_model_name_uses_profile_override():
    settings = DummySettings()
    settings.model_auto_profile = "mid"

    assert resolve_model_name(settings, memory_gb=32.0) == "qwen2.5-coder:7b"


def test_resolve_model_name_uses_memory_buckets_when_auto_profile():
    settings = DummySettings()

    assert resolve_model_name(settings, memory_gb=30.0) == "qwen2.5-coder:14b"
    assert resolve_model_name(settings, memory_gb=16.0) == "qwen2.5-coder:7b"
    assert resolve_model_name(settings, memory_gb=8.0) == "llama3.1:8b"


def test_resolve_model_name_returns_default_when_auto_disabled():
    settings = DummySettings()
    settings.model_auto_select = False

    assert resolve_model_name(settings, memory_gb=64.0) == "llama3.1:8b"
