"""Google Sheets service for lead management (Render-safe, production-ready)."""

import json
from typing import Any, Dict, List, Optional

from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from datetime import datetime, timedelta

settings = get_settings()


# =========================
# SAFE CREDENTIAL LOADER
# =========================

def get_service_account_credentials():
    """
    Load Google Service Account from Render environment variable.

    Expected:
    SERVICE_ACCOUNT_JSON = full JSON string
    """

    if not settings.service_account_json:
        raise ValueError("Missing SERVICE_ACCOUNT_JSON in environment")

    try:
        service_account_info = json.loads(settings.service_account_json)
    except json.JSONDecodeError as e:
        raise ValueError("Invalid SERVICE_ACCOUNT_JSON format") from e

    return ServiceAccountCredentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )


# =========================
# SHEETS SERVICE
# =========================

class GoogleSheetsService:
    """Google Sheets API wrapper (service account based)."""

    def __init__(self, credentials: Optional[ServiceAccountCredentials] = None):
        self._credentials = credentials
        self._service: Optional[Resource] = None
        self._spreadsheet_id: Optional[str] = None

    @property
    def service(self) -> Resource:
        """Lazy init Google Sheets client."""
        if self._service is None:
            if self._credentials is None:
                self._credentials = get_service_account_credentials()

            self._service = build(
                "sheets",
                "v4",
                credentials=self._credentials,
                cache_discovery=False,
            )

        return self._service

    # -------------------------
    # CONFIG
    # -------------------------
    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        self._spreadsheet_id = spreadsheet_id

    # -------------------------
    # READ LEADS
    # -------------------------
    def get_leads(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        self.set_spreadsheet_id(spreadsheet_id)

        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range="Sheet1!A:G",
                )
                .execute()
            )

            values = result.get("values", [])
            if not values or len(values) < 2:
                return []

            leads: List[Dict[str, Any]] = []

            for row in values[1:]:
                if not row:
                    continue

                leads.append({
                    "no": int(row[0]) if len(row) > 0 and str(row[0]).isdigit() else 0,
                    "name": row[1] if len(row) > 1 else "",
                    "email": row[2] if len(row) > 2 else "",
                    "github_url": row[3] if len(row) > 3 else "",
                    "status": row[4] if len(row) > 4 else "pending",
                    "last_contacted_at": row[5] if len(row) > 5 else "",
                    "followup_stage": row[6] if len(row) > 6 else "none",
                })

            return leads

        except HttpError as error:
            print(f"[Google Sheets] Read error: {error}")
            return []

    # -------------------------
    # UPDATE CELL
    # -------------------------
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
                if field not in column_map:
                    continue

                range_str = f"Sheet1!{column_map[field]}{row_number}"

                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_str,
                    valueInputOption="USER_ENTERED",
                    body={"values": [[str(value)]]},
                ).execute()

            return True

        except HttpError as error:
            print(f"[Google Sheets] Update error: {error}")
            return False

    # -------------------------
    # UPDATE BY EMAIL
    # -------------------------
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
                row_number = lead.get("no", 0) + 1

                return self.update_lead(
                    spreadsheet_id,
                    row_number,
                    {
                        "status": status,
                        "followup_stage": followup_stage,
                        "last_contacted_at": datetime.utcnow().isoformat(),
                    },
                )

        return False

    # -------------------------
    # MARK CONTACTED
    # -------------------------
    def mark_lead_contacted(
        self,
        spreadsheet_id: str,
        email: str,
        followup_stage: str = "none",
    ) -> bool:

        leads = self.get_leads(spreadsheet_id)

        for lead in leads:
            if lead.get("email") == email:
                row_number = lead.get("no", 0) + 1

                return self.update_lead(
                    spreadsheet_id,
                    row_number,
                    {
                        "status": "contacted",
                        "followup_stage": followup_stage,
                        "last_contacted_at": datetime.utcnow().isoformat(),
                    },
                )

        return False


# =========================
# LEAD MANAGER
# =========================

class LeadManager:
    """Business logic layer for leads."""

    def __init__(self, sheets_service: Optional[GoogleSheetsService] = None):
        self.sheets = sheets_service or GoogleSheetsService()

    def sync_leads(self, spreadsheet_id: str):
        return self.sheets.get_leads(spreadsheet_id)

    def get_pending_leads(self, spreadsheet_id: str, followup_stage: str = "none"):
        leads = self.sync_leads(spreadsheet_id)

        return [
            l for l in leads
            if l.get("status") == "pending"
            and l.get("followup_stage") == followup_stage
        ]

    def get_leads_for_followup(
        self,
        spreadsheet_id: str,
        stage: str,
        days_since_contact: int,
    ):
        leads = self.sync_leads(spreadsheet_id)
        cutoff = datetime.utcnow() - timedelta(days=days_since_contact)

        result = []

        for lead in leads:
            if lead.get("followup_stage") != stage:
                continue

            last = lead.get("last_contacted_at")
            if not last:
                continue

            try:
                dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if dt < cutoff:
                    result.append(lead)
            except Exception:
                continue

        return result

    def mark_initial_sent(self, spreadsheet_id: str, email: str):
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "initial")

    def mark_followup1_sent(self, spreadsheet_id: str, email: str):
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "followup1")

    def mark_followup2_sent(self, spreadsheet_id: str, email: str):
        return self.sheets.mark_lead_contacted(spreadsheet_id, email, "followup2")


# Singleton
lead_manager = LeadManager()