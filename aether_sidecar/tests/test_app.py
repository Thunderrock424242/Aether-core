from fastapi.testclient import TestClient

from aether_sidecar import app as app_module
from aether_sidecar.backends import BackendAttemptSummary, BackendUnavailableError
from aether_sidecar.config import settings

activation_registry = app_module.activation_registry
app = app_module.app
learning = app_module.learning


client = TestClient(app)


class FakeBackend:
    async def warmup(self, subsystem):
        return f"fake-{subsystem.value.lower()}"

    def connection_attempt_chain(self):
        return ["http://127.0.0.1:11434/api/generate", "http://localhost:11434/api/generate"]

    async def generate(self, prompt: str, subsystem):
        scope = "general" if "Request scope: general-conversation" in prompt else "minecraft"
        return f"[{scope}] simulated model response", f"fake-{subsystem.value.lower()}", BackendAttemptSummary()


def setup_function() -> None:
    activation_registry.active_instances.clear()
    learning._lessons.clear()
    settings.activation_hook_enabled = False
    settings.activation_hook_token = None
    settings.dev_playground_enabled = False
    settings.dev_playground_token = None
    settings.ollama_keep_alive = "15m"
    app_module.backend = FakeBackend()


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
    assert "aether_backend_attempts_total" in response.text
    assert "aether_backend_attempt_latency_seconds" in response.text
    assert "aether_generate_fallback_hops" in response.text


def test_health_returns_keep_alive_setting():
    settings.ollama_keep_alive = "30m"

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["keep_alive"] == "30m"




def test_status_reports_model_online_with_runtime_details():
    response = client.get("/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"]["status"] == "online"
    assert body["model"]["checked_model"] == "fake-aegis"
    assert body["model"]["attempted_urls"] == ["http://127.0.0.1:11434/api/generate", "http://localhost:11434/api/generate"]
    assert body["uptime_seconds"] >= 0


def test_status_reports_model_offline_when_backend_unavailable():
    class BrokenBackend:
        async def warmup(self, subsystem):
            raise BackendUnavailableError("backend down")

    app_module.backend = BrokenBackend()

    response = client.get("/status")

    assert response.status_code == 200
    body = response.json()
    assert body["model"]["status"] == "offline"
    assert body["model"]["detail"] == "backend down"
    assert body["model"]["attempted_urls"] == []



def test_status_handles_invalid_connection_attempt_chain_payload():
    class WeirdBackend:
        async def warmup(self, subsystem):
            return "weird-model"

        def connection_attempt_chain(self):
            return "not-a-list"

    app_module.backend = WeirdBackend()

    response = client.get("/status")

    assert response.status_code == 200
    assert response.json()["model"]["attempted_urls"] == []

def test_backend_warmup_endpoint_returns_ready():
    response = client.post("/backend/warmup", params={"subsystem": "Terra"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["model_name"] == "fake-terra"
    assert body["subsystem"] == "Terra"


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


def test_generate_allows_dev_playground_bypass_when_enabled():
    settings.activation_hook_enabled = True
    settings.dev_playground_enabled = True

    response = client.post(
        "/generate",
        headers={"X-Aether-Dev-Playground": "true"},
        json={
            "message": "hello from playground",
            "subsystem": "Auto",
            "session_id": "test-session-playground-bypass",
        },
    )

    assert response.status_code == 200


def test_generate_does_not_bypass_activation_without_playground_header():
    settings.activation_hook_enabled = True
    settings.dev_playground_enabled = True

    response = client.post(
        "/generate",
        json={
            "message": "hello",
            "subsystem": "Auto",
            "session_id": "test-session-no-bypass",
        },
    )

    assert response.status_code == 503


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
    assert "Teach the current message before sending it to chat" in response.text
    assert "Conversation" in response.text


def test_root_redirects_to_generate_ui():
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/generate"


def test_generate_get_serves_chat_page():
    response = client.get("/generate")

    assert response.status_code == 200
    assert "A.E.T.H.E.R Chat" in response.text
    assert "API clients can POST to" in response.text


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


def test_generate_returns_503_when_model_backend_unavailable():
    class DownBackend:
        async def warmup(self, subsystem):
            raise BackendUnavailableError("backend offline")

        async def generate(self, prompt: str, subsystem):
            raise BackendUnavailableError("backend offline")

    app_module.backend = DownBackend()

    response = client.post(
        "/generate",
        json={
            "message": "hello",
            "subsystem": "Auto",
            "session_id": "backend-down",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "backend offline"


def test_warmup_returns_503_when_model_backend_unavailable():
    class DownBackend:
        async def warmup(self, subsystem):
            raise BackendUnavailableError("backend offline")

        async def generate(self, prompt: str, subsystem):
            raise BackendUnavailableError("backend offline")

    app_module.backend = DownBackend()

    response = client.post("/backend/warmup")

    assert response.status_code == 503
    assert response.json()["detail"] == "backend offline"


def test_heath_redirects_to_status():
    response = client.get("/heath", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/status"
