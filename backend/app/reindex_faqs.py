"""Rebuild vectors from current FAQ content without running seed."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db import engine
from app.models import FAQ
from app.services.embeddings import embed_faq


def reindex_faqs() -> int:
    with Session(engine) as db, db.begin():
        faqs = list(db.scalars(select(FAQ).order_by(FAQ.id).with_for_update()))
        for faq in faqs:
            db.execute(
                update(FAQ).where(FAQ.id == faq.id).values(
                    embedding=embed_faq(faq),
                    # Index maintenance is not an administrator's content edit.
                    updated_at=FAQ.updated_at,
                ),
                execution_options={"synchronize_session": False},
            )
        return len(faqs)


if __name__ == "__main__":
    count = reindex_faqs()
    print(f"Reindexed {count} FAQs; content and timestamps preserved.")
