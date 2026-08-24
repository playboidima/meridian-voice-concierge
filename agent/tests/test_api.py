import asyncio

import httpx

from app.api import ConciergeAPI
from app.main import MeridianConcierge, SYSTEM_INSTRUCTIONS


def test_search_faq(monkeypatch):
    original_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/faq/search"
        return httpx.Response(200, json={"matched": True, "answer": "Працює 24/7"})

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )
    result = asyncio.run(
        ConciergeAPI("http://backend:8000").search_faq("Коли ви працюєте?")
    )
    assert result["matched"] is True


def test_record_unanswered(monkeypatch):
    original_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/unanswered"
        return httpx.Response(200, json={"id": 7, "frequency": 1})

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )
    result = asyncio.run(
        ConciergeAPI("http://backend:8000").record_unanswered("Нове питання")
    )
    assert result["id"] == 7


def test_agent_preserves_original_wording_for_bilingual_search():
    assert "guest's original complete" in SYSTEM_INSTRUCTIONS
    assert "Never translate a guest question" in SYSTEM_INSTRUCTIONS
    assert "repeat the question in English" in SYSTEM_INSTRUCTIONS
    assert "guest's original wording" in SYSTEM_INSTRUCTIONS


def test_known_faq_is_not_recorded(monkeypatch):
    original_client = httpx.AsyncClient
    requested_paths = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(200, json={"matched": True, "answer": "Open 24/7"})

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )

    result = asyncio.run(
        ConciergeAPI("http://backend:8000").search_and_record_unknown(
            "Is the poker room open?"
        )
    )

    assert requested_paths == ["/api/faq/search"]
    assert result["matched"] is True
    assert result["unanswered_recorded"] is False


def test_unknown_faq_is_recorded_once_with_original_wording(monkeypatch):
    original_client = httpx.AsyncClient
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.url.path, request.content))
        if request.url.path == "/api/faq/search":
            return httpx.Response(200, json={"matched": False, "score": 0.1})
        return httpx.Response(200, json={"id": 12, "frequency": 1})

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )
    question = "Do you offer airport transportation?"

    result = asyncio.run(
        ConciergeAPI("http://backend:8000").search_and_record_unknown(question)
    )

    assert [path for path, _ in requests] == [
        "/api/faq/search",
        "/api/unanswered",
    ]
    assert requests[0][1] == requests[1][1]
    assert question.encode() in requests[1][1]
    assert result["matched"] is False
    assert result["unanswered_recorded"] is True
    assert result["unanswered_id"] == 12


def test_unknown_search_does_not_claim_recording_when_record_api_fails(monkeypatch):
    original_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/faq/search":
            return httpx.Response(200, json={"matched": False, "score": 0.1})
        return httpx.Response(503, json={"detail": "temporarily unavailable"})

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )

    result = asyncio.run(
        ConciergeAPI("http://backend:8000").search_and_record_unknown(
            "Do you offer airport transportation?"
        )
    )

    assert result["matched"] is False
    assert result["unanswered_recorded"] is False
    assert result["recording_error"] == "service_unavailable"


def test_llm_has_no_separate_unanswered_recording_tool():
    assert not hasattr(MeridianConcierge, "record_unanswered_question")
    assert "automatically records" in SYSTEM_INSTRUCTIONS
    assert "do not claim that it was recorded" in SYSTEM_INSTRUCTIONS
