"""Gmail API service for sending emails with threading support."""

import base64
import json
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import google.auth
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from app.core.config import get_settings

settings = get_settings()


class GmailService:
    """Service for Gmail API operations."""

    def __init__(self, credentials: Optional[Credentials] = None):
        self._credentials = credentials
        self._service: Optional[Resource] = None

    @property
    def service(self) -> Resource:
        """Get or create Gmail service."""
        if self._service is None:
            if self._credentials is None:
                self._credentials, _ = google.auth.default()
            self._service = build("gmail", "v1", credentials=self._credentials)
        return self._service

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
        """Send an email via Gmail API.
        
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

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body=message)
                .execute()
            )

            return {
                "success": True,
                "message_id": result.get("id", ""),
                "thread_id": result.get("threadId", ""),
                "error": "",
            }

        except HttpError as error:
            print(f"Gmail API error: {error}")
            return {
                "success": False,
                "message_id": "",
                "thread_id": "",
                "error": str(error),
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
            result = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id)
                .execute()
            )
            return result
        except HttpError:
            return None

    def get_messages_in_thread(
        self,
        thread_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all messages in a thread."""
        thread = self.get_thread(thread_id)
        if thread:
            return thread.get("messages", [])
        return []

    def list_messages(
        self,
        max_results: int = 10,
        query: str = "",
    ) -> List[Dict[str, Any]]:
        """List recent messages."""
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", maxResults=max_results, q=query)
                .execute()
            )
            return results.get("messages", [])
        except HttpError:
            return []


class GmailAccountManager:
    """Manager for multi-account Gmail operations."""

    def __init__(self):
        self._accounts: Dict[str, Credentials] = {}
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
            credentials = Credentials(
                token=oauth_credentials.get("access_token", ""),
                refresh_token=oauth_credentials.get("refresh_token", ""),
                token_uri=oauth_credentials.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=[
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.readonly",
                ],
            )

            self._accounts[account_id] = credentials
            self._services[account_id] = GmailService(credentials)
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
        if account_id in self._accounts:
            del self._accounts[account_id]
        if account_id in self._services:
            del self._services[account_id]
        return True


# Global instances
gmail_service = GmailService()
gmail_manager = GmailAccountManager()