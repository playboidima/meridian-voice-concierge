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


class FAQAdminWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=2)
    category: str = Field(min_length=2, max_length=100)


class FAQAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    category: str
    created_at: datetime
    updated_at: datetime


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
