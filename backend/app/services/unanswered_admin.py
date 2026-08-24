from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import FAQ, UnansweredQuestion
from app.schemas import UnansweredConvertWrite
from app.services import embeddings
from app.services.faq_admin import FAQConflictError


class UnansweredNotFoundError(Exception):
    pass


def get_open_unanswered(db: Session, unanswered_id: int) -> UnansweredQuestion:
    item = db.get(UnansweredQuestion, unanswered_id)
    if item is None or item.status != "open":
        raise UnansweredNotFoundError
    return item


def dismiss_unanswered(db: Session, unanswered_id: int) -> UnansweredQuestion:
    item = get_open_unanswered(db, unanswered_id)
    item.status = "dismissed"
    db.commit()
    db.refresh(item)
    return item


def convert_unanswered_to_faq(
    db: Session,
    unanswered_id: int,
    payload: UnansweredConvertWrite,
) -> FAQ:
    item = get_open_unanswered(db, unanswered_id)
    question = item.original_question.strip()
    faq = FAQ(
        question=question,
        answer=payload.answer,
        category=payload.category,
        embedding=embeddings.embed_passage(
            embeddings.faq_embedding_text(question, payload.answer, payload.category)
        ),
    )
    db.add(faq)
    item.status = "converted"
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise FAQConflictError from error
    db.refresh(faq)
    return faq
