def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_faq_search_returns_match(client):
    response = client.post("/api/faq/search", json={"question": "Покерна кімната зараз відкрита?"})
    body = response.json()
    assert response.status_code == 200
    assert body["matched"] is True
    assert body["category"] == "casino"
    assert "24/7" in body["answer"]


def test_faq_search_matches_english_question(client):
    response = client.post("/api/faq/search", json={"question": "Is poker room open right now?"})
    body = response.json()
    assert response.status_code == 200
    assert body["matched"] is True
    assert "24/7" in body["answer"]


def test_faq_search_returns_no_match(client):
    response = client.post("/api/faq/search", json={"question": "Де купити синій велосипед?"})
    assert response.status_code == 200
    assert response.json()["matched"] is False


def test_unanswered_is_normalized_and_aggregated(client):
    first = client.post("/api/unanswered", json={"question": "Чи можна приїхати із собакою?"})
    second = client.post("/api/unanswered", json={"question": "  Чи можна приїхати із собакою?! "})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["frequency"] == 2


def test_question_validation(client):
    response = client.post("/api/faq/search", json={"question": "?"})
    assert response.status_code == 422
