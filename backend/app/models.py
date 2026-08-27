from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import VECTOR

from app.db import Base


class SeedState(Base):
    __tablename__ = "seed_state"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False)


class FAQ(Base):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(String(1000), unique=True)
    answer: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), index=True)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_question: Mapped[str] = mapped_column(String(1000))
    normalized_question: Mapped[str] = mapped_column(String(1000), unique=True)
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)


class VoiceConfig(Base):
    __tablename__ = "voice_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    provider_voice_id: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)
    preview_path: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def preview_url(self) -> str:
        return f"/api/admin/voices/{self.id}/preview"
