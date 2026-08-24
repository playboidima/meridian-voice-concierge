import re

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import FAQ
from app.seed import reconcile_legacy_seed_rows
from app.seed_data import FAQS
from app.seed_data import LEGACY_SEED_QUESTIONS


CYRILLIC = re.compile(r"[\u0400-\u04ff]")


def test_seed_catalog_contains_48_unique_english_faqs() -> None:
    assert len(FAQS) == 48
    assert len({item["question"] for item in FAQS}) == 48

    for item in FAQS:
        assert not CYRILLIC.search(item["question"]), item["question"]
        assert not CYRILLIC.search(item["answer"]), item["answer"]


def test_seed_catalog_includes_ev_parking_information() -> None:
    faq = next(
        item for item in FAQS
        if item["question"] == "Is parking with electric-vehicle charging available?"
    )

    assert faq["category"] == "general"
    assert "self-parking garage" in faq["answer"]
    assert "subject to availability" in faq["answer"]


def test_reconcile_updates_only_exact_legacy_seed_rows_and_preserves_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        legacy = FAQ(
            question=LEGACY_SEED_QUESTIONS[0],
            answer="Old built-in answer",
            category="general",
        )
        custom = FAQ(
            question="Моє власне питання",
            answer="Моя власна відповідь",
            category="custom",
        )
        db.add_all([legacy, custom])
        db.commit()
        legacy_id = legacy.id

        reconcile_legacy_seed_rows(db, [{**FAQS[0], "embedding": None}])
        db.commit()

        rows = list(db.scalars(select(FAQ).order_by(FAQ.id)))
        assert rows[0].id == legacy_id
        assert rows[0].question == "Where is The Meridian located?"
        assert rows[0].answer == FAQS[0]["answer"]
        assert rows[1].question == "Моє власне питання"
        assert rows[1].answer == "Моя власна відповідь"
