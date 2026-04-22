"""Google Sheets service for lead management."""

import json
from typing import Any, Dict, List, Optional

from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from app.core.config import get_settings

from datetime import datetime, timedelta

settings = get_settings()


def get_service_account_credentials():
    """Load Google Service Account from environment variable (Render-safe)."""
    service_account_info = json.loads(settings.service_account_json)

    return ServiceAccountCredentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )


class GoogleSheetsService:
    """Service for interacting with Google Sheets API using Service Account."""

    def __init__(self, credentials: Optional[ServiceAccountCredentials] = None):
        self._credentials = credentials
        self._service: Optional[Resource] = None
        self._spreadsheet_id: Optional[str] = None

    @property
    def service(self) -> Resource:
        """Get or create Sheets service."""
        if self._service is None:
            if self._credentials is None:
                self._credentials = get_service_account_credentials()

            self._service = build("sheets", "v4", credentials=self._credentials)

        return self._service

    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        self._spreadsheet_id = spreadsheet_id

    def get_leads(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Fetch all leads from Google Sheet."""
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

            leads = []

            for row in values[1:]:
                if len(row) >= 3:
                    leads.append({
                        "no": int(row[0]) if row[0] else 0,
                        "name": row[1] if len(row) > 1 else "",
                        "email": row[2] if len(row) > 2 else "",
                        "github_url": row[3] if len(row) > 3 else "",
                        "status": row[4] if len(row) > 4 else "pending",
                        "last_contacted_at": row[5] if len(row) > 5 else "",
                        "followup_stage": row[6] if len(row) > 6 else "none",
                    })

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

        leads = self.get_leads(spreadsheet_id)

        for lead in leads:
            if lead.get("email") == email:
                row_number = lead.get("no") + 1

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

        leads = self.get_leads(spreadsheet_id)

        for lead in leads:
            if lead.get("email") == email:
                row_number = lead.get("no") + 1

                updates = {
                    "status": "contacted",
                    "last_contacted_at": datetime.now().isoformat(),
                    "followup_stage": followup_stage,
                }

                return self.update_lead(spreadsheet_id, row_number, updates)

        return False


class LeadManager:
    """Manager for lead sync and updates."""

    def __init__(self, sheets_service: Optional[GoogleSheetsService] = None):
        self.sheets = sheets_service or GoogleSheetsService()
        self._spreadsheet_id: Optional[str] = None

    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        self._spreadsheet_id = spreadsheet_id
        self.sheets.set_spreadsheet_id(spreadsheet_id)

    def sync_leads(self, spreadsheet_id: str):
        self.set_spreadsheet_id(spreadsheet_id)
        return self.sheets.get_leads(spreadsheet_id)

    def get_pending_leads(self, spreadsheet_id: str, followup_stage: str = "none"):
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
    ):
        all_leads = self.sync_leads(spreadsheet_id)
        cutoff = datetime.now() - timedelta(days=days_since_contact)

        ready = []

        for lead in all_leads:
            if lead.get("followup_stage") == stage:
                last = lead.get("last_contacted_at", "")

                if last:
                    try:
                        dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                        if dt < cutoff:
                            ready.append(lead)
                    except Exception:
                        pass

        return ready

    def mark_initial_sent(self, spreadsheet_id: str, email: str):
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "initial")

    def mark_followup1_sent(self, spreadsheet_id: str, email: str):
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "followup1")

    def mark_followup2_sent(self, spreadsheet_id: str, email: str):
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "followup2")


lead_manager = LeadManager()