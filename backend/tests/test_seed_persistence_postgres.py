"""Opt-in seed/migration tests; only run against a disposable database."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import seed as seed_module
from app.models import FAQ


pytestmark = pytest.mark.skipif(
    not os.getenv("SEED_TEST_DATABASE_URL"),
    reason="Set SEED_TEST_DATABASE_URL to a disposable meridian_seed_test database.",
)


@pytest.fixture()
def seed_database(monkeypatch):
    url = make_url(os.environ["SEED_TEST_DATABASE_URL"])
    if url.database != "meridian_seed_test":
        pytest.fail("Seed tests require the dedicated meridian_seed_test database")
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    database = f"seed_test_{uuid4().hex}"
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    test_url = url.set(database=database)
    engine = create_engine(test_url)
    monkeypatch.setattr(seed_module, "engine", engine)
    # Embedding inference is unrelated to persistence and is tested elsewhere.
    monkeypatch.setattr(seed_module, "embed_passage", lambda _: [0.01] * 384)

    def migrate(revision="head"):
        environment = {
            **os.environ,
            "DATABASE_URL": test_url.render_as_string(hide_password=False),
        }
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            env=environment, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

    try:
        yield engine, migrate
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database}"'))
        admin.dispose()


def test_restart_preserves_edits_deletions_and_renames(seed_database):
    engine, migrate = seed_database
    migrate()
    seed_module.seed()
    with Session(engine) as db:
        rows = list(db.scalars(select(FAQ).order_by(FAQ.id)))
        assert len(rows) == 48
        edited_id, renamed_id = rows[0].id, rows[2].id
        deleted_question, previous_name = rows[1].question, rows[2].question
        rows[0].answer = "Administrator's updated answer"
        rows[0].category = "custom"
        rows[2].question = "Administrator's renamed question?"
        db.delete(rows[1])
        db.commit()
    seed_module.seed()
    with Session(engine) as db:
        assert db.get(FAQ, edited_id).answer == "Administrator's updated answer"
        assert db.get(FAQ, edited_id).category == "custom"
        assert db.get(FAQ, renamed_id).question == "Administrator's renamed question?"
        assert db.scalar(select(FAQ).where(FAQ.question == deleted_question)) is None
        assert db.scalar(select(FAQ).where(FAQ.question == previous_name)) is None
        assert db.scalar(select(func.count()).select_from(FAQ)) == 47


@pytest.mark.parametrize("empty", [False, True])
def test_existing_installation_is_not_reseeded_during_upgrade(seed_database, empty):
    engine, migrate = seed_database
    migrate("20260824_04")
    with Session(engine) as db:
        db.add(FAQ(question="Where is The Meridian located?", answer="Custom location", category="custom"))
        db.commit()
        if empty:
            db.execute(delete(FAQ))
            db.commit()
    migrate()
    seed_module.seed()
    with Session(engine) as db:
        rows = list(db.scalars(select(FAQ)))
        assert len(rows) == (0 if empty else 1)
        if not empty:
            assert rows[0].answer == "Custom location"


def test_repeat_seed_does_not_require_embedding_inference(seed_database, monkeypatch):
    _, migrate = seed_database
    migrate()
    seed_module.seed()

    def unavailable(_):
        raise RuntimeError("Embedding model unavailable")

    monkeypatch.setattr(seed_module, "embed_passage", unavailable)
    seed_module.seed()


def test_failed_seed_can_be_retried(seed_database, monkeypatch):
    engine, migrate = seed_database
    migrate()

    def unavailable(_):
        raise RuntimeError("Embedding model unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(seed_module, "embed_passage", unavailable)
        with pytest.raises(RuntimeError, match="Embedding model unavailable"):
            seed_module.seed()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(FAQ)) == 0
    seed_module.seed()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(FAQ)) == 48


def test_concurrent_first_seed_is_safe(seed_database):
    engine, migrate = seed_database
    migrate()
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: seed_module.seed(), range(2)))
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(FAQ)) == 48
        db.execute(delete(FAQ))
        db.commit()
    seed_module.seed()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(FAQ)) == 0
