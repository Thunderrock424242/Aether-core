from fastapi.testclient import TestClient

from aether_sidecar.app import activation_registry, app, learning
from aether_sidecar.config import settings


client = TestClient(app)


def setup_function() -> None:
    activation_registry.active_instances.clear()
    learning._lessons.clear()
    settings.activation_hook_enabled = False
    settings.activation_hook_token = None


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
    assert body["model_used"] == "aether-template-v1"


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
