// TypeScript types for the API

export interface GmailAccount {
  id: string;
  email: string;
  oauth_credentials: Record<string, unknown>;
  status: "active" | "paused";
  daily_sent_count: number;
  hourly_sent_count: number;
  last_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignState {
  id: string;
  is_running: boolean;
  is_paused: boolean;
  skip_today: boolean;
  last_run_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignStatus {
  is_running: boolean;
  is_paused: boolean;
  skip_today: boolean;
  last_run_date: string | null;
  today_emails_sent: number;
  active_accounts: number;
  paused_accounts: number;
}

export interface EmailLog {
  id: string;
  lead_email: string;
  account_id: string | null;
  type: "initial" | "followup1" | "followup2";
  status: "sent" | "failed" | "pending";
  openai_output: string;
  error_message: string;
  thread_id: string;
  message_id: string;
  timestamp: string;
}

export interface Lead {
  no: number;
  name: string;
  email: string;
  github_url: string;
  status: "pending" | "contacted" | "replied" | "bounced";
  last_contacted_at: string | null;
  followup_stage: "none" | "initial" | "followup1" | "followup2";
}

export interface OverviewStats {
  total_emails_today: number;
  active_accounts: number;
  paused_accounts: number;
  campaign_status: "running" | "paused" | "stopped";
  queue_size: number;
  pending_followups: number;
}

export interface LogStats {
  total_24h: number;
  sent_24h: number;
  failed_24h: number;
  by_type: Record<string, number>;
}