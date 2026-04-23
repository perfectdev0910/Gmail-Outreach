"""Gmail API service (production-safe, refresh-token based)."""

import base64
import json
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional


# =========================
# GMAIL SERVICE
# =========================

class GmailService:
    """Gmail service using refresh_token ONLY (correct OAuth flow)."""

    def __init__(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret

        self.token_uri = "https://oauth2.googleapis.com/token"
        self.base_url = "https://gmail.googleapis.com/gmail/v1/users/me"

        self.access_token = None

    # =========================
    # TOKEN GENERATION
    # =========================

    def _get_access_token(self) -> Optional[str]:
        """Generate fresh access token from refresh_token."""

        try:
            res = requests.post(
                self.token_uri,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )

            if res.status_code != 200:
                print(f"[GMAIL] Token error: {res.text}")
                return None

            data = res.json()
            self.access_token = data.get("access_token")
            return self.access_token

        except Exception as e:
            print(f"[GMAIL] Token exception: {e}")
            return None

    # =========================
    # HEADERS
    # =========================

    def _headers(self):
        if not self.access_token:
            self._get_access_token()

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # =========================
    # SEND EMAIL
    # =========================

    def send_email(
        self,
        sender: str,
        to: str,
        subject: str,
        body: str,
        thread_id: str = "",
        message_id: str = "",
    ) -> Dict[str, Any]:

        try:
            msg = MIMEMultipart()
            msg["to"] = to
            msg["from"] = sender
            msg["subject"] = subject

            if message_id:
                msg["In-Reply-To"] = message_id
                msg["References"] = message_id

            msg.attach(MIMEText(body, "plain"))

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            payload = {"raw": raw}
            if thread_id:
                payload["threadId"] = thread_id

            res = requests.post(
                f"{self.base_url}/messages/send",
                headers=self._headers(),
                json=payload,
                timeout=15,
            )

            if res.status_code == 200:
                data = res.json()
                return {
                    "success": True,
                    "message_id": data.get("id"),
                    "thread_id": data.get("threadId"),
                    "error": "",
                }

            return {
                "success": False,
                "error": res.text,
                "message_id": "",
                "thread_id": "",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message_id": "",
                "thread_id": "",
            }


# =========================
# ACCOUNT MANAGER
# =========================

class GmailAccountManager:
    """Multi-account manager (FIXED)."""

    def __init__(self):
        self._services: Dict[str, GmailService] = {}

    def add_account(self, account_id: str, oauth: Dict[str, Any]) -> bool:

        refresh_token = oauth.get("refresh_token")
        client_id = oauth.get("client_id")
        client_secret = oauth.get("client_secret")

        missing = []
        if not refresh_token:
            missing.append("refresh_token")
        if not client_id:
            missing.append("client_id")
        if not client_secret:
            missing.append("client_secret")

        if missing:
            print(f"[GMAIL] Missing OAuth fields {account_id}: {missing}")
            return False

        self._services[account_id] = GmailService(
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )

        return True

    def get_service(self, account_id: str) -> Optional[GmailService]:
        return self._services.get(account_id)

    def get_or_create(self, account_id: str, oauth: Dict[str, Any]) -> Optional[GmailService]:
        if account_id not in self._services:
            ok = self.add_account(account_id, oauth)
            if not ok:
                return None

        return self._services.get(account_id)

    def send_with_thread(
        self,
        account_id: str,
        email: str,
        oauth: Dict[str, Any],
        sender: str,
        subject: str,
        body: str,
        thread_id: str = "",
        message_id: str = "",
    ) -> Dict[str, Any]:

        service = self.get_or_create(account_id, oauth)

        if not service:
            return {
                "success": False,
                "error": "Invalid OAuth credentials or account not loaded",
                "message_id": "",
                "thread_id": "",
            }

        return service.send_email(
            sender=sender,
            to=email,
            subject=subject,
            body=body,
            thread_id=thread_id,
            message_id=message_id,
        )


# =========================
# SINGLETON
# =========================

gmail_manager = GmailAccountManager()