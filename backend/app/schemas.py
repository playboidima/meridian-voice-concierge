from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class FAQSearchResponse(BaseModel):
    matched: bool
    score: float
    best_match: str | None = None
    answer: str | None = None
    category: str | None = None


class UnansweredResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_question: str
    normalized_question: str
    frequency: int
    first_seen_at: datetime
    last_seen_at: datetime
    status: str


class HealthResponse(BaseModel):
    status: str
    database: str

