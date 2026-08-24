from app.models import VoiceConfig


def test_admin_lists_four_voices_in_catalog_order(client):
    response = client.get("/api/admin/voices")

    assert response.status_code == 200
    voices = response.json()
    assert [voice["name"] for voice in voices] == [
        "James",
        "Sofia",
        "Marcus",
        "Elena",
    ]
    assert sum(voice["is_active"] for voice in voices) == 1
    assert "provider_voice_id" not in voices[0]


def test_admin_activates_one_voice(client):
    voices = client.get("/api/admin/voices").json()
    sofia = next(voice for voice in voices if voice["name"] == "Sofia")

    response = client.post(f"/api/admin/voices/{sofia['id']}/activate")

    assert response.status_code == 200
    assert response.json()["name"] == "Sofia"
    assert response.json()["is_active"] is True
    refreshed = client.get("/api/admin/voices").json()
    assert sum(voice["is_active"] for voice in refreshed) == 1


def test_internal_active_voice_exposes_only_agent_runtime_fields(client):
    response = client.get("/api/voice/active")

    assert response.status_code == 200
    assert set(response.json()) == {"name", "provider_voice_id", "updated_at"}


def test_voice_preview_streams_mp3(client):
    james = client.get("/api/admin/voices").json()[0]

    response = client.get(f"/api/admin/voices/{james['id']}/preview")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert len(response.content) > 1_000


def test_missing_voice_activation_returns_404(client):
    response = client.post("/api/admin/voices/999999/activate")

    assert response.status_code == 404
    assert response.json() == {"detail": "Voice not found"}


def test_missing_voice_preview_returns_404(client):
    response = client.get("/api/admin/voices/999999/preview")

    assert response.status_code == 404
    assert response.json() == {"detail": "Voice not found"}


def test_missing_preview_asset_returns_404(client, db_session):
    james = db_session.query(VoiceConfig).filter_by(name="James").one()
    james.preview_path = "voice-previews/missing.mp3"
    db_session.commit()

    response = client.get(f"/api/admin/voices/{james.id}/preview")

    assert response.status_code == 404
    assert response.json() == {"detail": "Voice not found"}


def test_invalid_active_voice_state_returns_503(client, db_session):
    for voice in db_session.query(VoiceConfig):
        voice.is_active = False
    db_session.commit()

    response = client.get("/api/voice/active")

    assert response.status_code == 503
    assert response.json() == {"detail": "Active voice is unavailable"}
