"""System state model for storing key-value app configurations and health flags."""

from sqlalchemy import Column, String, DateTime, text
from datetime import datetime

from app.database import Base


class SystemState(Base):
    __tablename__ = "system_states"

    key = Column(String(50), primary_key=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
