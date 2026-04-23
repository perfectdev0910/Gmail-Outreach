"""Gmail API service for sending emails with threading support."""

import base64
import json
import time
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

settings = get_settings()


class GmailService:
    """Service for Gmail API operations using OAuth2 with token refresh."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_uri = "https://oauth2.googleapis.com/token"
        self._base_url = "https://gmail.googleapis.com/gmail/v1/users/me"

    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh_token."""
        try:
            response = requests.post(
                self._token_uri,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token", "")
                print(f"✓ Refreshed access token for Gmail account")
                return True
            else:
                print(f"✗ Token refresh failed: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Token refresh error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make request with automatic token refresh on 401."""
        response = requests.request(method, url, **kwargs)
        
        # If 401, try refreshing token and retry once
        if response.status_code == 401:
            if self._refresh_access_token():
                kwargs["headers"] = self._get_headers()
                response = requests.request(method, url, **kwargs)
        
        return response

    def create_message(
        self,
        sender: str,
        to: str,
        subject: str,
        body: str,
        thread_id: str = "",
        message_id: str = "",
    ) -> Dict[str, Any]:
        """Create a MIME message for email."""
        msg = MIMEMultipart("mixed")
        msg["to"] = to
        msg["from"] = sender
        msg["subject"] = subject

        if message_id:
            msg["In-Reply-To"] = message_id
            msg["References"] = message_id

        msg.attach(MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        
        result = {"raw": raw}
        if thread_id:
            result["threadId"] = thread_id
        
        return result

    def send_email(
        self,
        sender: str,
        to: str,
        subject: str,
        body: str,
        thread_id: str = "",
        message_id: str = "",
    ) -> Dict[str, Any]:
        """Send an email via Gmail API REST with automatic token refresh."""
        try:
            message = self.create_message(
                sender=sender,
                to=to,
                subject=subject,
                body=body,
                thread_id=thread_id,
                message_id=message_id,
            )

            response = self._make_request(
                "POST",
                f"{self._base_url}/messages/send",
                headers=self._get_headers(),
                json=message,
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message_id": result.get("id", ""),
                    "thread_id": result.get("threadId", ""),
                    "error": "",
                }
            else:
                return {
                    "success": False,
                    "message_id": "",
                    "thread_id": "",
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

        except Exception as error:
            print(f"Unexpected error: {error}")
            return {
                "success": False,
                "message_id": "",
                "thread_id": "",
                "error": str(error),
            }

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get thread details."""
        try:
            response = self._make_request(
                "GET",
                f"{self._base_url}/threads/{thread_id}",
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def list_messages(
        self,
        max_results: int = 10,
        query: str = "",
    ) -> List[Dict[str, Any]]:
        """List recent messages."""
        try:
            response = self._make_request(
                "GET",
                f"{self._base_url}/messages",
                headers=self._get_headers(),
                params={"maxResults": max_results, "q": query},
            )
            if response.status_code == 200:
                return response.json().get("messages", [])
            return []
        except Exception:
            return []


class GmailAccountManager:
    """Manager for multi-account Gmail operations."""

    def __init__(self):
        self._services: Dict[str, GmailService] = {}

    def add_account(
        self,
        account_id: str,
        email: str,
        oauth_credentials: Dict[str, Any],
    ) -> bool:
        """Add a Gmail account with OAuth credentials.
        
        Required fields in oauth_credentials:
        - access_token
        - refresh_token
        - client_id
        - client_secret
        """
        try:
            access_token = oauth_credentials.get("access_token", "")
            refresh_token = oauth_credentials.get("refresh_token", "")
            client_id = oauth_credentials.get("client_id", "")
            client_secret = oauth_credentials.get("client_secret", "")

            if not all([access_token, refresh_token, client_id, client_secret]):
                print(f"Missing OAuth fields for account {account_id}")
                return False

            self._services[account_id] = GmailService(
                access_token=access_token,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
            )
            return True

        except Exception as error:
            print(f"Failed to add account {account_id}: {error}")
            return False

    def get_service(self, account_id: str) -> Optional[GmailService]:
        """Get Gmail service for an account."""
        return self._services.get(account_id)

    def get_service_for_account(
        self,
        account_id: str,
        oauth_credentials: Dict[str, Any],
    ) -> GmailService:
        """Get or create Gmail service for an account."""
        if account_id not in self._services:
            self.add_account(account_id, "", oauth_credentials)
        return self._services.get(account_id)

    def send_with_thread(
        self,
        account_id: str,
        email: str,
        oauth_credentials: Dict[str, Any],
        sender: str,
        subject: str,
        body: str,
        thread_id: str = "",
        message_id: str = "",
    ) -> Dict[str, Any]:
        """Send email with threading support."""
        service = self.get_service_for_account(account_id, oauth_credentials)
        
        if service is None:
            return {
                "success": False,
                "message_id": "",
                "thread_id": "",
                "error": "Account not found",
            }

        return service.send_email(
            sender=sender,
            to=email,
            subject=subject,
            body=body,
            thread_id=thread_id,
            message_id=message_id,
        )

    def remove_account(self, account_id: str) -> bool:
        """Remove an account from the manager."""
        if account_id in self._services:
            del self._services[account_id]
        return True


# Global instances
gmail_manager = GmailAccountManager()