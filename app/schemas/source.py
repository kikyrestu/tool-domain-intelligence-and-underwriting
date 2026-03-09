"""Pydantic schemas for Source."""

from pydantic import BaseModel, HttpUrl
from datetime import datetime


class SourceCreate(BaseModel):
    url: str
    niche: str
    notes: str | None = None


class SourceResponse(BaseModel):
    id: int
    url: str
    niche: str
    notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
