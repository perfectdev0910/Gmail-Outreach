"""Google Sheets service for lead management (Render-safe + rate-limit safe)."""

import json
import time
from typing import Any, Dict, List, Optional

from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from datetime import datetime, timedelta

settings = get_settings()


# =========================
# SERVICE ACCOUNT LOADER
# =========================

def get_service_account_credentials():
    """Load Google Service Account from Render env variable."""

    if not settings.service_account_json:
        raise ValueError("Missing SERVICE_ACCOUNT_JSON")

    try:
        info = json.loads(settings.service_account_json)
    except json.JSONDecodeError as e:
        raise ValueError("Invalid SERVICE_ACCOUNT_JSON") from e

    return ServiceAccountCredentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )


# =========================
# SHEETS SERVICE
# =========================

class GoogleSheetsService:
    """
    Production-safe Google Sheets client:
    - caches reads (prevents 429)
    - minimizes API calls
    """

    def __init__(self, credentials: Optional[ServiceAccountCredentials] = None):
        self._credentials = credentials
        self._service: Optional[Resource] = None
        self._spreadsheet_id: Optional[str] = None

        # 🔥 CACHE (IMPORTANT FIX FOR 429)
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl = 60  # seconds

    @property
    def service(self) -> Resource:
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

    def set_spreadsheet_id(self, spreadsheet_id: str):
        self._spreadsheet_id = spreadsheet_id

    # =========================
    # CACHE WRAPPER
    # =========================
    def _get_cached(self, key: str):
        if time.time() - self._cache_time < self._cache_ttl:
            return self._cache.get(key)
        return None

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = value
        self._cache_time = time.time()

    # =========================
    # READ LEADS (CACHED)
    # =========================
    def get_leads(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        self.set_spreadsheet_id(spreadsheet_id)

        cache_key = f"leads_{spreadsheet_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

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

            leads = []

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

            self._set_cache(cache_key, leads)
            return leads

        except HttpError as e:
            print("[Sheets ERROR]", e)
            return []

    # =========================
    # UPDATE LEAD
    # =========================
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

                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"Sheet1!{column_map[field]}{row_number}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[str(value)]]},
                ).execute()

            # invalidate cache after update
            self._cache.clear()

            return True

        except HttpError as e:
            print("[Sheets UPDATE ERROR]", e)
            return False

    # =========================
    # UPDATE BY EMAIL
    # =========================
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
                row = lead.get("no", 0) + 1

                return self.update_lead(
                    spreadsheet_id,
                    row,
                    {
                        "status": status,
                        "followup_stage": followup_stage,
                        "last_contacted_at": datetime.utcnow().isoformat(),
                    },
                )

        return False

    # =========================
    # MARK CONTACTED
    # =========================
    def mark_lead_contacted(
        self,
        spreadsheet_id: str,
        email: str,
        followup_stage: str = "none",
    ) -> bool:

        leads = self.get_leads(spreadsheet_id)

        for lead in leads:
            if lead.get("email") == email:
                row = lead.get("no", 0) + 1

                return self.update_lead(
                    spreadsheet_id,
                    row,
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
    def __init__(self, sheets_service: Optional[GoogleSheetsService] = None):
        self.sheets = sheets_service or GoogleSheetsService()

    def sync_leads(self, spreadsheet_id: str):
        return self.sheets.get_leads(spreadsheet_id)

    def get_pending_leads(self, spreadsheet_id: str, followup_stage: str = "none"):
        return [
            l for l in self.sync_leads(spreadsheet_id)
            if l.get("status") == "pending"
            and l.get("followup_stage") == followup_stage
        ]

    def get_leads_for_followup(self, spreadsheet_id: str, stage: str, days_since_contact: int):
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


lead_manager = LeadManager()