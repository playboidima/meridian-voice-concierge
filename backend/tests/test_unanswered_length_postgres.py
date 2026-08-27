import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models import FAQ
from test_seed_persistence_postgres import seed_database  # noqa: F401


pytestmark = pytest.mark.skipif(
    not os.getenv("SEED_TEST_DATABASE_URL"),
    reason="Requires the disposable meridian_seed_test PostgreSQL database.",
)


@pytest.mark.parametrize("length", [500, 501, 1000])
def test_long_unanswered_question_can_be_converted_and_edited(seed_database, monkeypatch, length):
    engine, migrate = seed_database
    migrate()
    monkeypatch.setattr("app.services.embeddings.embed_passage", lambda _: [0.1] * 384)
    question = "q" * length
    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                unknown = client.post("/api/unanswered", json={"question": question})
                assert unknown.status_code == 200
                response = client.post(f"/api/admin/unanswered/{unknown.json()['id']}/convert",
                                       json={"answer": "Boundary test answer.", "category": "test"})
                assert response.status_code == 201
                assert response.json()["question"] == question
                faq_id = response.json()["id"]
                edited = client.put(f"/api/admin/faqs/{faq_id}", json={
                    "question": question, "answer": "Updated boundary answer.", "category": "test",
                })
                assert edited.status_code == 200
                assert client.get("/api/admin/unanswered").json() == []
                assert db.scalar(select(FAQ.question).where(FAQ.id == faq_id)) == question
        finally:
            app.dependency_overrides.pop(get_db, None)


def test_question_length_migration_preserves_existing_content_and_refuses_lossy_downgrade(seed_database):
    engine, migrate = seed_database
    migrate("20260827_05")
    with Session(engine) as db:
        faq = FAQ(question="q" * 500, answer="Preserved answer", category="test")
        db.add(faq)
        db.commit()
        original = (faq.id, faq.question, faq.answer, faq.created_at, faq.updated_at)
    migrate()
    with Session(engine) as db:
        faq = db.get(FAQ, original[0])
        assert (faq.id, faq.question, faq.answer, faq.created_at, faq.updated_at) == original
        faq.question = "q" * 1000
        db.commit()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "20260827_05"],
        env={**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False)},
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "longer than 500" in result.stderr
    with Session(engine) as db:
        assert db.get(FAQ, original[0]).question == "q" * 1000
