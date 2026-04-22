"""Campaign management API endpoints."""

from fastapi import APIRouter, HTTPException

from app.core.database import db
from app.services.worker import worker

router = APIRouter(prefix="/campaign", tags=["campaign"])


@router.post("/start")
async def start_campaign(spreadsheet_id: str):
    """Start the email campaign.
    
    Args:
        spreadsheet_id: Google Sheets ID containing leads
    """
    # Update campaign state
    db.update_campaign_state({"is_running": True, "is_paused": False})
    
    # Start worker
    success = worker.start(spreadsheet_id)
    
    if success:
        return {"status": "started", "spreadsheet_id": spreadsheet_id}
    raise HTTPException(status_code=400, detail="Campaign already running")


@router.post("/pause")
async def pause_campaign():
    """Pause the campaign (stops sending but keeps worker running)."""
    success = worker.pause()
    
    if success:
        db.update_campaign_state({"is_paused": True})
        return {"status": "paused"}
    raise HTTPException(status_code=400, detail="Campaign not running")


@router.post("/resume")
async def resume_campaign():
    """Resume the campaign."""
    success = worker.resume()
    
    if success:
        db.update_campaign_state({"is_paused": False})
        return {"status": "resumed"}
    raise HTTPException(status_code=400, detail="Campaign not running")


@router.post("/stop")
async def stop_campaign():
    """Stop the campaign completely."""
    db.update_campaign_state({"is_running": False, "is_paused": False})
    
    success = worker.stop()
    
    return {"status": "stopped"}


@router.get("/status")
async def get_campaign_status():
    """Get current campaign status."""
    campaign_state = db.get_campaign_state()
    accounts = db.get_gmail_accounts()
    
    active_count = sum(1 for a in accounts if a.get("status") == "active")
    paused_count = sum(1 for a in accounts if a.get("status") == "paused")
    today_sent = sum(a.get("daily_sent_count", 0) for a in accounts)
    
    return {
        "is_running": campaign_state.get("is_running", False),
        "is_paused": campaign_state.get("is_paused", False),
        "skip_today": campaign_state.get("skip_today", False),
        "last_run_date": campaign_state.get("last_run_date"),
        "today_emails_sent": today_sent,
        "active_accounts": active_count,
        "paused_accounts": paused_count,
        "worker_running": worker.is_running,
        "worker_paused": worker.is_paused,
    }


@router.post("/skip-today")
async def skip_today():
    """Skip today's campaign run."""
    db.update_campaign_state({"skip_today": True})
    return {"status": "skip_today_set"}


@router.delete("/skip-today")
async def clear_skip_today():
    """Clear skip today flag."""
    db.update_campaign_state({"skip_today": False})
    return {"status": "skip_today_cleared"}