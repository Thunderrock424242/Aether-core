from fastapi.testclient import TestClient

from aether_sidecar import app as app_module
from aether_sidecar.backends import TemplateBackend
from aether_sidecar.config import settings

activation_registry = app_module.activation_registry
app = app_module.app
learning = app_module.learning


client = TestClient(app)


class FakeBackend:
    async def generate(self, prompt: str, subsystem):
        scope = "general" if "Request scope: general-conversation" in prompt else "minecraft"
        return f"[{scope}] simulated model response", f"fake-{subsystem.value.lower()}"


def setup_function() -> None:
    activation_registry.active_instances.clear()
    learning._lessons.clear()
    settings.activation_hook_enabled = False
    settings.activation_hook_token = None
    settings.dev_playground_enabled = False
    settings.dev_playground_token = None
    app_module.backend = TemplateBackend("aether-template-v1")


def test_generate_returns_keyword_alerts():
    response = client.post(
        "/generate",
        json={
            "message": "rift anomaly near my machine",
            "subsystem": "Auto",
            "player_context": {"health": 20},
            "world_context": {"weather": "storm"},
            "session_id": "test-session-1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subsystem_used"] == "Eclipse"
    assert "Eclipse" in body["subsystem_alerts"]
    assert "anomaly" in body["subsystem_alerts"]["Eclipse"]
    assert body["model_used"] == "fake-eclipse"
    assert "[minecraft]" in body["text"]


def test_generate_non_minecraft_message_returns_aether_smalltalk_reply():
    response = client.post(
        "/generate",
        json={
            "message": "How are you today?",
            "subsystem": "Auto",
            "session_id": "test-session-smalltalk",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subsystem_used"] == "Aegis"
    assert body["model_used"] == "fake-aegis"
    assert "[general]" in body["text"]


def test_metrics_endpoint_available():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "aether_http_requests_total" in response.text


def test_activation_hook_lifecycle_blocks_until_activated():
    settings.activation_hook_enabled = True

    blocked = client.post(
        "/generate",
        json={
            "message": "hello",
            "subsystem": "Auto",
            "session_id": "test-session-2",
        },
    )
    assert blocked.status_code == 503

    activate = client.post(
        "/hooks/mod-lifecycle",
        json={
            "action": "activate",
            "mod_id": "aether-core-mod",
            "mod_version": "1.0.0",
            "instance_id": "client-1",
        },
    )
    assert activate.status_code == 200
    assert activate.json()["active_instances"] == ["client-1"]

    allowed = client.post(
        "/generate",
        json={
            "message": "hello",
            "subsystem": "Auto",
            "session_id": "test-session-2",
        },
    )
    assert allowed.status_code == 200


def test_activation_hook_rejects_invalid_token():
    settings.activation_hook_enabled = True
    settings.activation_hook_token = "secret"

    denied = client.post(
        "/hooks/mod-lifecycle",
        json={
            "action": "activate",
            "mod_id": "aether-core-mod",
            "mod_version": "1.0.0",
            "instance_id": "client-1",
            "token": "wrong",
        },
    )

    assert denied.status_code == 401


def test_teach_and_learning_status_endpoints():
    teach_response = client.post(
        "/teach",
        json={"lesson": "Prefer concise explanations.", "session_id": "test-session-3"},
    )

    assert teach_response.status_code == 200
    assert teach_response.json()["lessons_count"] == 1

    status_response = client.get("/learning/test-session-3")
    assert status_response.status_code == 200
    assert status_response.json()["lessons"] == ["Prefer concise explanations."]


def test_generate_includes_learned_context():
    client.post(
        "/teach",
        json={"lesson": "I am building NeoForge mods with Gradle.", "session_id": "test-session-4"},
    )

    response = client.post(
        "/generate",
        json={
            "message": "How should we structure our next feature?",
            "subsystem": "Auto",
            "session_id": "test-session-4",
        },
    )

    assert response.status_code == 200
    assert response.json()["learned_context"] == ["I am building NeoForge mods with Gradle."]


def test_dev_playground_disabled_by_default():
    response = client.get("/dev/playground")
    assert response.status_code == 404


def test_dev_playground_page_enabled():
    settings.dev_playground_enabled = True
    response = client.get("/dev/playground")
    assert response.status_code == 200
    assert "A.E.T.H.E.R Dev Playground" in response.text


def test_playground_token_required_for_generate_teach_learning():
    settings.dev_playground_token = "secret"

    teach_denied = client.post(
        "/teach",
        json={"lesson": "Use concise answers.", "session_id": "token-test"},
    )
    assert teach_denied.status_code == 401

    teach_allowed = client.post(
        "/teach",
        headers={"Authorization": "Bearer secret"},
        json={"lesson": "Use concise answers.", "session_id": "token-test"},
    )
    assert teach_allowed.status_code == 200

    learning_denied = client.get("/learning/token-test")
    assert learning_denied.status_code == 401

    learning_allowed = client.get("/learning/token-test", headers={"Authorization": "Bearer secret"})
    assert learning_allowed.status_code == 200

    generate_denied = client.post(
        "/generate",
        json={
            "message": "hello",
            "subsystem": "Auto",
            "session_id": "token-test",
        },
    )
    assert generate_denied.status_code == 401

    generate_allowed = client.post(
        "/generate",
        headers={"Authorization": "Bearer secret"},
        json={
            "message": "hello",
            "subsystem": "Auto",
            "session_id": "token-test",
        },
    )
    assert generate_allowed.status_code == 200
