"""CrawlJob — log setiap kali crawl dijalankan."""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    total_links_found: Mapped[int] = mapped_column(Integer, default=0)
    total_candidates: Mapped[int] = mapped_column(Integer, default=0)
    total_dead_links: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    source = relationship("Source", back_populates="crawl_jobs")
    candidates = relationship("CandidateDomain", back_populates="crawl_job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_crawl_jobs_source", "source_id"),
        Index("idx_crawl_jobs_status", "status"),
    )

    def __repr__(self):
        return f"<CrawlJob {self.id}: source={self.source_id} status={self.status}>"
