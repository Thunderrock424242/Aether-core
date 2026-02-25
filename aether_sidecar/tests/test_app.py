from fastapi.testclient import TestClient

from aether_sidecar.app import app


client = TestClient(app)


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


def test_metrics_endpoint_available():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "aether_http_requests_total" in response.text
