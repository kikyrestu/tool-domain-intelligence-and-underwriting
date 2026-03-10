"""SuggestedSource — domain outbound yang ditemukan Wayback, menunggu approval owner."""

from datetime import datetime
from sqlalchemy import String, Text, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class SuggestedSource(Base):
    __tablename__ = "suggested_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    discovered_from: Mapped[str] = mapped_column(String(2048), nullable=False)  # domain yang jadi asal penemuan
    niche: Mapped[str] = mapped_column(String(100), nullable=False, default="General")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<SuggestedSource {self.id}: {self.url}>"
