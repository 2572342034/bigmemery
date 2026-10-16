from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    source: str = Field(default="manual", max_length=160)


class KnowledgeItem(BaseModel):
    id: str
    title: str
    source: str
    file_name: str | None = None
    file_path: str | None = None
    mime_type: str | None = None
    storage_provider: str = "local"
    file_size: int = 0
    chunk_count: int = 0
    content_length: int = 0
    index_status: str = "ready"
    content_preview: str = ""
    content: str | None = None
    created_at: datetime | None = None
