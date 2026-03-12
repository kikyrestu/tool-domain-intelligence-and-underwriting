"""SuggestedCandidate — root domain yang ditemukan sistem (Wayback, crawl outbound),
menunggu owner untuk di-evaluate (RDAP + Wayback) sebagai candidate beli.

Berbeda dari SuggestedSource:
- SuggestedSource = halaman/URL yang bisa dijadikan INPUT crawl (punya konten + outbound links)
- SuggestedCandidate = root domain yang ingin dievaluasi apakah layak DIBELI
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SuggestedCandidate(Base):
    __tablename__ = "suggested_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(String(253), unique=True, nullable=False)
    discovered_from: Mapped[str] = mapped_column(String(253), nullable=False)  # domain asal penemuan
    niche: Mapped[str] = mapped_column(String(100), nullable=False, default="General")
    discovery_source: Mapped[str] = mapped_column(String(30), nullable=False, default="wayback")
    # discovery_source values: "wayback", "crawl", "crtsh", "manual"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_suggested_candidates_domain", "domain"),
        Index("idx_suggested_candidates_created", "created_at"),
    )

    def __repr__(self):
        return f"<SuggestedCandidate {self.id}: {self.domain} (from {self.discovered_from})>"
