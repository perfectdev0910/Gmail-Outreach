"""Gmail API service for sending emails with threading support."""

import base64
import json
import random
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.config import get_settings

settings = get_settings()


class GmailService:
    """Service for Gmail API operations using HTTP requests directly."""

    def __init__(self, access_token: str):
        self._access_token = access_token
        self._base_url = "https://gmail.googleapis.com/gmail/v1/users/me"

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def create_message(
        self,
        sender: str,
        to: str,
        subject: str,
        body: str,
        thread_id: str = "",
        message_id: str = "",
    ) -> Dict[str, Any]:
        """Create a MIME message for email.
        
        Args:
            sender: Sender email address
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            thread_id: Gmail thread ID for threading
            message_id: Original message ID for In-Reply-To header
        """
        msg = MIMEMultipart("mixed")
        msg["to"] = to
        msg["from"] = sender
        msg["subject"] = subject

        # Add threading headers if this is a follow-up
        if message_id:
            msg["In-Reply-To"] = message_id
            msg["References"] = message_id

        # Attach body
        msg.attach(MIMEText(body, "plain"))

        # Encode message
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
        """Send an email via Gmail API REST.
        
        Args:
            sender: Sender email address
            to: Recipient email address
            subject: Email subject
            body: Email body
            thread_id: Gmail thread ID (for follow-ups)
            message_id: Original message ID (for threading)
            
        Returns:
            Dict with 'success', 'message_id', 'thread_id', 'error'
        """
        try:
            message = self.create_message(
                sender=sender,
                to=to,
                subject=subject,
                body=body,
                thread_id=thread_id,
                message_id=message_id,
            )

            response = requests.post(
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
            response = requests.get(
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
            response = requests.get(
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
        
        Args:
            account_id: Unique account identifier
            email: Gmail address
            oauth_credentials: OAuth2 tokens dict with 'access_token', 'refresh_token', etc.
        """
        try:
            access_token = oauth_credentials.get("access_token", "")
            if not access_token:
                print(f"No access token for account {account_id}")
                return False

            self._services[account_id] = GmailService(access_token)
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
        """Get or create Gmail service for an account.
        
        Creates service if not already cached.
        """
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
        """Send email with threading support.
        
        Args:
            account_id: Account identifier
            email: Recipient email
            oauth_credentials: OAuth credentials
            sender: Sender email
            subject: Email subject
            body: Email body
            thread_id: Existing thread ID for follow-ups
            message_id: Original message ID for headers
        """
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