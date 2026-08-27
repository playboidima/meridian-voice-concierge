import pytest

from app.seed_data import FAQS
from app.services.embeddings import faq_embedding_text, embed_faq
from app.models import FAQ


@pytest.mark.parametrize("faq", FAQS, ids=lambda faq: faq["question"])
def test_embedding_uses_current_answer_and_category(faq):
    original = faq_embedding_text(faq["question"], faq["answer"], faq["category"])
    changed_answer = faq_embedding_text(
        faq["question"], "This service is permanently closed.", faq["category"]
    )
    changed_category = faq_embedding_text(faq["question"], faq["answer"], "updated-category")

    assert changed_answer != original
    assert "This service is permanently closed." in changed_answer
    assert changed_category != original
    assert "updated-category" in changed_category
    assert faq["question"] in original


def test_closed_spa_embedding_does_not_include_old_opening_hours():
    passage = faq_embedding_text(
        "When is Meridian Spa open?", "The spa is permanently closed.", "closed"
    )
    assert "The spa is permanently closed." in passage
    assert "8 AM to 8 PM" not in passage
    assert "Book 24 hours ahead" not in passage


def test_admin_answer_only_edit_changes_persisted_embedding(client, db_session):
    values = next(item for item in FAQS if item["question"] == "When is Meridian Spa open?")
    faq = FAQ(**values)
    faq.embedding = embed_faq(faq)
    db_session.add(faq)
    db_session.commit()
    original = list(faq.embedding)

    response = client.put(
        f"/api/admin/faqs/{faq.id}",
        json={**values, "answer": "The spa is permanently closed."},
    )

    assert response.status_code == 200
    db_session.refresh(faq)
    assert len(faq.embedding) == 384
    assert list(faq.embedding) != original
    assert faq.question == values["question"]
    assert faq.answer == "The spa is permanently closed."
