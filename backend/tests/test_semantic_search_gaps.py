import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import FAQ
from app.seed_data import FAQS
from app.services.faq_search import find_best_faq


MATCH_THRESHOLD = 0.35


@pytest.fixture()
def populated_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all(FAQ(**item) for item in FAQS)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("question", "expected_question"),
    [
        (
            "What time can I get my room?",
            "О котрій заселення та чи можливе раннє заселення?",
        ),
        (
            "Where can I work out after midnight?",
            "Коли працює фітнес-центр?",
        ),
        (
            "Where can I eat sushi?",
            "Розкажіть про ресторан Silk Road.",
        ),
        (
            "Could I get a room with a terrace?",
            "Що входить у Penthouse Suite?",
        ),
        (
            "Can my 19-year-old enter a family restaurant?",
            "Які вікові обмеження діють у комплексі?",
        ),
    ],
)
def test_unseen_english_paraphrase_matches_by_meaning(
    populated_session: Session,
    question: str,
    expected_question: str,
) -> None:
    faq, score = find_best_faq(populated_session, question)

    assert faq is not None
    assert score >= MATCH_THRESHOLD
    assert faq.question == expected_question


def test_all_five_prd_conversation_scenarios_in_english(
    populated_session: Session,
) -> None:
    known_cases = {
        "Is the poker room open right now?": "Коли працює покерна кімната",
        "What is the best restaurant at the Meridian?": "Aurelia",
        "Can you recommend a good restaurant nearby?": "Carbone",
        "I want to propose to my girlfriend this weekend. Can you help?": "освідчення",
    }

    for question, expected in known_cases.items():
        faq, score = find_best_faq(populated_session, question)
        assert faq is not None
        assert score >= MATCH_THRESHOLD
        assert expected.casefold() in f"{faq.question} {faq.answer}".casefold()

    _, unknown_score = find_best_faq(
        populated_session,
        "Can I bring my dog to the hotel?",
    )
    assert unknown_score < MATCH_THRESHOLD
