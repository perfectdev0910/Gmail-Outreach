"""Email logs API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from app.core.database import db

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def get_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    lead_email: Optional[str] = None,
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    log_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get email logs with optional filters."""
    if lead_email:
        return db.get_lead_logs(lead_email)
    
    return db.get_email_logs(limit=limit, offset=offset)


@router.get("/recent")
async def get_recent_logs(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Get recent email logs (last N hours)."""
    return db.get_recent_logs(hours=hours, limit=limit)


@router.get("/stats")
async def get_log_stats() -> Dict[str, Any]:
    """Get log statistics."""
    logs = db.get_recent_logs(hours=24, limit=1000)
    
    total = len(logs)
    sent = sum(1 for l in logs if l.get("status") == "sent")
    failed = sum(1 for l in logs if l.get("status") == "failed")
    
    by_type = {}
    for log in logs:
        log_type = log.get("type", "unknown")
        by_type[log_type] = by_type.get(log_type, 0) + 1
    
    return {
        "total_24h": total,
        "sent_24h": sent,
        "failed_24h": failed,
        "by_type": by_type,
    }


@router.get("/by-lead/{lead_email}")
async def get_lead_logs(lead_email: str) -> List[Dict[str, Any]]:
    """Get all logs for a specific lead."""
    return db.get_lead_logs(lead_email)


@router.get("/lead/{lead_email}")
async def get_lead_last_email(lead_email: str) -> Optional[Dict[str, Any]]:
    """Get the last email sent to a lead."""
    return db.get_last_email_to_lead(lead_email)