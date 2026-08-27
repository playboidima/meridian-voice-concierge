"""Conservative topic coverage for English retrieval, not fact generation.

These synonyms describe topics, never which services a venue actually offers.
Question aggregation deliberately keeps using the separate text normalizer.
"""

import re
import unicodedata

from app.services.text import STOP_WORDS, normalize_question


REQUEST_WORDS = STOP_WORDS | {
    "about", "at", "be", "by", "from", "has", "have", "how", "it", "its",
    "tell", "get", "try", "need", "want", "would", "should", "must", "may",
    "any", "some", "there", "this", "that", "available", "availability",
    "offer", "provide", "include", "allow", "allowed", "bring", "enter",
    "guest", "good", "best", "recommend", "help", "now", "today", "today's",
    "weekend", "girlfriend", "time", "or", "a", "an", "after", "property",
    "find", "play", "host", "many", "they", "arrive", "special", "all",
}
SYNONYMS = {
    "eat": "restaurant", "dine": "restaurant", "dining": "restaurant",
    "cuisine": "restaurant", "fine-dining": "restaurant",
    "near": "nearby", "away": "nearby",
    "hotel": "property", "resort": "property", "meridian": "property",
    "puppy": "dog",
    "cancellation": "cancel", "cancelling": "cancel", "canceling": "cancel",
    "transportation": "transfer", "shuttle": "transfer",
    "exercise": "gym", "workout": "gym", "fitness": "gym",
    "midnight": "night", "tonight": "night",
    "opening": "open", "hour": "open", "opened": "open",
    "close": "open", "closing": "open",
    "leave": "checkout", "departure": "checkout",
    "propose": "proposal", "engagement": "proposal",
    "complimentary": "free", "cost": "price", "rate": "price",
    "kid": "child", "children": "child", "aged": "age",
    "twenty-one": "age", "internet": "wifi", "wi-fi": "wifi",
    "suite": "room", "steakhouse": "steakhouse restaurant",
    "reservation": "book", "booking": "book", "booked": "book",
    "appointment": "book", "event": "performance", "residency": "performance",
    "residencie": "performance", "show": "performance",
}


def _words(value: str) -> list[str]:
    value = unicodedata.normalize("NFKC", value).casefold().replace("’", "'")
    value = re.sub(r"\bhow much\b", "price", value)
    if re.search(r"[$€£]\s*\d|\b\d[\d,.]*\s*(?:dollars?|euros?|pounds?|usd)\b", value):
        value += " price"
    value = re.sub(r"\b(?:\d+|nineteen|twenty)[ -]year[ -]old\b", "age", value)
    value = re.sub(r"\bunder\s+(?:twenty[ -]one|21)\b", "age", value)
    value = re.sub(r"\b24\s*/\s*7\b", "open day night", value)
    value = re.sub(r"\bwork out\b|\bfitness cent(?:er|re)\b", "gym", value)
    value = re.sub(r"\bcheck[ -]?in\b", "checkin", value)
    value = re.sub(r"\bcheck[ -]?out\b", "checkout", value)
    value = re.sub(r"\ball ages\b", "age child adult", value)
    value = re.sub(r"\bloyalty program\b", "rewards", value)
    value = re.sub(r"\belectric[ -](?:vehicles?|cars?)\b|\bev\b", "ev", value)
    value = re.sub(r"\bself[ -]parking\b", "selfparking", value)
    value = re.sub(r"\bparking lot\b", "parking", value)
    value = re.sub(r"\boutdoor terrace\b", "terrace", value)
    words = re.findall(r"[\w'-]+", value)
    result = []
    for word in words:
        if (word not in REQUEST_WORDS and word.endswith("s") and len(word) > 3
                and not word.endswith(("ss", "us"))):
            word = word[:-1]
        result.extend(SYNONYMS.get(word, word).split())
    return result


def topic_terms(value: str) -> set[str]:
    return set(_words(value)) - REQUEST_WORDS


def lexical_text(value: str) -> str:
    return normalize_question(" ".join(_words(value)))
