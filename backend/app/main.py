from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import FAQ, UnansweredQuestion
from app.schemas import (
    FAQAdminResponse,
    FAQAdminWrite,
    FAQSearchResponse,
    HealthResponse,
    QuestionRequest,
    UnansweredResponse,
)
from app.services.faq_search import find_best_faq
from app.services.faq_admin import (
    FAQConflictError,
    FAQNotFoundError,
    create_faq,
    delete_faq,
    update_faq,
)
from app.services.text import normalize_question
from app.services.unanswered import record_unanswered_question

app = FastAPI(title="Meridian Voice Concierge API", version="0.1.0")


def faq_admin_http_error(error: FAQConflictError | FAQNotFoundError) -> HTTPException:
    if isinstance(error, FAQNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="FAQ question already exists",
    )


@app.get("/api/admin/faqs", response_model=list[FAQAdminResponse])
def list_admin_faqs(db: Session = Depends(get_db)) -> list[FAQ]:
    return list(db.scalars(select(FAQ).order_by(FAQ.id)))


@app.post(
    "/api/admin/faqs",
    response_model=FAQAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_faq(payload: FAQAdminWrite, db: Session = Depends(get_db)) -> FAQ:
    try:
        return create_faq(db, payload)
    except FAQConflictError as error:
        raise faq_admin_http_error(error) from error


@app.put("/api/admin/faqs/{faq_id}", response_model=FAQAdminResponse)
def update_admin_faq(
    faq_id: int, payload: FAQAdminWrite, db: Session = Depends(get_db)
) -> FAQ:
    try:
        return update_faq(db, faq_id, payload)
    except (FAQConflictError, FAQNotFoundError) as error:
        raise faq_admin_http_error(error) from error


@app.delete("/api/admin/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_faq(faq_id: int, db: Session = Depends(get_db)) -> None:
    try:
        delete_faq(db, faq_id)
    except FAQNotFoundError as error:
        raise faq_admin_http_error(error) from error


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
