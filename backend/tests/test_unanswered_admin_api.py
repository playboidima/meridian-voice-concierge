from sqlalchemy import select

from app.models import FAQ, UnansweredQuestion


def add_unanswered(db_session, question: str, frequency: int) -> UnansweredQuestion:
    item = UnansweredQuestion(
        original_question=question,
        normalized_question=question.lower(),
        frequency=frequency,
        status="open",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_admin_unanswered_queue_lists_open_questions_by_frequency(client, db_session):
    lower = add_unanswered(db_session, "Lower priority question", 2)
    higher = add_unanswered(db_session, "Higher priority question", 5)
    dismissed = add_unanswered(db_session, "Already dismissed", 10)
    dismissed.status = "dismissed"
    db_session.commit()

    response = client.get("/api/admin/unanswered")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [higher.id, lower.id]
    assert response.json()[0]["frequency"] == 5
    assert all(item["status"] == "open" for item in response.json())


def test_admin_can_dismiss_an_unanswered_question(client, db_session):
    item = add_unanswered(db_session, "Irrelevant question", 1)

    response = client.post(f"/api/admin/unanswered/{item.id}/dismiss")

    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"
    db_session.refresh(item)
    assert item.status == "dismissed"
    assert client.get("/api/admin/unanswered").json() == []


def test_admin_can_convert_an_unanswered_question_to_faq(
    client, db_session, monkeypatch
):
    item = add_unanswered(db_session, "  Is airport transfer available?  ", 3)
    embedding = [0.4] * 384
    monkeypatch.setattr("app.services.embeddings.embed_passage", lambda _: embedding)

    response = client.post(
        f"/api/admin/unanswered/{item.id}/convert",
        json={"answer": "  Airport transfers can be arranged.  ", "category": "  hotel  "},
    )

    assert response.status_code == 201
    assert response.json()["question"] == "Is airport transfer available?"
    assert response.json()["answer"] == "Airport transfers can be arranged."
    assert response.json()["category"] == "hotel"
    assert "embedding" not in response.json()
    db_session.refresh(item)
    assert item.status == "converted"
    faq = db_session.scalar(
        select(FAQ).where(FAQ.question == "Is airport transfer available?")
    )
    assert faq is not None
    assert faq.embedding == embedding


def test_admin_unanswered_actions_return_not_found(client):
    dismiss = client.post("/api/admin/unanswered/9999/dismiss")
    convert = client.post(
        "/api/admin/unanswered/9999/convert",
        json={"answer": "Valid answer", "category": "hotel"},
    )

    assert dismiss.status_code == 404
    assert dismiss.json() == {"detail": "Unanswered question not found"}
    assert convert.status_code == 404
    assert convert.json() == {"detail": "Unanswered question not found"}


def test_convert_duplicate_faq_rolls_back_unanswered_status(
    client, db_session, monkeypatch
):
    item = add_unanswered(
        db_session,
        "Коли працює покерна кімната і які ігри доступні?",
        2,
    )
    monkeypatch.setattr("app.services.embeddings.embed_passage", lambda _: [0.4] * 384)

    response = client.post(
        f"/api/admin/unanswered/{item.id}/convert",
        json={"answer": "Duplicate", "category": "casino"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "FAQ question already exists"}
    db_session.refresh(item)
    assert item.status == "open"
