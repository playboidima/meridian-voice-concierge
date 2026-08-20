from app.services.text import normalize_question


def test_normalize_question_handles_case_punctuation_and_synonyms():
    assert normalize_question("Чи ВІДКРИТА покерна кімната?") == "працює покер кімната"

