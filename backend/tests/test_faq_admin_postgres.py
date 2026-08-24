import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import FAQ


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_INTEGRATION") != "1",
    reason="Set RUN_POSTGRES_INTEGRATION=1 to test the running PostgreSQL stack.",
)

BACKEND_URL = os.getenv("INTEGRATION_BACKEND_URL", "http://backend:8000")
DATABASE_URL = os.getenv(
    "INTEGRATION_DATABASE_URL",
    "postgresql+psycopg://meridian:change-me@db:5432/meridian",
)


@pytest.mark.postgres_integration
def test_admin_faq_lifecycle_is_searchable_and_persists_384_dimension_embeddings():
    token = uuid4()
    original_question = f"zzzmeridian {token} original question"
    updated_question = f"zzzmeridian {token} updated question"
    original_answer = f"Original answer for {token}"
    updated_answer = f"Updated answer for {token}"
    engine = create_engine(DATABASE_URL)
    faq_id = None
    created_id = None

    try:
        create_response = httpx.post(
            f"{BACKEND_URL}/api/admin/faqs",
            json={
                "question": original_question,
                "answer": original_answer,
                "category": "integration",
            },
            timeout=30,
        )
        assert create_response.status_code == 201, create_response.text
        faq_id = create_response.json()["id"]
        created_id = faq_id

        original_search = httpx.post(
            f"{BACKEND_URL}/api/faq/search",
            json={"question": original_question},
            timeout=30,
        )
        assert original_search.status_code == 200, original_search.text
        assert original_search.json()["answer"] == original_answer

        with Session(engine) as db:
            assert db.scalar(
                select(func.vector_dims(FAQ.embedding)).where(FAQ.id == faq_id)
            ) == 384

        update_response = httpx.put(
            f"{BACKEND_URL}/api/admin/faqs/{faq_id}",
            json={
                "question": updated_question,
                "answer": updated_answer,
                "category": "integration",
            },
            timeout=30,
        )
        assert update_response.status_code == 200, update_response.text

        updated_search = httpx.post(
            f"{BACKEND_URL}/api/faq/search",
            json={"question": updated_question},
            timeout=30,
        )
        assert updated_search.status_code == 200, updated_search.text
        assert updated_search.json()["answer"] == updated_answer

        with Session(engine) as db:
            assert db.scalar(
                select(func.vector_dims(FAQ.embedding)).where(FAQ.id == faq_id)
            ) == 384

        delete_response = httpx.delete(
            f"{BACKEND_URL}/api/admin/faqs/{faq_id}", timeout=30
        )
        assert delete_response.status_code == 204, delete_response.text
        faq_id = None
    finally:
        if faq_id is not None:
            cleanup_response = httpx.delete(
                f"{BACKEND_URL}/api/admin/faqs/{faq_id}", timeout=30
            )
            assert cleanup_response.status_code == 204, cleanup_response.text
        if created_id is not None:
            with Session(engine) as db:
                assert db.get(FAQ, created_id) is None
        engine.dispose()
