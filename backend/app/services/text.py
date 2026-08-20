import re
import unicodedata


STOP_WORDS = {
    "а", "але", "в", "ви", "до", "з", "за", "і", "із", "й", "на", "про",
    "та", "у", "це", "ці", "цими", "чи", "що", "як", "я", "вас", "ваш", "ваша", "ваші",
    "зараз", "хочу", "можете", "допомогти", "дівчині", "вихідними", "порадите", "хороший",
    "a", "an", "and", "are", "can", "could", "do", "does", "for", "i", "in", "is", "me",
    "my", "of", "on", "please", "right", "the", "there", "to", "we", "what", "when", "where",
    "which", "with", "you", "your",
}

SYNONYMS = {
    "відкрита": "працює", "відкритий": "працює", "відкрито": "працює",
    "години": "працює", "графік": "працює", "коштує": "ціна", "вартість": "ціна",
    "авто": "паркування", "машина": "паркування", "пес": "собака",
    "покеру": "покер", "покерна": "покер", "ресторани": "ресторан",
    "номери": "номер", "басейни": "басейн", "знижки": "знижка",
    "open": "працює", "opened": "працює", "hours": "працює",
    "poker": "покер", "room": "кімната", "casino": "казино",
}


def normalize_question(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("’", "'")
    intent_tokens = []
    if "найкращ" in value and "ресторан" in value:
        intent_tokens.append("aurelia")
    if "поблизу" in value and "ресторан" in value:
        intent_tokens.append("carbone")
    if "освідч" in value:
        intent_tokens.append("освідчення")
    words = re.findall(r"[\w'-]+", value, flags=re.UNICODE)
    normalized = [SYNONYMS.get(word, word) for word in words if word not in STOP_WORDS]
    return " ".join(normalized + intent_tokens)
