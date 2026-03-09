"""Pydantic schemas for CandidateDomain."""

from pydantic import BaseModel
from datetime import datetime


class CandidateResponse(BaseModel):
    id: int
    domain: str
    niche: str
    source_url_found: str | None
    http_status: int | None
    is_dead_link: bool
    availability_status: str | None
    score_total: float | None
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
