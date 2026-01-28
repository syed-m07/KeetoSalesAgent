"""
Lead model for CRM.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum

from .database import Base


class LeadStatus(str, enum.Enum):
    """Status of a lead in the pipeline."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class Lead(Base):
    """Lead model for storing prospect information."""

    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(
        SQLEnum(LeadStatus, name="lead_status"),
        default=LeadStatus.NEW,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.name}', status='{self.status}')>"
