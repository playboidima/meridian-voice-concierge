import pytest

from sqlalchemy import select

from app.models import FAQ
from app.schemas import FAQAdminWrite


def test_admin_faq_list_is_sorted_and_hides_embedding(client):
    response = client.get("/api/admin/faqs")
    body = response.json()

    assert response.status_code == 200
    assert [item["id"] for item in body] == sorted(item["id"] for item in body)
    assert body
    assert "embedding" not in body[0]
    assert set(body[0]) == {
        "id", "question", "answer", "category", "created_at", "updated_at"
    }


def test_admin_faq_write_strips_fields_and_rejects_blank_values():
    payload = FAQAdminWrite(
        question="  Is breakfast available?  ",
        answer="  Breakfast is served daily.  ",
        category="  dining  ",
    )
    assert payload.question == "Is breakfast available?"
    assert payload.answer == "Breakfast is served daily."
    assert payload.category == "dining"


def test_admin_can_create_faq_with_a_persisted_embedding(client, db_session, monkeypatch):
    embedding = [0.25] * 384
    monkeypatch.setattr("app.services.embeddings.embed_passage", lambda _: embedding)

    response = client.post(
        "/api/admin/faqs",
        json={
            "question": "  Is late checkout available?  ",
            "answer": "  Late checkout is subject to availability.  ",
            "category": "  hotel  ",
        },
    )

    assert response.status_code == 201
    assert set(response.json()) == {
        "id", "question", "answer", "category", "created_at", "updated_at"
    }
    assert "embedding" not in response.json()
    assert response.json()["question"] == "Is late checkout available?"
    assert response.json()["answer"] == "Late checkout is subject to availability."
    assert response.json()["category"] == "hotel"

    faq = db_session.scalar(select(FAQ).where(FAQ.id == response.json()["id"]))
    assert faq is not None
    assert faq.embedding == embedding


def test_admin_create_rejects_duplicate_question(client, monkeypatch):
    monkeypatch.setattr("app.services.embeddings.embed_passage", lambda _: [0.25] * 384)

    response = client.post(
        "/api/admin/faqs",
        json={
            "question": "Коли працює покерна кімната і які ігри доступні?",
            "answer": "A duplicate answer.",
            "category": "casino",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "FAQ question already exists"}


@pytest.mark.parametrize(
    "payload",
    [
        {"question": " ", "answer": "Valid answer", "category": "hotel"},
        {"question": "Valid question", "answer": " ", "category": "hotel"},
        {"question": "Valid question", "answer": "Valid answer", "category": " "},
    ],
)
def test_admin_faq_rejects_blank_fields(client, payload):
    response = client.post(
        "/api/admin/faqs",
        json=payload,
    )

    assert response.status_code == 422
