"""
Pydantic schemas for CRM API.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    """Schema for creating a new lead."""

    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    company: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "company": "Acme Corp",
                "summary": "Interested in enterprise plan",
            }
        }


class LeadResponse(BaseModel):
    """Schema for lead response."""

    id: UUID
    name: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    summary: Optional[str]
    status: str
    external_id: Optional[str] = None
    provider: str = "none"
    synced_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    """Schema for updating a lead."""

    name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    company: Optional[str] = Field(default=None, max_length=255)
    summary: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)


class EmailRequest(BaseModel):
    """Schema for sending an email."""

    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body (plain text)")

    class Config:
        json_schema_extra = {
            "example": {
                "to": "john@example.com",
                "subject": "Thanks for your interest!",
                "body": "Hi John, thanks for chatting with our AI agent...",
            }
        }


class SyncResponse(BaseModel):
    """Schema for sync operation response."""

    lead_id: UUID
    provider: str
    external_id: Optional[str] = None
    success: bool
    message: str
