from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.models import VoiceConfig
from app.voice_catalog import VOICE_CATALOG, VOICE_ORDER


class VoiceNotFoundError(Exception):
    pass


class InvalidVoiceStateError(Exception):
    pass


def reconcile_voice_catalog(db: Session) -> None:
    existing = {
        voice.name: voice for voice in db.scalars(select(VoiceConfig)).all()
    }
    for values in VOICE_CATALOG:
        voice = existing.get(values["name"])
        if voice is None:
            voice = VoiceConfig(**values, is_active=False)
            db.add(voice)
        else:
            voice.provider_voice_id = values["provider_voice_id"]
            voice.description = values["description"]
            voice.preview_path = values["preview_path"]

    db.flush()
    active_count = len(
        db.scalars(select(VoiceConfig).where(VoiceConfig.is_active.is_(True))).all()
    )
    if active_count == 0:
        james = db.scalar(select(VoiceConfig).where(VoiceConfig.name == "James"))
        if james is None:
            raise InvalidVoiceStateError
        james.is_active = True
    db.commit()


def list_voices(db: Session) -> list[VoiceConfig]:
    ordering = case(VOICE_ORDER, value=VoiceConfig.name, else_=len(VOICE_ORDER))
    return list(db.scalars(select(VoiceConfig).order_by(ordering)))


def activate_voice(db: Session, voice_id: int) -> VoiceConfig:
    voices = list(
        db.scalars(select(VoiceConfig).order_by(VoiceConfig.id).with_for_update())
    )
    selected = next((voice for voice in voices if voice.id == voice_id), None)
    if selected is None:
        db.rollback()
        raise VoiceNotFoundError

    db.execute(update(VoiceConfig).values(is_active=False))
    db.flush()
    selected.is_active = True
    db.commit()
    db.refresh(selected)
    return selected


def get_active_voice(db: Session) -> VoiceConfig:
    active = list(
        db.scalars(select(VoiceConfig).where(VoiceConfig.is_active.is_(True)))
    )
    if len(active) != 1:
        raise InvalidVoiceStateError
    return active[0]
