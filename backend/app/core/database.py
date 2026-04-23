"""Database client for Supabase connection (production-safe fixed version)."""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from supabase import Client, create_client
from app.core.config import get_settings

settings = get_settings()


# =========================
# SUPABASE CLIENT
# =========================

def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_key)


# =========================
# DATABASE WRAPPER
# =========================

class Database:
    """Production-safe Supabase wrapper."""

    def __init__(self):
        self.client: Optional[Client] = None

    def connect(self) -> None:
        self.client = get_supabase_client()

    @property
    def supabase(self) -> Client:
        if self.client is None:
            self.connect()
        return self.client

    # =========================
    # GMAIL ACCOUNTS
    # =========================

    def get_gmail_accounts(self):
        res = self.supabase.table("gmail_accounts").select("*").execute()
        return res.data or []

    def get_active_gmail_accounts(self):
        res = (
            self.supabase.table("gmail_accounts")
            .select("*")
            .eq("status", "active")
            .execute()
        )
        return res.data or []

    def get_gmail_account(self, account_id: str):
        res = (
            self.supabase.table("gmail_accounts")
            .select("*")
            .eq("id", account_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def add_gmail_account(self, email: str, oauth_credentials: Dict[str, Any], status="active"):
        data = {
            "email": email,
            "oauth_credentials": json.dumps(oauth_credentials),
            "status": status,
            "daily_sent_count": 0,
            "hourly_sent_count": 0,
            "last_sent_at": None,
        }

        res = self.supabase.table("gmail_accounts").insert(data).execute()
        return res.data[0] if res.data else {}

    def update_gmail_account(self, account_id: str, updates: Dict[str, Any]):
        if "oauth_credentials" in updates:
            updates["oauth_credentials"] = json.dumps(updates["oauth_credentials"])

        res = (
            self.supabase.table("gmail_accounts")
            .update(updates)
            .eq("id", account_id)
            .execute()
        )

        return res.data[0] if res.data else {}

    # =========================
    # COUNTERS (SAFE FIX)
    # =========================

    def increment_sent_count(self, account_id: str):
        acc = self.get_gmail_account(account_id)
        if not acc:
            return

        self.supabase.table("gmail_accounts").update({
            "daily_sent_count": (acc.get("daily_sent_count", 0) + 1),
            "hourly_sent_count": (acc.get("hourly_sent_count", 0) + 1),
            "last_sent_at": datetime.utcnow().isoformat(),
        }).eq("id", account_id).execute()

    # ❌ FIX: avoid unsafe global UPDATE without WHERE crash
    def reset_hourly_counts(self):
        self.supabase.table("gmail_accounts").update({
            "hourly_sent_count": 0
        }).eq("status", "active").execute()

    def reset_daily_counts(self):
        self.supabase.table("gmail_accounts").update({
            "daily_sent_count": 0
        }).eq("status", "active").execute()

    # =========================
    # CAMPAIGN STATE (FIXED MISSING METHOD)
    # =========================

    def get_campaign_state(self):
        res = self.supabase.table("campaign_state").select("*").limit(1).execute()

        if res.data:
            return res.data[0]

        default = {
            "is_running": False,
            "is_paused": False,
            "skip_today": False,
            "last_run_date": None,
        }

        created = self.supabase.table("campaign_state").insert(default).execute()
        return created.data[0] if created.data else default

    def update_campaign_state(self, updates: Dict[str, Any]):
        """
        FIX: This was missing → caused your crash in worker.py
        """

        state = self.get_campaign_state()

        if not state or "id" not in state:
            return {}

        res = (
            self.supabase.table("campaign_state")
            .update(updates)
            .eq("id", state["id"])
            .execute()
        )

        return res.data[0] if res.data else {}

    # =========================
    # EMAIL LOGS (FIXED SCHEMA)
    # =========================

    def add_email_log(
        self,
        lead_email: str,
        account_id: str,
        log_type: str,
        status: str,
        openai_output: str = "",
        error_message: str = "",
        thread_id: str = "",
        message_id: str = "",
    ):
        """
        FIX: column name is `type` NOT `log_type`
        """

        data = {
            "lead_email": lead_email,
            "account_id": account_id,
            "type": log_type,   # IMPORTANT FIX
            "status": status,
            "openai_output": openai_output,
            "error_message": error_message,
            "thread_id": thread_id,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        res = self.supabase.table("email_logs").insert(data).execute()
        return res.data[0] if res.data else {}

    def get_email_logs(self, limit=100, offset=0):
        res = (
            self.supabase.table("email_logs")
            .select("*")
            .order("timestamp", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return res.data or []

    def get_recent_logs(self, hours=24, limit=50):
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        res = (
            self.supabase.table("email_logs")
            .select("*")
            .gte("timestamp", cutoff.isoformat())
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )

        return res.data or []

    def get_last_email_to_lead(self, lead_email: str):
        res = (
            self.supabase.table("email_logs")
            .select("*")
            .eq("lead_email", lead_email)
            .eq("status", "sent")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        return res.data[0] if res.data else None


# =========================
# SINGLETON
# =========================

db = Database()