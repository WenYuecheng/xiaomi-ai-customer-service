from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import DocumentStatus, JobStatus


class UploadResponse(BaseModel):
    document_id: str
    job_id: str
    status: JobStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    original_filename: str
    stored_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    error_message: str | None
    chunk_size: int
    chunk_overlap: int
    source_url: str | None
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ordinal: int
    text: str
    location: str
    product_models: list[str]


class ChunkList(BaseModel):
    items: list[ChunkResponse]
    total: int


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    operation: str
    status: JobStatus
    stage: str
    error_message: str | None
    attempts: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
