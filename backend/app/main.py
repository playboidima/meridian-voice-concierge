from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import UnansweredQuestion
from app.schemas import FAQSearchResponse, HealthResponse, QuestionRequest, UnansweredResponse
from app.services.faq_search import find_best_faq
from app.services.text import normalize_question
from app.services.unanswered import record_unanswered_question

app = FastAPI(title="Meridian Voice Concierge API", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ok")


@app.post("/api/faq/search", response_model=FAQSearchResponse)
def search_faq(payload: QuestionRequest, db: Session = Depends(get_db)) -> FAQSearchResponse:
    faq, score = find_best_faq(db, payload.question)
    if faq is None or score < settings.faq_match_threshold:
        return FAQSearchResponse(matched=False, score=score)
    return FAQSearchResponse(
        matched=True,
        score=score,
        best_match=faq.question,
        answer=faq.answer,
        category=faq.category,
    )


@app.post("/api/unanswered", response_model=UnansweredResponse)
def record_unanswered(payload: QuestionRequest, db: Session = Depends(get_db)) -> UnansweredQuestion:
    normalized = normalize_question(payload.question)
    return record_unanswered_question(
        db,
        original_question=payload.question.strip(),
        normalized_question=normalized,
    )
