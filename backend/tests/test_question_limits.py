import pytest


@pytest.mark.parametrize("path", ["/api/unanswered", "/api/faq/search", "/api/admin/faqs"])
def test_api_rejects_question_over_1000_characters(client, path):
    response = client.post(path, json={
        "question": "q" * 1001, "answer": "Test answer", "category": "test",
    })
    assert response.status_code == 422
    assert any(error["loc"] == ["body", "question"] for error in response.json()["detail"])
