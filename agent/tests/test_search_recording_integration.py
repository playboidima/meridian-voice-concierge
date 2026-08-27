"""Opt-in real backend round trip, never target the user's working database."""

import asyncio
import os
from urllib.parse import urlparse

import httpx
import pytest

from app.api import ConciergeAPI


URL = os.getenv("SEARCH_TEST_BACKEND_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="Requires an isolated search-test backend")


@pytest.mark.parametrize("question", [
    "Does Aurelia allow dogs?",
    "Does Carbone have a wheelchair ramp?",
    "What is Aurelia cancellation policy?",
])
def test_real_no_match_is_recorded_with_original_wording_and_frequency(question):
    assert urlparse(URL).hostname == "meridian-search-audit-backend", "Refusing a non-test backend"
    api = ConciergeAPI(URL, timeout_seconds=30)
    before = httpx.get(f"{URL}/api/admin/unanswered", timeout=30).json()
    previous_frequency = next((item["frequency"] for item in before
                               if item["original_question"] == question), 0)
    first = asyncio.run(api.search_and_record_unknown(question))
    second = asyncio.run(api.search_and_record_unknown(question))
    assert first["matched"] is False
    assert first["unanswered_recorded"] is True
    assert first["unanswered_id"] == second["unanswered_id"]
    queue = httpx.get(f"{URL}/api/admin/unanswered", timeout=30).json()
    item = next(item for item in queue if item["id"] == first["unanswered_id"])
    assert item["original_question"] == question
    assert item["frequency"] == previous_frequency + 2


def test_real_known_question_is_not_recorded():
    assert urlparse(URL).hostname == "meridian-search-audit-backend", "Refusing a non-test backend"
    before = httpx.get(f"{URL}/api/admin/unanswered", timeout=30).json()
    result = asyncio.run(ConciergeAPI(URL, timeout_seconds=30).search_and_record_unknown(
        "Where can I eat near the hotel?"
    ))
    assert result["matched"] is True
    assert "Carbone" in result["answer"]
    assert result["unanswered_recorded"] is False
    assert httpx.get(f"{URL}/api/admin/unanswered", timeout=30).json() == before
