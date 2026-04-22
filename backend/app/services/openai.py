"""OpenAI service for email content generation."""

import json
import random
from typing import Any, Dict, Optional

from openai import Client

from app.core.config import get_settings

settings = get_settings()


# Email templates to guide AI generation and ensure quality
INITIAL_EMAIL_GUIDELINES = """You are writing a personalized outreach email to a developer.
- Write 80-150 words
- Natural, friendly tone
- Mention something specific from their GitHub profile/repo
- Be genuine - not salesy or spammy
- Include a clear call-to-action
- End with a casual sign-off
- NO all caps, NO excessive punctuation, NO spam words
- Avoid: "free", "guaranteed", "act now", "limited time", "exclusive deal"
"""

FOLLOWUP1_GUIDELINES = """You are writing a follow-up email to a developer you previously reached out to.
- Write 40-80 words (shorter than initial)
- Softer, lower-pressure tone
- Reference the previous email casually
- Add new value or perspective
- Keep it brief and conversational
- End casually
- NO pushy language
"""

FOLLOWUP2_GUIDELINES = """You are writing a final follow-up email to a developer.
- Write 1-3 sentences only (very short)
- Casual, no-pressure tone
- Keep it simple and brief
- End with a simple sign-off
"""


class OpenAIService:
    """Service for generating email content with OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self._client = None
        self._api_key = api_key or settings.openai_api_key

    @property
    def client(self) -> Client:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = Client(api_key=self._api_key)
        return self._client

    def _generate_email(
        self,
        system_prompt: str,
        lead_info: Dict[str, Any],
        previous_email: str = "",
    ) -> Dict[str, Any]:
        """Generate email content using OpenAI.
        
        Args:
            system_prompt: System instructions for tone and style
            lead_info: Dict with 'name', 'email', 'github_url', etc.
            previous_email: Previous email content for follow-ups
            
        Returns:
            Dict with 'subject', 'body', 'success', 'error'
        """
        # Build user prompt with lead info
        user_prompt_parts = [
            f"Recipient name: {lead_info.get('name', '')}",
            f"Recipient GitHub: {lead_info.get('github_url', 'Not provided')}",
        ]

        if previous_email:
            user_prompt_parts.append(f"Previous email:\n{previous_email}")

        user_prompt = "\n".join(user_prompt_parts)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            
            # Parse subject and body from response
            lines = content.split("\n")
            subject = ""
            body = ""

            # Extract subject line if present
            for i, line in enumerate(lines):
                if line.strip().lower().startswith("subject:"):
                    subject = line.strip()[len("subject:"):].strip()
                    body = "\n".join(lines[i + 1:])
                    break
                elif line.strip().lower().startswith("subject "):
                    subject = line.strip()[len("subject :"):].strip()
                    body = "\n".join(lines[i + 1:])
                    break

            # If no subject line found, use first line as subject
            if not subject and lines:
                # Try to extract subject from first line
                first_line = lines[0].strip()
                if len(first_line) < 100 and not first_line.startswith("Hi"):
                    subject = first_line
                    body = "\n".join(lines[1:])
                else:
                    # No clear subject, use generic
                    subject = "Quick question"
                    body = content

            return {
                "subject": subject.strip(),
                "body": body.strip(),
                "success": True,
                "error": "",
            }

        except Exception as error:
            print(f"OpenAI generation error: {error}")
            return {
                "subject": "",
                "body": "",
                "success": False,
                "error": str(error),
            }

    def generate_initial_email(self, lead_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate initial outreach email."""
        return self._generate_email(
            system_prompt=INITIAL_EMAIL_GUIDELINES,
            lead_info=lead_info,
        )

    def generate_followup1(self, lead_info: Dict[str, Any], previous_email: str) -> Dict[str, Any]:
        """Generate first follow-up email."""
        return self._generate_email(
            system_prompt=FOLLOWUP1_GUIDELINES,
            lead_info=lead_info,
            previous_email=previous_email,
        )

    def generate_followup2(self, lead_info: Dict[str, Any], previous_email: str) -> Dict[str, Any]:
        """Generate second follow-up email."""
        return self._generate_email(
            system_prompt=FOLLOWUP2_GUIDELINES,
            lead_info=lead_info,
            previous_email=previous_email,
        )

    def generate_email_for_stage(
        self,
        stage: str,
        lead_info: Dict[str, Any],
        previous_email: str = "",
    ) -> Dict[str, Any]:
        """Generate email based on follow-up stage.
        
        Args:
            stage: 'initial', 'followup1', or 'followup2'
            lead_info: Lead information
            previous_email: Previous email content for follow-ups
        """
        if stage == "initial":
            return self.generate_initial_email(lead_info)
        elif stage == "followup1":
            return self.generate_followup1(lead_info, previous_email)
        elif stage == "followup2":
            return self.generate_followup2(lead_info, previous_email)
        else:
            return {
                "subject": "",
                "body": "",
                "success": False,
                "error": f"Unknown stage: {stage}",
            }


# Singleton instance
openai_service = OpenAIService()