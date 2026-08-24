from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import FAQ
from app.seed_data import FAQS
from app.services.faq_search import find_best_faq
from app.services.search_aliases import faq_search_aliases


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
        "Is the poker room open right now?": "poker room",
        "What is the best restaurant at The Meridian?": "Aurelia",
        "Can you recommend a good restaurant nearby?": "Carbone",
        "I want to propose to my girlfriend this weekend. Can you help?": "proposal",
    }
    for question, expected in cases.items():
        faq, score = find_best_faq(session, question)
        assert faq is not None
        assert score >= 0.35, question
        assert expected.casefold() in f"{faq.question} {faq.answer}".casefold()


def test_unknown_pet_policy_does_not_match():
    session = populated_session()
    _, score = find_best_faq(session, "Can I bring my dog to the hotel?")
    assert score < 0.35


def test_best_restaurant_does_not_return_dress_code_faq():
    session = populated_session()
    faq, score = find_best_faq(session, "What is the best restaurant at Meridian?")
    assert faq is not None
    assert score >= 0.35
    assert faq.question == "Tell me about Aurelia."


def test_english_poker_room_question_returns_english_answer():
    session = populated_session()
    faq, score = find_best_faq(session, "Is poker room open right now?")
    assert faq is not None
    assert score >= 0.35
    assert "The poker room is open 24/7" in faq.answer


def test_typical_paraphrases_route_to_expected_faqs():
    session = populated_session()
    cases = {
        "When are today's poker tournaments?": "poker room",
        "Where can I eat near the hotel?": "Carbone",
        "I want to propose to my girlfriend.": "birthday, anniversary, or proposal",
        "Can I check in early?": "check-in",
        "What time must I leave my room?": "check-out",
        "Can children enter the hotel?": "age restrictions",
        "How many pools do you have?": "pools",
        "When does the spa open?": "Meridian Spa",
        "Is the gym open at night?": "fitness center",
        "When is NOVA open?": "Nightclub NOVA",
        "What is in the penthouse?": "Penthouse Suite",
        "Where can I play blackjack?": "blackjack",
        "How does the loyalty program work?": "Meridian Rewards",
        "Where can I find whiskey and cigars?": "The Vault",
        "Can I host a wedding?": "wedding packages",
        "What is the helicopter tour discount?": "Vegas Nights Aviation",
    }
    for question, expected in cases.items():
        faq, score = find_best_faq(session, question)
        assert faq is not None
        assert score >= 0.35, question
        assert expected.casefold() in faq.question.casefold()


def test_typical_unknown_questions_stay_below_threshold():
    session = populated_session()
    questions = (
        "Can I rent a telescope?",
        "Do you provide airport transfers?",
        "Do you offer babysitting services?",
        "Can I bring my dog?",
    )
    for question in questions:
        _, score = find_best_faq(session, question)
        assert score < 0.35


def test_typical_english_questions_route_without_llm_translation():
    session = populated_session()
    cases = {
        "Can guests under twenty one enter the hotel?": "age restrictions",
        "How many pools do you have and when do they close?": "pools",
        "What time is check in and can I arrive early?": "check-in",
        "Can you recommend a good restaurant nearby?": "Carbone",
        "What is included in the Penthouse Suite?": "Penthouse Suite",
        "What discount do guests get on helicopter tours?": "Vegas Nights Aviation",
        "Do you have a special parking lot for electric cars?": "electric-vehicle charging",
    }
    for question, expected in cases.items():
        faq, score = find_best_faq(session, question)
        assert faq is not None
        assert score >= 0.35
        assert expected.casefold() in faq.question.casefold()


def test_every_seeded_faq_has_a_working_english_alias():
    session = populated_session()

    for item in FAQS:
        aliases = faq_search_aliases(item["question"])
        english_aliases = [
            alias for alias in aliases if any("a" <= char.casefold() <= "z" for char in alias)
        ]
        assert english_aliases, f'No English alias for: {item["question"]}'

        faq, score = find_best_faq(session, english_aliases[0])
        assert faq is not None
        assert score >= 0.35
        assert faq.question == item["question"]
