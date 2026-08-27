from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import FAQ, SeedState
from app.seed_data import FAQS, LEGACY_TO_ENGLISH_QUESTIONS
from app.services.embeddings import embed_passage, faq_embedding_text
from app.services.voice_admin import reconcile_voice_catalog


def reconcile_legacy_seed_rows(db: Session, rows: list[dict]) -> None:
    """Legacy upgrade helper; deliberately not called during application startup."""
    rows_by_question = {row["question"]: row for row in rows}
    for legacy_question, english_question in LEGACY_TO_ENGLISH_QUESTIONS.items():
        new_values = rows_by_question.get(english_question)
        if new_values is None:
            continue

        legacy_row = db.scalar(select(FAQ).where(FAQ.question == legacy_question))
        if legacy_row is None:
            continue

        english_row = db.scalar(select(FAQ).where(FAQ.question == english_question))
        if english_row is not None:
            db.delete(legacy_row)
            continue

        legacy_row.question = new_values["question"]
        legacy_row.answer = new_values["answer"]
        legacy_row.category = new_values["category"]
        legacy_row.embedding = new_values["embedding"]

    db.flush()


def seed() -> None:
    with Session(engine) as db:
        with db.begin():
            state = db.scalar(
                select(SeedState)
                .where(SeedState.name == "meridian_faq_v1")
                .with_for_update()
            )
            if state is None:
                raise RuntimeError("Missing seed state; run alembic upgrade head first")
            if not state.applied:
                rows = [
                    {
                        **item,
                        "embedding": embed_passage(
                            faq_embedding_text(item["question"], item["answer"], item["category"])
                        ),
                    }
                    for item in FAQS
                ]
                db.execute(
                    pg_insert(FAQ).values(rows).on_conflict_do_nothing(
                        index_elements=[FAQ.question]
                    )
                )
                state.applied = True
        reconcile_voice_catalog(db)
    print("FAQ initialization complete; existing FAQ content preserved.")


if __name__ == "__main__":
    seed()
