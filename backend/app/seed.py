from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import engine
from app.models import FAQ
from app.seed_data import FAQS
from app.services.embeddings import embed_passage, faq_embedding_text


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
