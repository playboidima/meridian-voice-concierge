import os
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from app.models import VoiceConfig


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_INTEGRATION") != "1",
    reason="Set RUN_POSTGRES_INTEGRATION=1 to test the running PostgreSQL stack.",
)

BACKEND_URL = os.getenv("INTEGRATION_BACKEND_URL", "http://backend:8000")
DATABASE_URL = os.getenv(
    "INTEGRATION_DATABASE_URL",
    "postgresql+psycopg://meridian:change-me@db:5432/meridian",
)


@pytest.mark.postgres_integration
def test_concurrent_activation_keeps_exactly_one_active_voice():
    engine = create_engine(DATABASE_URL)
    with Session(engine) as db:
        voice_ids = list(db.scalars(select(VoiceConfig.id).order_by(VoiceConfig.id)))
        james_id = db.scalar(select(VoiceConfig.id).where(VoiceConfig.name == "James"))
    assert len(voice_ids) == 4
    assert james_id is not None

    def activate(voice_id: int) -> int:
        response = httpx.post(
            f"{BACKEND_URL}/api/admin/voices/{voice_id}/activate", timeout=30
        )
        return response.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(activate, voice_ids[1:3]))
        assert statuses == [200, 200]

        with Session(engine) as db:
            assert db.scalar(
                select(func.count()).select_from(VoiceConfig).where(
                    VoiceConfig.is_active.is_(True)
                )
            ) == 1
    finally:
        with Session(engine) as db:
            db.execute(update(VoiceConfig).values(is_active=False))
            james = db.get(VoiceConfig, james_id)
            james.is_active = True
            db.commit()
        engine.dispose()
