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
