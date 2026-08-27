import pytest
from sqlalchemy import delete

from app.models import FAQ
from app.seed_data import FAQS


@pytest.fixture()
def catalog(client, db_session):
    db_session.execute(delete(FAQ))
    db_session.add_all(FAQ(**item) for item in FAQS)
    db_session.commit()
    return client


@pytest.mark.parametrize("question", [
    "Does Aurelia allow dogs?",
    "Does Carbone have a wheelchair ramp?",
    "What is Aurelia cancellation policy?",
    "Can I bring a pet to Aurelia?",
    "Does Aurelia provide airport transfers?",
    "What is the dress code at Carbone?",
    "What time does Aurelia open and are dogs allowed?",
    "Does the fitness center offer bicycle repairs?",
])
def test_known_venue_does_not_hide_missing_information(catalog, question):
    response = catalog.post("/api/faq/search", json={"question": question})
    assert response.status_code == 200
    assert response.json()["matched"] is False, response.json()


def test_new_fact_makes_previously_unknown_question_answerable(catalog):
    question = "Does Aurelia allow dogs?"
    assert catalog.post("/api/faq/search", json={"question": question}).json()["matched"] is False
    created = catalog.post("/api/admin/faqs", json={
        "question": "What is the dog policy at Aurelia?",
        "answer": "Dogs are not allowed inside Aurelia.",
        "category": "restaurants",
    })
    assert created.status_code == 201
    response = catalog.post("/api/faq/search", json={"question": question}).json()
    assert response["matched"] is True
    assert response["answer"] == "Dogs are not allowed inside Aurelia."


def test_changed_answer_is_found_without_renaming_seeded_question(catalog):
    spa = next(faq for faq in catalog.get("/api/admin/faqs").json()
               if faq["question"] == "When is Meridian Spa open?")
    changed = catalog.put(f"/api/admin/faqs/{spa['id']}", json={
        "question": spa["question"],
        "answer": "Meridian Spa now offers halotherapy in a salt room from noon to 6 PM.",
        "category": "amenities",
    })
    assert changed.status_code == 200
    found = catalog.post("/api/faq/search", json={"question": "Where can I try halotherapy?"}).json()
    assert found["matched"] is True
    assert found["answer"] == changed.json()["answer"]


def test_dog_policy_is_not_used_as_a_cat_policy(catalog):
    catalog.post("/api/admin/faqs", json={
        "question": "What is the dog policy at Aurelia?",
        "answer": "Dogs are allowed inside Aurelia.",
        "category": "restaurants",
    })
    found = catalog.post("/api/faq/search", json={"question": "Does Aurelia allow cats?"}).json()
    assert found["matched"] is False


@pytest.mark.parametrize(("question", "expected"), [
    ("How much is a Deluxe Room?", "What is included in a Deluxe Room?"),
    ("What are Aurelia prices?", "Tell me about Aurelia."),
    ("What are the opening hours of Aurelia?", "Tell me about Aurelia."),
    ("How much does valet parking cost?", "How much does valet parking cost?"),
])
def test_basic_prices_and_hours_are_supported_by_current_facts(catalog, question, expected):
    result = catalog.post("/api/faq/search", json={"question": question}).json()
    assert result["matched"] is True, result
    assert result["best_match"] == expected
