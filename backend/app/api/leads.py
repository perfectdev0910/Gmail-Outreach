"""Leads API endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from app.services.google_sheets import lead_manager

router = APIRouter(prefix="/leads", tags=["leads"])

# Store spreadsheet ID in memory (in production, store in database)
_spreadsheet_id: str = ""


def set_spreadsheet_id(spreadsheet_id: str) -> None:
    """Set the Google Sheets spreadsheet ID."""
    global _spreadsheet_id
    _spreadsheet_id = spreadsheet_id


def get_spreadsheet_id() -> str:
    """Get the current spreadsheet ID."""
    return _spreadsheet_id


@router.get("")
async def get_leads(
    status: str = Query(None, description="Filter by status"),
    followup_stage: str = Query(None, description="Filter by follow-up stage"),
) -> List[Dict[str, Any]]:
    """Get all leads from Google Sheets."""
    if not _spreadsheet_id:
        raise HTTPException(status_code=400, detail="No spreadsheet configured")
    
    leads = lead_manager.sync_leads(_spreadsheet_id)
    
    if status:
        leads = [l for l in leads if l.get("status") == status]
    if followup_stage:
        leads = [l for l in leads if l.get("followup_stage") == followup_stage]
    
    return leads


@router.get("/pending")
async def get_pending_leads() -> List[Dict[str, Any]]:
    """Get leads that need initial contact."""
    if not _spreadsheet_id:
        raise HTTPException(status_code=400, detail="No spreadsheet configured")
    
    return lead_manager.get_pending_leads(_spreadsheet_id)


@router.get("/followup/{stage}")
async def get_leads_for_followup(stage: str) -> List[Dict[str, Any]]:
    """Get leads ready for follow-up.
    
    Args:
        stage: 'initial', 'followup1', or 'followup2'
    """
    if not _spreadsheet_id:
        raise HTTPException(status_code=400, detail="No spreadsheet configured")
    
    from app.core.config import get_settings
    settings = get_settings()
    
    if stage == "followup1":
        days = settings.followup1_days
    elif stage == "followup2":
        days = settings.followup2_days
    else:
        days = 0
    
    return lead_manager.get_leads_for_followup(_spreadsheet_id, stage, days)


@router.post("/sync")
async def sync_leads(spreadsheet_id: str = Query(..., description="Google Sheets ID")) -> Dict[str, Any]:
    """Sync leads from Google Sheets."""
    set_spreadsheet_id(spreadsheet_id)
    leads = lead_manager.sync_leads(spreadsheet_id)
    
    return {
        "spreadsheet_id": spreadsheet_id,
        "total_leads": len(leads),
        "leads": leads[:10],  # Return first 10 as preview
    }


@router.post("/configure")
async def configure_spreadsheet(spreadsheet_id: str) -> Dict[str, str]:
    """Configure the Google Sheets spreadsheet ID."""
    set_spreadsheet_id(spreadsheet_id)
    return {"status": "configured", "spreadsheet_id": spreadsheet_id}


@router.post("/{lead_email}/mark-contacted")
async def mark_lead_contacted(
    lead_email: str,
    followup_stage: str = "initial",
) -> Dict[str, str]:
    """Manually mark a lead as contacted."""
    if not _spreadsheet_id:
        raise HTTPException(status_code=400, detail="No spreadsheet configured")
    
    success = lead_manager.mark_lead_contacted(_spreadsheet_id, lead_email, followup_stage)
    
    if success:
        return {"status": "updated", "email": lead_email}
    raise HTTPException(status_code=404, detail="Lead not found")