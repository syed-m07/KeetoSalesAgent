"""
User model for authentication.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class User(Base):
    """User model for storing authenticated users."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)  # e.g., "CTO", "Developer", "Sales"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Conversation memory fields
    last_conversation_summary = Column(Text, nullable=True)  # Stores AI-generated summary
    last_active_at = Column(DateTime, nullable=True)  # When user last chatted

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"

    def to_context_dict(self) -> dict:
        """Convert user to context dictionary for agent prompts."""
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "company": self.company or "Unknown Company",
            "role": self.role or "Professional",
            "last_conversation_summary": self.last_conversation_summary or "",
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
