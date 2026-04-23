"""Database client for Supabase connection (production-safe)."""

import json
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from app.core.config import get_settings

settings = get_settings()


def get_supabase_client() -> Client:
    """Create and return Supabase client."""
    return create_client(settings.supabase_url, settings.supabase_key)


class Database:
    """Database operations wrapper for Supabase."""

    def __init__(self):
        self.client: Optional[Client] = None

    def connect(self) -> None:
        """Initialize the database connection."""
        self.client = get_supabase_client()

    @property
    def supabase(self) -> Client:
        """Get Supabase client, connecting if needed."""
        if self.client is None:
            self.connect()
        return self.client

    # =========================
    # GMAIL ACCOUNTS
    # =========================

    def get_gmail_accounts(self) -> List[Dict[str, Any]]:
        response = self.supabase.table("gmail_accounts").select("*").execute()
        return response.data or []

    def get_active_gmail_accounts(self) -> List[Dict[str, Any]]:
        response = (
            self.supabase.table("gmail_accounts")
            .select("*")
            .eq("status", "active")
            .execute()
        )
        return response.data or []

    def get_gmail_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        response = (
            self.supabase.table("gmail_accounts")
            .select("*")
            .eq("id", account_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def add_gmail_account(
        self,
        email: str,
        oauth_credentials: Dict[str, Any],
        status: str = "active",
    ) -> Dict[str, Any]:

        data = {
            "email": email,
            "oauth_credentials": json.dumps(oauth_credentials),
            "status": status,
            "daily_sent_count": 0,
            "hourly_sent_count": 0,
        }

        response = self.supabase.table("gmail_accounts").insert(data).execute()
        return response.data[0] if response.data else {}

    def update_gmail_account(
        self,
        account_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:

        if "oauth_credentials" in updates:
            updates["oauth_credentials"] = json.dumps(updates["oauth_credentials"])

        response = (
            self.supabase.table("gmail_accounts")
            .update(updates)
            .eq("id", account_id)  # ✅ REQUIRED WHERE
            .execute()
        )
        return response.data[0] if response.data else {}

    def delete_gmail_account(self, account_id: str) -> bool:
        response = (
            self.supabase.table("gmail_accounts")
            .delete()
            .eq("id", account_id)
            .execute()
        )
        return len(response.data) > 0

    def increment_sent_count(self, account_id: str) -> None:
        account = self.get_gmail_account(account_id)

        if account:
            self.update_gmail_account(
                account_id,
                {
                    "daily_sent_count": account.get("daily_sent_count", 0) + 1,
                    "hourly_sent_count": account.get("hourly_sent_count", 0) + 1,
                    "last_sent_at": "now()",
                },
            )

    # =========================
    # 🚨 FIXED: SAFE RESETS
    # =========================

    def reset_hourly_counts(self) -> None:
        """Reset hourly counts safely (NO crash)."""

        accounts = self.supabase.table("gmail_accounts").select("id").execute().data or []

        for acc in accounts:
            self.supabase.table("gmail_accounts") \
                .update({"hourly_sent_count": 0}) \
                .eq("id", acc["id"]) \
                .execute()

    def reset_daily_counts(self) -> None:
        """Reset daily counts safely (NO crash)."""

        accounts = self.supabase.table("gmail_accounts").select("id").execute().data or []

        for acc in accounts:
            self.supabase.table("gmail_accounts") \
                .update({"daily_sent_count": 0}) \
                .eq("id", acc["id"]) \
                .execute()

    # =========================
    # CAMPAIGN STATE
    # =========================

    def get_campaign_state(self) -> Dict[str, Any]:
        response = self.supabase.table("campaign_state").select("*").limit(1).execute()

        if response.data:
            return response.data[0]

        default_state = {
            "is_running": False,
            "is_paused": False,
            "skip_today": False,
            "last_run_date": None,
        }

        response = self.supabase.table("campaign_state").insert(default_state).execute()
        return response.data[0] if response.data else default_state

    def update_campaign_state(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        state = self.get_campaign_state()

        if state:
            response = (
                self.supabase.table("campaign_state")
                .update(updates)
                .eq("id", state["id"])  # ✅ REQUIRED WHERE
                .execute()
            )
            return response.data[0] if response.data else {}

        return {}

    # =========================
    # EMAIL LOGS
    # =========================

    def get_email_logs(self, limit: int = 100, offset: int = 0):
        response = (
            self.supabase.table("email_logs")
            .select("*")
            .order("timestamp", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []

    def get_recent_logs(self, hours: int = 24, limit: int = 50):
        import datetime

        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

        response = (
            self.supabase.table("email_logs")
            .select("*")
            .gte("timestamp", cutoff.isoformat())
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

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

        data = {
            "lead_email": lead_email,
            "account_id": account_id,
            "type": log_type,
            "status": status,
            "openai_output": openai_output,
            "error_message": error_message,
            "thread_id": thread_id,
            "message_id": message_id,
        }

        response = self.supabase.table("email_logs").insert(data).execute()
        return response.data[0] if response.data else {}

    def get_lead_logs(self, lead_email: str):
        response = (
            self.supabase.table("email_logs")
            .select("*")
            .eq("lead_email", lead_email)
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data or []

    def get_last_email_to_lead(self, lead_email: str):
        response = (
            self.supabase.table("email_logs")
            .select("*")
            .eq("lead_email", lead_email)
            .eq("status", "sent")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None


# Singleton
db = Database()