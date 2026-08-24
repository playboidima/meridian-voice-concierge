from difflib import SequenceMatcher

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import FAQ
from app.services.embeddings import embed_faq, embed_query
from app.services.search_aliases import faq_search_aliases
from app.services.text import normalize_question


STRONG_LEXICAL_THRESHOLD = 0.45
SEMANTIC_MIN_MARGIN = 0.01


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
    faqs = list(db.scalars(select(FAQ)))
    lexical_faq = None
    lexical_score = 0.0
    for faq in faqs:
        normalized_question = normalize_question(faq.question)
        aliases = " ".join(faq_search_aliases(faq.question))
        searchable = normalize_question(
            f"{faq.question} {aliases} {faq.answer} {faq.category}"
        )
        score = _score(normalized_query, searchable)
        for marker in {"aurelia", "carbone", "proposal", "освідчення"}:
            if marker in normalized_query.split() and marker in normalized_question.split():
                score = min(1.0, score + 0.4)
        if score > lexical_score:
            lexical_faq, lexical_score = faq, score

    semantic_faq = None
    semantic_score = 0.0
    semantic_runner_up_score = 0.0
    is_english_query = not any("\u0400" <= character <= "\u04ff" for character in question)
    if not is_english_query:
        return lexical_faq, lexical_score

    query_embedding = embed_query(question)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        distance = FAQ.embedding.cosine_distance(query_embedding)
        rows = db.execute(
            select(FAQ, (1 - distance).label("similarity"))
            .where(FAQ.embedding.is_not(None))
            .order_by(distance)
            .limit(2)
        ).all()
        if rows:
            semantic_faq = rows[0][0]
            semantic_score = round(float(rows[0][1]), 4)
            if len(rows) > 1:
                semantic_runner_up_score = round(float(rows[1][1]), 4)
    else:
        semantic_matches = []
        for faq in faqs:
            score = float(np.dot(query_embedding, embed_faq(faq)))
            semantic_matches.append((score, faq))
        semantic_matches.sort(key=lambda match: match[0], reverse=True)
        if semantic_matches:
            semantic_score, semantic_faq = semantic_matches[0]
            semantic_score = round(semantic_score, 4)
            if len(semantic_matches) > 1:
                semantic_runner_up_score = round(semantic_matches[1][0], 4)

    if lexical_faq is not None and lexical_score >= STRONG_LEXICAL_THRESHOLD:
        return lexical_faq, lexical_score
    semantic_margin = semantic_score - semantic_runner_up_score
    if (
        semantic_faq is not None
        and semantic_score >= settings.semantic_match_threshold
        and semantic_margin >= SEMANTIC_MIN_MARGIN
    ):
        return semantic_faq, semantic_score
    return lexical_faq, lexical_score
