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

    async def get_active_voice(self) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.get("/api/voice/active")
            response.raise_for_status()
            payload = response.json()
            provider_voice_id = payload.get("provider_voice_id")
            if not isinstance(provider_voice_id, str) or not provider_voice_id.strip():
                raise ValueError("Invalid active voice response")
            return payload

    async def search_and_record_unknown(self, question: str) -> dict[str, Any]:
        """Search once and automatically record a no-match with the original wording."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            search_response = await client.post(
                "/api/faq/search", json={"question": question}
            )
            search_response.raise_for_status()
            result = search_response.json()

            if result.get("matched") is True:
                result["unanswered_recorded"] = False
                return result

            try:
                record_response = await client.post(
                    "/api/unanswered", json={"question": question}
                )
                record_response.raise_for_status()
            except (httpx.HTTPError, ValueError):
                result["unanswered_recorded"] = False
                result["recording_error"] = "service_unavailable"
                return result

            recorded = record_response.json()
            result["unanswered_recorded"] = True
            result["unanswered_id"] = recorded.get("id")
            return result
