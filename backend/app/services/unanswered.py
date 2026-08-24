from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import UnansweredQuestion


def record_unanswered_question(
    db: Session,
    *,
    original_question: str,
    normalized_question: str,
) -> UnansweredQuestion:
    now = datetime.now(timezone.utc)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = (
            postgresql_insert(UnansweredQuestion)
            .values(
                original_question=original_question,
                normalized_question=normalized_question,
                frequency=1,
                first_seen_at=now,
                last_seen_at=now,
                status="open",
            )
            .on_conflict_do_update(
                index_elements=[UnansweredQuestion.normalized_question],
                set_={
                    "frequency": UnansweredQuestion.frequency + 1,
                    "last_seen_at": now,
                },
            )
            .returning(UnansweredQuestion)
        )
        item = db.scalar(statement)
        db.commit()
        return item

    return _record_with_orm_fallback(
        db,
        original_question=original_question,
        normalized_question=normalized_question,
        now=now,
    )


def _record_with_orm_fallback(
    db: Session,
    *,
    original_question: str,
    normalized_question: str,
    now: datetime,
) -> UnansweredQuestion:
    existing = db.scalar(
        select(UnansweredQuestion).where(
            UnansweredQuestion.normalized_question == normalized_question
        )
    )
    if existing:
        existing.frequency += 1
        existing.last_seen_at = now
        db.commit()
        db.refresh(existing)
        return existing

    item = UnansweredQuestion(
        original_question=original_question,
        normalized_question=normalized_question,
        first_seen_at=now,
        last_seen_at=now,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(UnansweredQuestion).where(
                UnansweredQuestion.normalized_question == normalized_question
            )
        )
        if existing is None:
            raise
        existing.frequency += 1
        existing.last_seen_at = now
        db.commit()
        db.refresh(existing)
        return existing
    db.refresh(item)
    return item
