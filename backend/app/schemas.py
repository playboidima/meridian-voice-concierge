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

    question: str = Field(min_length=2, max_length=1000)
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


class UnansweredConvertWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    answer: str = Field(min_length=2)
    category: str = Field(min_length=2, max_length=100)


class HealthResponse(BaseModel):
    status: str
    database: str


class VoiceAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    is_active: bool
    preview_url: str
    updated_at: datetime


class ActiveVoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    provider_voice_id: str
    updated_at: datetime


class LiveKitTokenRequest(BaseModel):
    room_name: str | None = None
    participant_identity: str | None = None
    participant_name: str | None = None
    participant_metadata: str | None = None
    participant_attributes: dict[str, str] | None = None
    room_config: dict | None = None


class LiveKitTokenResponse(BaseModel):
    server_url: str
    participant_token: str
