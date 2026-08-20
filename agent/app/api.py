from typing import Any

import httpx


class ConciergeAPI:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)

    async def search_faq(self, question: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.post("/api/faq/search", json={"question": question})
            response.raise_for_status()
            return response.json()

    async def record_unanswered(self, question: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.post("/api/unanswered", json={"question": question})
            response.raise_for_status()
            return response.json()

