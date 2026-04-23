"""Campaign worker engine - the heart of the outreach system."""

import json
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytz

from app.core.config import get_settings
from app.core.database import Database, db
from app.services.gmail import gmail_manager
from app.services.google_sheets import lead_manager
from app.services.openai import openai_service

settings = get_settings()


class CampaignWorker:
    """Worker engine that runs the email outreach campaign."""

    def __init__(self):
        self._running = False
        self._paused = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._consecutive_sends = 0
        self._last_reset_hourly = datetime.utcnow()
        self._last_reset_daily = datetime.utcnow()
        self._spreadsheet_id: str = ""
        self._current_account_index = 0
        self._shuffled_leads: List[Dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    @property
    def is_paused(self) -> bool:
        """Check if worker is paused."""
        return self._paused

    def start(self, spreadsheet_id: str) -> bool:
        """Start the campaign worker.
        
        Args:
            spreadsheet_id: Google Sheets ID for leads
            
        Returns:
            True if started successfully
        """
        if self._running:
            return False

        self._spreadsheet_id = spreadsheet_id
        self._running = True
        self._paused = False
        self._stop_event.clear()

        # Start worker thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        return True

    def stop(self) -> bool:
        """Stop the campaign worker."""
        if not self._running:
            return False

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=10)

        return True

    def pause(self) -> bool:
        """Pause the campaign (keeps running but doesn't send)."""
        if not self._running:
            return False
        self._paused = True
        return True

    def resume(self) -> bool:
        """Resume the campaign."""
        if not self._running:
            return False
        self._paused = False
        return True

    def _run_loop(self) -> None:
        """Main worker loop."""
        # Reset counters periodically
        self._reset_counters_if_needed()

        while self._running and not self._stop_event.is_set():
            try:
                # Check campaign state
                campaign_state = db.get_campaign_state()

                # Exit if campaign stopped
                if not campaign_state.get("is_running", False):
                    break

                # Check pause state
                if campaign_state.get("is_paused", False):
                    self._paused = True
                else:
                    self._paused = False

                # Skip if paused
                if self._paused:
                    time.sleep(10)
                    continue

                # Check EST time window
                if not self._is_within_send_window():
                    print("Outside EST send window (9AM-5PM), sleeping...")
                    time.sleep(60)
                    continue

                # Check skip today
                if campaign_state.get("skip_today", False):
                    print("Skip today is set, waiting...")
                    time.sleep(60)
                    continue

                # Process leads
                self._process_leads()

            except Exception as e:
                print(f"Worker loop error: {e}")
                time.sleep(30)

        self._running = False

    def _reset_counters_if_needed(self) -> None:
        """Reset hourly/daily counters at appropriate times."""
        now = datetime.utcnow()
        est = pytz.timezone(settings.est_timezone)
        now_est = now.astimezone(est)

        # Reset hourly at start of each hour
        if now_est.hour != self._last_reset_hourly.astimezone(est).hour:
            db.reset_hourly_counts()
            self._last_reset_hourly = now
            print("Reset hourly counts")

        # Reset daily at midnight EST
        if now_est.hour == 0 and self._last_reset_daily.astimezone(est).hour != 0:
            db.reset_daily_counts()
            self._last_reset_daily = now
            print("Reset daily counts")

    def _is_within_send_window(self) -> bool:
        """Check if current time is within EST send window (9AM-5PM)."""
        est = pytz.timezone(settings.est_timezone)
        now_est = datetime.now(est)
        current_hour = now_est.hour

        # Check weekday
        if settings.skip_weekends and now_est.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Check hours
        return settings.send_window_start <= current_hour < settings.send_window_end

    def _process_leads(self) -> None:
        """Process leads and send emails."""
        # Shuffle leads if needed
        if not self._shuffled_leads:
            self._shuffle_leads()

        # Process one lead at a time
        for lead in self._shuffled_leads[:]:
            if not self._running or self._paused:
                break

            # Determine email type
            email_type = self._determine_email_type(lead)
            if not email_type:
                continue

            # Get available account
            account = self._get_available_account()
            if not account:
                print("No available accounts, waiting...")
                time.sleep(60)
                continue

            # Check follow-up timing
            if email_type != "initial":
                if not self._should_send_followup(lead, email_type):
                    continue

            # Send the email
            success = self._send_email(lead, account, email_type)
            
            if success:
                # Remove from queue
                self._shuffled_leads.remove(lead)
                
                # Update lead in sheet
                lead_manager.set_spreadsheet_id(self._spreadsheet_id)
                if email_type == "initial":
                    lead_manager.mark_initial_sent(self._spreadsheet_id, lead.get("email", ""))
                elif email_type == "followup1":
                    lead_manager.mark_followup1_sent(self._spreadsheet_id, lead.get("email", ""))
                elif email_type == "followup2":
                    lead_manager.mark_followup2_sent(self._spreadsheet_id, lead.get("email", ""))

            # Apply delay
            self._apply_delay()

    def _shuffle_leads(self) -> None:
        """Shuffle leads for random ordering."""
        pending = lead_manager.get_pending_leads(self._spreadsheet_id)
        followup1 = lead_manager.get_leads_for_followup(
            self._spreadsheet_id, "initial", settings.followup1_days
        )
        followup2 = lead_manager.get_leads_for_followup(
            self._spreadsheet_id, "followup1", settings.followup2_days
        )

        # Combine and shuffle
        all_leads = pending + followup1 + followup2
        random.shuffle(all_leads)
        
        self._shuffled_leads = all_leads

    def _determine_email_type(self, lead: Dict[str, Any]) -> Optional[str]:
        """Determine which type of email to send.
        
        Args:
            lead: Lead dictionary
            
        Returns:
            'initial', 'followup1', 'followup2', or None
        """
        followup_stage = lead.get("followup_stage", "none")
        
        if followup_stage == "none":
            return "initial"
        elif followup_stage == "initial":
            return "followup1"
        elif followup_stage == "followup1":
            return "followup2"
        
        return None

    def _get_available_account(self) -> Optional[Dict[str, Any]]:
        """Get an available Gmail account.
        
        Returns:
            Account dict or None
        """
        accounts = db.get_active_gmail_accounts()
        
        if not accounts:
            return None

        # Filter by limits
        available = [
            a for a in accounts
            if a.get("daily_sent_count", 0) < settings.max_emails_per_day
            and a.get("hourly_sent_count", 0) < settings.max_emails_per_hour
        ]

        if not available:
            return None

        # Round-robin selection
        account = available[self._current_account_index % len(available)]
        self._current_account_index += 1

        return account

    def _should_send_followup(
        self,
        lead: Dict[str, Any],
        email_type: str,
    ) -> bool:
        """Check if enough time has passed for follow-up.
        
        Args:
            lead: Lead dictionary
            email_type: 'followup1' or 'followup2'
            
        Returns:
            True if follow-up should be sent
        """
        last_contacted = lead.get("last_contacted_at", "")
        
        if not last_contacted:
            return False

        try:
            contact_date = datetime.fromisoformat(last_contacted.replace("Z", "+00:00"))
            days_since = (datetime.now() - contact_date).days

            if email_type == "followup1":
                return days_since >= settings.followup1_days
            elif email_type == "followup2":
                return days_since >= settings.followup2_days

        except (ValueError, TypeError):
            pass

        return False

    def _send_email(
        self,
        lead: Dict[str, Any],
        account: Dict[str, Any],
        email_type: str,
    ) -> bool:
        """Send an email to a lead.
        
        Args:
            lead: Lead dictionary
            account: Gmail account dictionary
            email_type: Type of email
            
        Returns:
            True if sent successfully
        """
        lead_email = lead.get("email", "")
        lead_name = lead.get("name", "")
        github_url = lead.get("github_url", "")

        if not lead_email:
            print(f"Skipping lead with no email: {lead}")
            return False

        lead_info = {
            "name": lead_name,
            "email": lead_email,
            "github_url": github_url,
        }

        # Get previous email for follow-ups
        previous_email = ""
        thread_id = ""
        message_id = ""

        if email_type != "initial":
            last_log = db.get_last_email_to_lead(lead_email)
            if last_log:
                previous_email = last_log.get("openai_output", "")
                thread_id = last_log.get("thread_id", "")
                message_id = last_log.get("message_id", "")

        # Generate content
        result = openai_service.generate_email_for_stage(
            stage=email_type,
            lead_info=lead_info,
            previous_email=previous_email,
        )

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            db.add_email_log(
                lead_email=lead_email,
                account_id=account.get("id", ""),
                log_type=email_type,
                status="failed",
                error_message=error,
            )
            return False

        subject = result.get("subject", "")
        body = result.get("body", "")
        openai_output = f"Subject: {subject}\n\n{body}"

        # Send via Gmail
        oauth_creds = json.loads(account.get("oauth_credentials", "{}"))
        send_result = gmail_manager.send_with_thread(
            account_id=str(account.get("id", "")),
            email=lead_email,
            oauth=oauth_creds,
            sender=account.get("email", ""),
            subject=subject,
            body=body,
            thread_id=thread_id,
            message_id=message_id,
        )

        if send_result.get("success"):
            # Update account count
            db.increment_sent_count(str(account.get("id", "")))
            
            # Log success
            db.add_email_log(
                lead_email=lead_email,
                account_id=str(account.get("id", "")),
                log_type=email_type,
                status="sent",
                openai_output=openai_output,
                thread_id=send_result.get("thread_id", ""),
                message_id=send_result.get("message_id", ""),
            )
            
            self._consecutive_sends += 1
            return True
        else:
            # Log failure
            error = send_result.get("error", "Send failed")
            db.add_email_log(
                lead_email=lead_email,
                account_id=str(account.get("id", "")),
                log_type=email_type,
                status="failed",
                openai_output=openai_output,
                error_message=error,
            )
            return False

    def _apply_delay(self) -> None:
        """Apply human-like delay between sends."""
        base_delay = settings.min_delay_between_emails
        random_addition = random.randint(0, settings.random_delay_range)
        total_delay = base_delay + random_addition

        # Occasional longer pause
        if self._consecutive_sends >= settings.occasional_pause_after_emails:
            total_delay += settings.occasional_pause_duration
            self._consecutive_sends = 0

        # Sleep in smaller chunks to allow quick exit
        for _ in range(total_delay // 10):
            if not self._running or self._paused:
                break
            time.sleep(10)
        
        remaining = total_delay % 10
        if remaining > 0 and self._running and not self._paused:
            time.sleep(remaining)


# Singleton instance
worker = CampaignWorker()