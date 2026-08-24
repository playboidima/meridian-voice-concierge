from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import FAQ
from app.seed_data import FAQS, LEGACY_TO_ENGLISH_QUESTIONS
from app.services.embeddings import embed_passage, faq_embedding_text


def reconcile_legacy_seed_rows(db: Session, rows: list[dict]) -> None:
    """Upgrade only exact built-in FAQ rows from the previous seed catalog."""
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
        rows = [
            {
                **item,
                "embedding": embed_passage(
                    faq_embedding_text(item["question"], item["answer"], item["category"])
                ),
            }
            for item in FAQS
        ]
        reconcile_legacy_seed_rows(db, rows)
        statement = pg_insert(FAQ).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[FAQ.question],
            set_={
                "answer": statement.excluded.answer,
                "category": statement.excluded.category,
                "embedding": statement.excluded.embedding,
            },
        )
        db.execute(statement)
        db.commit()
    print(f"Seeded {len(FAQS)} Meridian FAQs.")


if __name__ == "__main__":
    seed()
