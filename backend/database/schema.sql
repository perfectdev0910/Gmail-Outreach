-- Gmail Outreach Automation System - Database Schema
-- Run this SQL in Supabase SQL Editor to create all required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Gmail Accounts Table
CREATE TABLE IF NOT EXISTS gmail_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    oauth_credentials JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
    daily_sent_count INTEGER NOT NULL DEFAULT 0,
    hourly_sent_count INTEGER NOT NULL DEFAULT 0,
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Campaign State Table (singleton)
CREATE TABLE IF NOT EXISTS campaign_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_running BOOLEAN NOT NULL DEFAULT FALSE,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    skip_today BOOLEAN NOT NULL DEFAULT FALSE,
    last_run_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Email Logs Table
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_email TEXT NOT NULL,
    account_id UUID REFERENCES gmail_accounts(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('initial', 'followup1', 'followup2')),
    status TEXT NOT NULL CHECK (status IN ('sent', 'failed', 'pending')),
    openai_output TEXT,
    error_message TEXT,
    thread_id TEXT,
    message_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_email_logs_lead_email ON email_logs(lead_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_account_id ON email_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_timestamp ON email_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);
CREATE INDEX IF NOT EXISTS idx_gmail_accounts_status ON gmail_accounts(status);

-- Insert default campaign state if not exists
INSERT INTO campaign_state (is_running, is_paused, skip_today)
SELECT false, false, false
WHERE NOT EXISTS (SELECT 1 FROM campaign_state LIMIT 1);

-- Row Level Security (RLS) - Optional, enable if needed
-- ALTER TABLE gmail_accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE campaign_state ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (adjust as needed for your security requirements)
-- CREATE POLICY "Service role can do everything" ON gmail_accounts FOR ALL USING (true) WITH CHECK (true);
-- CREATE POLICY "Service role can do everything" ON campaign_state FOR ALL USING (true) WITH CHECK (true);
-- CREATE POLICY "Service role can do everything" ON email_logs FOR ALL USING (true) WITH CHECK (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_gmail_accounts_updated_at ON gmail_accounts;
CREATE TRIGGER update_gmail_accounts_updated_at
    BEFORE UPDATE ON gmail_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_campaign_state_updated_at ON campaign_state;
CREATE TRIGGER update_campaign_state_updated_at
    BEFORE UPDATE ON campaign_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
