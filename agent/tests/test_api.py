import asyncio

import httpx

from app.api import ConciergeAPI
from app.main import SYSTEM_INSTRUCTIONS


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


def test_agent_translates_search_query_but_preserves_unknown_wording():
    assert "translate the guest's complete question into Ukrainian" in SYSTEM_INSTRUCTIONS
    assert "guest's original wording" in SYSTEM_INSTRUCTIONS
