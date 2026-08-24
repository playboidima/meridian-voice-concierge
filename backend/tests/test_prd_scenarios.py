from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import FAQ
from app.seed_data import FAQS
from app.services.faq_search import find_best_faq
from app.services.search_aliases import FAQ_SEARCH_ALIASES


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


def test_typical_paraphrases_route_to_expected_faqs():
    session = populated_session()
    cases = {
        "Коли сьогодні покерні турніри?": "Коли працює покерна кімната",
        "Де поїсти недалеко від готелю?": "Яка партнерська знижка в Carbone",
        "Хочу зробити пропозицію дівчині": "Які пакети є для дня народження",
        "Коли можна заселитися раніше?": "О котрій заселення",
        "О котрій треба виїхати з номера?": "О котрій виселення",
        "Чи можна дітям заходити в готель?": "Які вікові обмеження",
        "Скільки у вас басейнів?": "Які басейни",
        "Коли відкривається спа?": "Коли працює Meridian Spa",
        "Ваш спортзал працює вночі?": "Коли працює фітнес-центр",
        "Коли працює нічний клуб NOVA?": "Коли працює Nightclub NOVA",
        "Що є в пентхаусі?": "Що входить у Penthouse Suite",
        "Де можна пограти в блекджек?": "Які столи для блекджеку",
        "Як працює програма лояльності?": "Як працює Meridian Rewards",
        "Де є віскі та сигари?": "Розкажіть про The Vault",
        "Чи можна провести весілля?": "Які весільні пакети",
        "Яка знижка на гелікоптерний тур?": "Vegas Nights Aviation",
    }
    for question, expected in cases.items():
        faq, score = find_best_faq(session, question)
        assert faq is not None
        assert score >= 0.35
        assert expected.casefold() in faq.question.casefold()


def test_typical_unknown_questions_stay_below_threshold():
    session = populated_session()
    questions = (
        "Чи є зарядка для електромобіля?",
        "Чи надаєте трансфер з аеропорту?",
        "Чи є послуги няні?",
        "Чи можна приїхати із собакою?",
    )
    for question in questions:
        _, score = find_best_faq(session, question)
        assert score < 0.35


def test_typical_english_questions_route_without_llm_translation():
    session = populated_session()
    cases = {
        "Can guests under twenty one enter the hotel?": "Які вікові обмеження",
        "How many pools do you have and when do they close?": "Які басейни",
        "What time is check in and can I arrive early?": "О котрій заселення",
        "Can you recommend a good restaurant nearby?": "Carbone",
        "What is included in the Penthouse Suite?": "Penthouse Suite",
        "What discount do guests get on helicopter tours?": "Vegas Nights Aviation",
    }
    for question, expected in cases.items():
        faq, score = find_best_faq(session, question)
        assert faq is not None
        assert score >= 0.35
        assert expected.casefold() in faq.question.casefold()


def test_every_seeded_faq_has_a_working_english_alias():
    session = populated_session()

    for item in FAQS:
        aliases = FAQ_SEARCH_ALIASES.get(item["question"], ())
        english_aliases = [
            alias for alias in aliases if any("a" <= char.casefold() <= "z" for char in alias)
        ]
        assert english_aliases, f'No English alias for: {item["question"]}'

        faq, score = find_best_faq(session, english_aliases[0])
        assert faq is not None
        assert score >= 0.35
        assert faq.question == item["question"]
