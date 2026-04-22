"""OpenAI service for email content generation."""

import json
import random
from typing import Any, Dict, Optional

from openai import Client

from app.core.config import get_settings

settings = get_settings()


def build_initial_email_prompt() -> str:
    """Build the initial email prompt with configurable sender info."""
    return f"""You are writing a personalized outreach email from {settings.sender_name}, founder of a {settings.sender_company} based in {settings.sender_location}.

EMAIL TEMPLATE STYLE TO FOLLOW:
<p>Hi <strong>{{firstName}}</strong>,</p>
<p>I hope you're doing well!</p>
<p>{settings.sender_intro}. Our team includes {settings.sender_eu_team}, along with {settings.sender_us_team}.<br> Our US team is mainly responsible for client communication, while all other tasks, like meetings and coding, are handled by our EU developers.<br> <strong>We're currently looking for a US-based professional who can work as {settings.sender_us_role} with us.</strong><br> After reviewing your GitHub profile({{github_url}}), I was really impressed with your background.<br> 
<br> The role would focus exclusively on {settings.sender_role_focus}, making use of your native English skills.<br>
<strong>Here's what we're looking for:</strong><br>
- US citizenship<br>
- Development experience.<br>
<br> If this sounds like an opportunity you'd be interested in, I'd love to chat and provide more details.<br>
Best regards,<br>
{settings.sender_name}.</p>

RULES:
- Write similar length to the template above (80-150 words)
- Follow the same structure: greeting, introduction, compliment based on GitHub, role description, requirements, call-to-action
- Professional but friendly, agency-founder tone
- Mention something specific from their GitHub profile
- End with "Best regards, {settings.sender_name}."
- NO all caps, NO excessive punctuation, NO spam words
- Avoid: "free", "guaranteed", "act now", "limited time", "exclusive deal"
"""


def build_followup1_prompt() -> str:
    """Build the first follow-up prompt with configurable sender info."""
    return f"""You are writing a follow-up email from {settings.sender_name}, founder of a {settings.sender_company} in {settings.sender_location}.

STYLE:
- Professional but friendly
- Softer, lower-pressure tone than initial
- Reference the previous email casually ("I wanted to follow up on my earlier email...")
- Keep it brief (40-80 words)
- Remind about the opportunity briefly
- End with "Best regards, {settings.sender_name}."
- NO pushy language
"""


def build_followup2_prompt() -> str:
    """Build the second follow-up prompt with configurable sender info."""
    return f"""You are writing a final follow-up email from {settings.sender_name}, founder of a {settings.sender_company} in {settings.sender_location}.

STYLE:
- Very short and casual (1-3 sentences)
- No-pressure tone
- Simple check-in
- End with "Best, {settings.sender_name.split()[0]}" or "Best regards, {settings.sender_name}."
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
            system_prompt=build_initial_email_prompt(),
            lead_info=lead_info,
        )

    def generate_followup1(self, lead_info: Dict[str, Any], previous_email: str) -> Dict[str, Any]:
        """Generate first follow-up email."""
        return self._generate_email(
            system_prompt=build_followup1_prompt(),
            lead_info=lead_info,
            previous_email=previous_email,
        )

    def generate_followup2(self, lead_info: Dict[str, Any], previous_email: str) -> Dict[str, Any]:
        """Generate second follow-up email."""
        return self._generate_email(
            system_prompt=build_followup2_prompt(),
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