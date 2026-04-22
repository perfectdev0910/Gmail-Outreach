"""Google Sheets service for lead management."""

import json
from typing import Any, Dict, List, Optional

import google.auth
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from app.core.config import get_settings

settings = get_settings()


class GoogleSheetsService:
    """Service for interacting with Google Sheets API using Service Account.
    
    No billing required - service accounts have free quota for Sheet reading.
    """

    def __init__(self, credentials: Optional[Credentials] = None):
        self._credentials = credentials
        self._service: Optional[Resource] = None
        self._spreadsheet_id: Optional[str] = None

    @property
    def service(self) -> Resource:
        """Get or create Sheets service."""
        if self._service is None:
            if self._credentials is None:
                # Use service account for free Sheet access
                # Share the sheet with the service account email
                creds = ServiceAccountCredentials.from_service_account_file(
                    "service-account.json",
                    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
                )
                self._credentials = creds
            self._service = build("sheets", "v4", credentials=self._credentials)
        return self._service

    @classmethod
    def from_service_account_json(cls, json_path: str = "service-account.json") -> "GoogleSheetsService":
        """Create service from service account JSON file."""
        creds = ServiceAccountCredentials.from_service_account_file(
            json_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return cls(credentials=creds)

    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        """Set the Google Sheets spreadsheet ID."""
        self._spreadsheet_id = spreadsheet_id

    def get_leads(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Fetch all leads from the Google Sheet.
        
        Expected columns: No, name, email, github_url, status, last_contacted_at, followup_stage
        """
        self.set_spreadsheet_id(spreadsheet_id)
        
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range="Sheet1!A:G")
                .execute()
            )
            
            values = result.get("values", [])
            if not values:
                return []
            
            # First row is headers
            headers = values[0]
            leads = []
            
            # Parse data rows
            for row in values[1:]:
                if len(row) >= 3:  # At least No, name, email
                    lead = {
                        "no": int(row[0]) if row[0] else 0,
                        "name": row[1] if len(row) > 1 else "",
                        "email": row[2] if len(row) > 2 else "",
                        "github_url": row[3] if len(row) > 3 else "",
                        "status": row[4] if len(row) > 4 else "pending",
                        "last_contacted_at": row[5] if len(row) > 5 else "",
                        "followup_stage": row[6] if len(row) > 6 else "none",
                    }
                    leads.append(lead)
            
            return leads
        
        except HttpError as error:
            print(f"Google Sheets API error: {error}")
            return []

    def update_lead(
        self,
        spreadsheet_id: str,
        row_number: int,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a specific lead row in Google Sheets.
        
        Args:
            spreadsheet_id: The Google Sheets ID
            row_number: The row number to update (1-indexed, includes header)
            updates: Dict with column names and new values
        """
        self.set_spreadsheet_id(spreadsheet_id)
        
        # Map field names to column letters
        column_map = {
            "no": "A",
            "name": "B",
            "email": "C",
            "github_url": "D",
            "status": "E",
            "last_contacted_at": "F",
            "followup_stage": "G",
        }
        
        try:
            for field, value in updates.items():
                if field in column_map:
                    column = column_map[field]
                    range_str = f"Sheet1!{column}{row_number}"
                    
                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_str,
                        valueInputOption="USER_ENTERED",
                        body={"values": [[str(value)]]},
                    ).execute()
            
            return True
        
        except HttpError as error:
            print(f"Google Sheets update error: {error}")
            return False

    def update_lead_status(
        self,
        spreadsheet_id: str,
        email: str,
        status: str,
        followup_stage: str = "none",
    ) -> bool:
        """Update lead status by email address."""
        leads = self.get_leads(spreadsheet_id)
        
        for lead in leads:
            if lead.get("email") == email:
                row_number = lead.get("no") + 1  # +1 for header row
                updates = {
                    "status": status,
                    "followup_stage": followup_stage,
                    "last_contacted_at": datetime.now().isoformat(),
                }
                return self.update_lead(spreadsheet_id, row_number, updates)
        
        return False

    def mark_lead_contacted(
        self,
        spreadsheet_id: str,
        email: str,
        followup_stage: str = "none",
    ) -> bool:
        """Mark a lead as contacted with the appropriate follow-up stage."""
        from datetime import datetime
        
        leads = self.get_leads(spreadsheet_id)
        
        for lead in leads:
            if lead.get("email") == email:
                row_number = lead.get("no") + 1  # +1 for header row
                now = datetime.now().isoformat()
                updates = {
                    "status": "contacted",
                    "last_contacted_at": now,
                    "followup_stage": followup_stage,
                }
                return self.update_lead(spreadsheet_id, row_number, updates)
        
        return False


class LeadManager:
    """Manager for lead sync and updates between database and Google Sheets."""

    def __init__(self, sheets_service: Optional[GoogleSheetsService] = None):
        self.sheets = sheets_service or GoogleSheetsService()
        self._spreadsheet_id: Optional[str] = None

    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        """Set the spreadsheet ID for lead operations."""
        self._spreadsheet_id = spreadsheet_id
        self.sheets.set_spreadsheet_id(spreadsheet_id)

    def sync_leads(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Sync leads from Google Sheets."""
        self.set_spreadsheet_id(spreadsheet_id)
        return self.sheets.get_leads(spreadsheet_id)

    def get_pending_leads(
        self,
        spreadsheet_id: str,
        followup_stage: str = "none",
    ) -> List[Dict[str, Any]]:
        """Get leads that need to be contacted."""
        all_leads = self.sync_leads(spreadsheet_id)
        return [
            lead for lead in all_leads
            if lead.get("status") == "pending"
            and lead.get("followup_stage") == followup_stage
        ]

    def get_leads_for_followup(
        self,
        spreadsheet_id: str,
        stage: str,
        days_since_contact: int,
    ) -> List[Dict[str, Any]]:
        """Get leads ready for follow-up based on timing rules."""
        from datetime import datetime, timedelta
        
        all_leads = self.sync_leads(spreadsheet_id)
        cutoff = datetime.now() - timedelta(days=days_since_contact)
        
        ready_leads = []
        for lead in all_leads:
            if lead.get("followup_stage") == stage:
                last_contacted = lead.get("last_contacted_at", "")
                if last_contacted:
                    try:
                        contact_date = datetime.fromisoformat(last_contacted.replace("Z", "+00:00"))
                        if contact_date < cutoff:
                            ready_leads.append(lead)
                    except (ValueError, TypeError):
                        continue
        
        return ready_leads

    def mark_initial_sent(self, spreadsheet_id: str, email: str) -> bool:
        """Mark that initial email was sent to lead."""
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "initial")

    def mark_followup1_sent(self, spreadsheet_id: str, email: str) -> bool:
        """Mark that first follow-up was sent."""
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "followup1")

    def mark_followup2_sent(self, spreadsheet_id: str, email: str) -> bool:
        """Mark that second follow-up was sent."""
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "followup2")


# Singleton instance
lead_manager = LeadManager()