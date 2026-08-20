from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FAQ
from app.services.text import normalize_question


def _score(query: str, candidate: str) -> float:
    query_tokens = set(query.split())
    candidate_tokens = set(candidate.split())
    union = query_tokens | candidate_tokens
    token_score = len(query_tokens & candidate_tokens) / len(union) if union else 0.0
    phrase_score = SequenceMatcher(None, query, candidate).ratio()
    containment = len(query_tokens & candidate_tokens) / len(query_tokens) if query_tokens else 0.0
    return round(0.45 * containment + 0.35 * token_score + 0.20 * phrase_score, 4)


def find_best_faq(db: Session, question: str) -> tuple[FAQ | None, float]:
    normalized_query = normalize_question(question)
    best_faq = None
    best_score = 0.0
    for faq in db.scalars(select(FAQ)):
        normalized_question = normalize_question(faq.question)
        searchable = normalize_question(f"{faq.question} {faq.answer} {faq.category}")
        score = _score(normalized_query, searchable)
        for marker in {"aurelia", "carbone", "освідчення"}:
            if marker in normalized_query.split() and marker in normalized_question.split():
                score = min(1.0, score + 0.4)
        if score > best_score:
            best_faq, best_score = faq, score
    return best_faq, best_score
