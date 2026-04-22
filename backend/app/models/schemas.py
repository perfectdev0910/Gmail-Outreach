"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Account Models
class GmailAccountCreate(BaseModel):
    """Request model for adding a Gmail account."""
    email: EmailStr
    oauth_credentials: Dict[str, Any] = Field(default_factory=dict)


class GmailAccountUpdate(BaseModel):
    """Request model for updating a Gmail account."""
    status: Optional[str] = None
    daily_sent_count: Optional[int] = None
    hourly_sent_count: Optional[int] = None


class GmailAccountResponse(BaseModel):
    """Response model for Gmail account."""
    id: UUID
    email: str
    oauth_credentials: Dict[str, Any]
    status: str
    daily_sent_count: int
    hourly_sent_count: int
    last_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Campaign State Models
class CampaignStateResponse(BaseModel):
    """Response model for campaign state."""
    id: UUID
    is_running: bool
    is_paused: bool
    skip_today: bool
    last_run_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignStatusResponse(BaseModel):
    """Simplified campaign status response."""
    is_running: bool
    is_paused: bool
    skip_today: bool
    last_run_date: Optional[str] = None
    today_emails_sent: int = 0
    active_accounts: int = 0
    paused_accounts: int = 0


# Email Log Models
class EmailLogCreate(BaseModel):
    """Request model for creating email log."""
    lead_email: EmailStr
    account_id: UUID
    log_type: str  # initial, followup1, followup2
    status: str  # sent, failed, pending
    openai_output: str = ""
    error_message: str = ""
    thread_id: str = ""
    message_id: str = ""


class EmailLogResponse(BaseModel):
    """Response model for email log."""
    id: UUID
    lead_email: str
    account_id: Optional[UUID] = None
    log_type: str
    status: str
    openai_output: str = ""
    error_message: str = ""
    thread_id: str = ""
    message_id: str = ""
    timestamp: datetime

    class Config
        from_attributes = True


# Lead Models
class Lead(BaseModel):
    """Lead model from Google Sheets."""
    no: int
    name: str
    email: EmailStr
    github_url: str = ""
    status: str = "pending"
    last_contacted_at: Optional[datetime] = None
    followup_stage: str = "none"


class LeadUpdate(BaseModel):
    """Request model for updating a lead."""
    status: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    followup_stage: Optional[str] = None


# Overview Stats
class OverviewStats(BaseModel):
    """Overview statistics for dashboard."""
    total_emails_today: int = 0
    active_accounts: int = 0
    paused_accounts: int = 0
    campaign_status: str = "stopped"
    queue_size: int = 0
    pending_followups: int = 0