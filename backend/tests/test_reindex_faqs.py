from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import FAQ


def snapshot(db):
    return [(faq.id, faq.question, faq.answer, faq.category, faq.created_at, faq.updated_at)
            for faq in db.scalars(select(FAQ).order_by(FAQ.id))]


def test_reindex_changes_only_vectors_and_uses_current_answers(db_session, monkeypatch):
    from app import reindex_faqs as module

    fixed_time = datetime(2020, 1, 2, 3, 4, 5)
    for faq in db_session.scalars(select(FAQ)):
        faq.embedding = [0.1] * 384
        faq.updated_at = fixed_time
    db_session.commit()
    before = snapshot(db_session)
    monkeypatch.setattr(module, "engine", db_session.get_bind())

    def vector_for_current_faq(faq):
        assert faq.answer in {row[2] for row in before}
        return [0.2] * 384

    monkeypatch.setattr(module, "embed_faq", vector_for_current_faq)
    assert module.reindex_faqs() == 2
    db_session.expire_all()
    assert snapshot(db_session) == before
    assert all(list(faq.embedding) == [0.2] * 384 for faq in db_session.scalars(select(FAQ)))


def test_reindex_rolls_back_every_vector_on_failure(db_session, monkeypatch):
    from app import reindex_faqs as module

    for faq in db_session.scalars(select(FAQ)):
        faq.embedding = [0.1] * 384
    db_session.commit()
    before = snapshot(db_session)
    monkeypatch.setattr(module, "engine", db_session.get_bind())
    first_id = before[0][0]

    def unavailable_after_first(faq):
        if faq.id != first_id:
            raise RuntimeError("Model unavailable")
        return [0.2] * 384

    monkeypatch.setattr(module, "embed_faq", unavailable_after_first)
    with pytest.raises(RuntimeError, match="Model unavailable"):
        module.reindex_faqs()
    db_session.expire_all()
    assert snapshot(db_session) == before
    assert all(list(faq.embedding) == [0.1] * 384 for faq in db_session.scalars(select(FAQ)))
