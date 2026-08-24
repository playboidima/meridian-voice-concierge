import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.models import UnansweredQuestion
from app.services.text import normalize_question


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_INTEGRATION") != "1",
    reason="Set RUN_POSTGRES_INTEGRATION=1 to test the running PostgreSQL stack.",
)

BACKEND_URL = os.getenv("INTEGRATION_BACKEND_URL", "http://backend:8000")
DATABASE_URL = os.getenv(
    "INTEGRATION_DATABASE_URL",
    "postgresql+psycopg://meridian:change-me@db:5432/meridian",
)


def test_concurrent_duplicate_questions_increment_frequency_atomically():
    request_count = 50
    question = f"Concurrency test unknown question {uuid4()}"
    normalized = normalize_question(question)
    barrier = Barrier(request_count)
    engine = create_engine(DATABASE_URL)

    def submit_question() -> int:
        barrier.wait()
        response = httpx.post(
            f"{BACKEND_URL}/api/unanswered",
            json={"question": question},
            timeout=20,
        )
        return response.status_code

    try:
        with ThreadPoolExecutor(max_workers=request_count) as executor:
            status_codes = list(executor.map(lambda _: submit_question(), range(request_count)))

        assert status_codes == [200] * request_count

        with Session(engine) as db:
            item = db.scalar(
                select(UnansweredQuestion).where(
                    UnansweredQuestion.normalized_question == normalized
                )
            )
            assert item is not None
            assert item.frequency == request_count
    finally:
        with Session(engine) as db:
            db.execute(
                delete(UnansweredQuestion).where(
                    UnansweredQuestion.normalized_question == normalized
                )
            )
            db.commit()
        engine.dispose()
