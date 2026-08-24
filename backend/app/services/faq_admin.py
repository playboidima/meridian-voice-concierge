from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import FAQ
from app.schemas import FAQAdminWrite
from app.services import embeddings


class FAQConflictError(Exception):
    pass


class FAQNotFoundError(Exception):
    pass


def create_faq(db: Session, payload: FAQAdminWrite) -> FAQ:
    faq = FAQ(
        question=payload.question,
        answer=payload.answer,
        category=payload.category,
        embedding=embeddings.embed_passage(
            embeddings.faq_embedding_text(
                payload.question,
                payload.answer,
                payload.category,
            )
        ),
    )
    db.add(faq)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise FAQConflictError from error
    db.refresh(faq)
    return faq


def update_faq(db: Session, faq_id: int, payload: FAQAdminWrite) -> FAQ:
    faq = db.get(FAQ, faq_id)
    if faq is None:
        raise FAQNotFoundError

    faq.question = payload.question
    faq.answer = payload.answer
    faq.category = payload.category
    faq.embedding = embeddings.embed_passage(
        embeddings.faq_embedding_text(
            payload.question,
            payload.answer,
            payload.category,
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise FAQConflictError from error
    db.refresh(faq)
    return faq


def delete_faq(db: Session, faq_id: int) -> None:
    faq = db.get(FAQ, faq_id)
    if faq is None:
        raise FAQNotFoundError

    db.delete(faq)
    db.commit()
