from datetime import datetime

from pydantic import BaseModel, Field


class ConversationSource(BaseModel):
    citation: str
    title: str
    source: str
    score: float


class ConversationMessage(BaseModel):
    id: int | str
    role: str
    content: str
    model: str | None = None
    created_at: datetime | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    preview: str = ""
    model: str
    use_rag: bool = True
    latest_grounded: bool = False
    latest_sources: list[ConversationSource] = Field(default_factory=list)
    updated_at: datetime | None = None
    created_at: datetime | None = None
    message_count: int = 0


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage] = Field(default_factory=list)


class CreateConversationRequest(BaseModel):
    model: str | None = None
    use_rag: bool = True
