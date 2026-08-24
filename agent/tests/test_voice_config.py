import asyncio

import httpx

from app.api import ConciergeAPI
from app.main import build_session, resolve_voice_id


def test_api_get_active_voice_validates_provider_id(monkeypatch):
    original_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/voice/active"
        return httpx.Response(
            200,
            json={
                "name": "James",
                "provider_voice_id": "voice-james",
                "updated_at": "2026-08-24T12:00:00Z",
            },
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )

    result = asyncio.run(ConciergeAPI("http://backend:8000").get_active_voice())

    assert result["provider_voice_id"] == "voice-james"


def test_resolve_voice_uses_backend_provider_id():
    class API:
        async def get_active_voice(self):
            return {"name": "Sofia", "provider_voice_id": "voice-sofia"}

    assert asyncio.run(resolve_voice_id(API(), "fallback")) == "voice-sofia"


def test_resolve_voice_falls_back_when_backend_fails():
    class API:
        async def get_active_voice(self):
            raise httpx.ConnectError("offline")

    assert asyncio.run(resolve_voice_id(API(), "fallback")) == "fallback"


def test_resolve_voice_falls_back_when_backend_payload_is_invalid():
    class API:
        async def get_active_voice(self):
            raise ValueError("Invalid active voice response")

    assert asyncio.run(resolve_voice_id(API(), "fallback")) == "fallback"


def test_each_new_session_uses_the_latest_backend_voice(monkeypatch):
    voices = iter(("voice-james", "voice-sofia"))
    tts_arguments = []

    class API:
        async def get_active_voice(self):
            return {"name": "test", "provider_voice_id": next(voices)}

    monkeypatch.setattr(
        "app.main.inference.TTS",
        lambda **kwargs: tts_arguments.append(kwargs) or ("tts", kwargs),
    )
    monkeypatch.setattr("app.main.inference.STT", lambda **kwargs: "stt")
    monkeypatch.setattr("app.main.inference.LLM", lambda **kwargs: "llm")
    monkeypatch.setattr("app.main.inference.TurnDetector", lambda: "turn-detector")
    monkeypatch.setattr("app.main.AgentSession", lambda **kwargs: kwargs)

    asyncio.run(build_session(API(), "fallback"))
    asyncio.run(build_session(API(), "fallback"))

    assert [arguments["voice"] for arguments in tts_arguments] == [
        "voice-james",
        "voice-sofia",
    ]
