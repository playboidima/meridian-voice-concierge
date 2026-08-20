from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import engine
from app.models import FAQ
from app.seed_data import FAQS


def seed() -> None:
    with Session(engine) as db:
        statement = pg_insert(FAQ).values(FAQS)
        statement = statement.on_conflict_do_update(
            index_elements=[FAQ.question],
            set_={"answer": statement.excluded.answer, "category": statement.excluded.category},
        )
        db.execute(statement)
        db.commit()
    print(f"Seeded {len(FAQS)} Meridian FAQs.")


if __name__ == "__main__":
    seed()

