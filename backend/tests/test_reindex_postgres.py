import os

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import reindex_faqs as module
from app.models import FAQ
from app.services.faq_search import find_best_faq
from test_seed_persistence_postgres import seed_database  # noqa: F401


pytestmark = pytest.mark.skipif(
    not os.getenv("SEED_TEST_DATABASE_URL"),
    reason="Requires the disposable meridian_seed_test PostgreSQL database.",
)


def test_postgres_reindex_preserves_content_and_searches_current_answer(seed_database, monkeypatch):
    engine, migrate = seed_database
    migrate()
    monkeypatch.setattr(module, "engine", engine)
    columns = [FAQ.id, FAQ.question, FAQ.answer, FAQ.category, FAQ.created_at, FAQ.updated_at]
    with Session(engine) as db:
        db.add(FAQ(question="When is Meridian Spa open?",
                   answer="The spa offers halotherapy in a salt room from noon to 6 PM.",
                   category="amenities", embedding=[0.01] * 384))
        db.commit()
        before = db.execute(select(*columns).order_by(FAQ.id)).all()
    assert module.reindex_faqs() == 1
    with Session(engine) as db:
        assert db.execute(select(*columns).order_by(FAQ.id)).all() == before
        faq, score = find_best_faq(db, "Where can I try halotherapy?")
        assert faq is not None
        assert score >= .35
        assert "halotherapy" in faq.answer
        assert len(faq.embedding) == 384
        assert list(faq.embedding) != [0.01] * 384


def test_postgres_reindex_failure_keeps_old_vectors(seed_database, monkeypatch):
    engine, migrate = seed_database
    migrate()
    monkeypatch.setattr(module, "engine", engine)
    with Session(engine) as db:
        for i in range(2):
            db.add(FAQ(question=f"Custom question {i}?", answer="Custom answer.",
                       category="custom", embedding=[0.01] * 384))
        db.commit()
        ids = list(db.scalars(select(FAQ.id).order_by(FAQ.id)))

    def fail_second(faq):
        if faq.id == ids[1]:
            raise RuntimeError("Embedding failure")
        return [0.5] * 384

    monkeypatch.setattr(module, "embed_faq", fail_second)
    with pytest.raises(RuntimeError, match="Embedding failure"):
        module.reindex_faqs()
    with Session(engine) as db:
        for faq in db.scalars(select(FAQ)):
            assert float(faq.embedding[0]) == pytest.approx(.01)
