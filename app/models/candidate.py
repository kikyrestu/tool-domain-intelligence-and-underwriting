"""CandidateDomain — domain kandidat hasil extract + filter dari crawl."""

from datetime import datetime, date
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, Date,
    DateTime, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CandidateDomain(Base):
    __tablename__ = "candidate_domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    crawl_job_id: Mapped[int] = mapped_column(ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False)
    source_url_found: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    original_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)

    # Domain Status (root domain check)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dns_resolves: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_domain_alive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_parked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Availability (Week 2)
    availability_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    whois_registrar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whois_created_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    whois_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    whois_days_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dns_has_records: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    whois_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # History (Week 3)
    wayback_total_snapshots: Mapped[int] = mapped_column(Integer, default=0)
    wayback_first_seen: Mapped[date | None] = mapped_column(Date, nullable=True)
    wayback_last_seen: Mapped[date | None] = mapped_column(Date, nullable=True)
    wayback_years_active: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dominant_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    content_drift_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    wayback_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Scoring (Week 3)
    score_availability: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_continuity: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_cleanliness: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    label_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Owner
    owner_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Meta
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source = relationship("Source", back_populates="candidates")
    crawl_job = relationship("CrawlJob", back_populates="candidates")

    __table_args__ = (
        UniqueConstraint("domain", "source_id", name="uq_candidates_domain_source"),
        Index("idx_candidates_domain", "domain"),
        Index("idx_candidates_source", "source_id"),
        Index("idx_candidates_label", "label"),
        Index("idx_candidates_score", "score_total"),
        Index("idx_candidates_availability", "availability_status"),
        Index("idx_candidates_niche", "niche"),
    )

    def __repr__(self):
        return f"<CandidateDomain {self.id}: {self.domain}>"
