from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import FAQ
from app.seed_data import FAQS
from app.services.faq_search import find_best_faq


def populated_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all(FAQ(**item) for item in FAQS)
    session.commit()
    return session


def test_four_known_prd_scenarios_match_expected_faqs():
    session = populated_session()
    cases = {
        "Покерна кімната зараз відкрита?": "покерна кімната",
        "Який у вас найкращий ресторан?": "Aurelia",
        "Порадите хороший ресторан поблизу?": "Carbone",
        "Я хочу освідчитися дівчині цими вихідними. Ви можете допомогти?": "освідчення",
    }
    for question, expected in cases.items():
        faq, score = find_best_faq(session, question)
        assert faq is not None
        assert score >= 0.35
        assert expected.casefold() in f"{faq.question} {faq.answer}".casefold()


def test_unknown_pet_policy_does_not_match():
    session = populated_session()
    _, score = find_best_faq(session, "Чи можна приїхати в готель із собакою?")
    assert score < 0.35


def test_best_restaurant_does_not_return_dress_code_faq():
    session = populated_session()
    faq, score = find_best_faq(session, "Який ресторан найкращий у Meridian?")
    assert faq is not None
    assert score >= 0.35
    assert faq.question == "Розкажіть про ресторан Aurelia."


def test_english_poker_room_question_matches_ukrainian_faq():
    session = populated_session()
    faq, score = find_best_faq(session, "Is poker room open right now?")
    assert faq is not None
    assert score >= 0.35
    assert "Покерна кімната працює 24/7" in faq.answer
