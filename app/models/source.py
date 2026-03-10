"""Source — URL sumber yang di-input owner untuk di-crawl."""

from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False, default="General")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    crawl_jobs = relationship("CrawlJob", back_populates="source", cascade="all, delete-orphan")
    candidates = relationship("CandidateDomain", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_sources_niche", "niche"),
        Index("idx_sources_active", "is_active"),
    )

    def __repr__(self):
        return f"<Source {self.id}: {self.url}>"
