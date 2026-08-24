import base64
import json

from app.config import settings


def decode_jwt_payload(token: str) -> dict:
    encoded = token.split(".")[1]
    encoded += "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(encoded))


def configure_livekit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "livekit_url", "wss://example.livekit.cloud")
    monkeypatch.setattr(settings, "livekit_api_key", "test-key")
    monkeypatch.setattr(
        settings,
        "livekit_api_secret",
        "test-secret-at-least-thirty-two-bytes",
    )
    monkeypatch.setattr(settings, "agent_name", "meridian-concierge")


def test_token_endpoint_returns_503_when_livekit_is_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "livekit_url", "")
    monkeypatch.setattr(settings, "livekit_api_key", "")
    monkeypatch.setattr(settings, "livekit_api_secret", "")

    response = client.post("/api/livekit/token", json={})

    assert response.status_code == 503
    assert response.json() == {"detail": "LiveKit is not configured"}
    assert "secret" not in response.text.lower()


def test_token_endpoint_returns_short_lived_room_scoped_credentials(client, monkeypatch):
    configure_livekit(monkeypatch)

    response = client.post("/api/livekit/token", json={})

    assert response.status_code == 201
    assert set(response.json()) == {"server_url", "participant_token"}
    assert response.json()["server_url"] == "wss://example.livekit.cloud"
    payload = decode_jwt_payload(response.json()["participant_token"])
    assert payload["sub"].startswith("tester-")
    assert 0 < payload["exp"] - payload["nbf"] <= 600
    assert payload["video"]["room"].startswith("playground-")
    assert payload["video"]["roomJoin"] is True
    assert payload["video"]["canPublish"] is True
    assert payload["video"]["canSubscribe"] is True


def test_token_endpoint_generates_unique_default_sessions(client, monkeypatch):
    configure_livekit(monkeypatch)

    first = decode_jwt_payload(
        client.post("/api/livekit/token", json={}).json()["participant_token"]
    )
    second = decode_jwt_payload(
        client.post("/api/livekit/token", json={}).json()["participant_token"]
    )

    assert first["sub"] != second["sub"]
    assert first["video"]["room"] != second["video"]["room"]


def test_token_endpoint_preserves_agent_dispatch_configuration(client, monkeypatch):
    configure_livekit(monkeypatch)
    room_config = {
        "agents": [
            {
                "agent_name": "meridian-concierge",
                "metadata": "playground",
            }
        ]
    }

    response = client.post(
        "/api/livekit/token",
        json={"room_name": "review-room", "room_config": room_config},
    )

    assert response.status_code == 201
    payload = decode_jwt_payload(response.json()["participant_token"])
    assert payload["video"]["room"] == "review-room"
    assert payload["roomConfig"] == {
        "agents": [
            {
                "agentName": "meridian-concierge",
                "metadata": "playground",
            }
        ]
    }
