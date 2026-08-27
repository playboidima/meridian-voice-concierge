from difflib import SequenceMatcher

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import FAQ
from app.seed_data import LEGACY_TO_ENGLISH_QUESTIONS
from app.services.embeddings import embed_faq, embed_query
from app.services.search_aliases import faq_search_aliases
from app.services.search_terms import lexical_text, topic_terms
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
    is_english_query = not any("\u0400" <= character <= "\u04ff" for character in question)
    normalize = lexical_text if is_english_query else normalize_question
    normalized_query = normalize(question)
    faqs = list(db.scalars(select(FAQ)))
    if is_english_query:
        required = topic_terms(question)
        if not required:
            return None, 0.0
        # Aliases rank candidates but cannot supply facts absent from the current FAQ.
        faqs = [faq for faq in faqs if required <= topic_terms(
            f"{LEGACY_TO_ENGLISH_QUESTIONS.get(faq.question, faq.question)} {faq.answer}"
        )]
    if not faqs:
        return None, 0.0
    lexical_faq = None
    lexical_score = 0.0
    for faq in faqs:
        score = max(
            _score(normalized_query, normalize(candidate))
            for candidate in (faq.question, faq.answer, *faq_search_aliases(faq.question))
        )
        if score > lexical_score:
            lexical_faq, lexical_score = faq, score

    semantic_faq = None
    semantic_score = 0.0
    semantic_runner_up_score = 0.0
    if not is_english_query:
        return lexical_faq, lexical_score

    query_embedding = embed_query(question)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        distance = FAQ.embedding.cosine_distance(query_embedding)
        rows = db.execute(
            select(FAQ, (1 - distance).label("similarity"))
            .where(FAQ.embedding.is_not(None))
            .where(FAQ.id.in_([faq.id for faq in faqs]))
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
