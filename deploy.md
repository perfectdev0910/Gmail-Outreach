# Deployment Guide

Step-by-step guide to deploy the Gmail Outreach Automation System to production.

## Overview

**No Google Cloud billing required!**

- **Google Sheets**: Uses a service account (free quota for reading)
- **Gmail sending**: Uses OAuth tokens from individual accounts (no client app needed)

| Service | Platform | Purpose |
|---------|----------|--------|
| Backend | Render | FastAPI server + worker |
| Frontend | Vercel | Next.js dashboard |
| Database | Supabase | PostgreSQL storage |
| Leads | Google Sheets | Your existing sheet |
| Sending | Gmail accounts | Your sending accounts |

## Step 1: Supabase Setup

### 1.1 Create Project

1. Go to [supabase.com](https://supabase.com)
2. Click "New Project"
3. Choose your organization
4. Set project name (e.g., `gmail-outreach`)
5. Select region closest to you
6. Set a strong database password
7. Wait for project to provision (~2 minutes)

### 1.2 Get Credentials

From project Settings > API:
- **Project URL**: `https://xxxxx.supabase.co`
- **Service role key**: `eyJhbGc...` (keep this secret!)

### 1.3 Run Database Schema

1. Go to **SQL Editor** in Supabase dashboard
2. Copy and paste the contents of `backend/database/schema.sql`
3. Click **Run**

## Step 2: Get Gmail OAuth Tokens

Each Gmail sending account needs OAuth tokens. No Google Cloud project needed.

### 2.1 Open OAuth Consent Page

1. Go to your Gmail account
2. Visit: `https://accounts.google.com/o/oauth2/v2/auth?client_id=&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/gmail.send&access_type=offline&prompt=consent`

### 2.2 Get Authorization Code

1. Sign in with your Gmail account
2. Click "Allow" to grant access
3. Copy the **authorization code** shown on the page

### 2.3 Exchange for Tokens

You'll need to exchange the code manually. Create a simple script:

```python
import requests

auth_code = "YOUR_AUTH_CODE_HERE"

response = requests.post(
    "https://oauth2.googleapis.com/token",
    data={
        "code": auth_code,
        "client_id": "",  # Leave empty for installed apps
        "client_secret": "",  # Leave empty for installed apps
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "authorization_code",
    }
)

tokens = response.json()
print(f"access_token: {tokens['access_token']}")
print(f"refresh_token: {tokens['refresh_token']}")
```

Or use curl:

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d "code=YOUR_AUTH_CODE&client_id=&client_secret=&redirect_uri=urn:ietf:wg:oauth:2.0:oob&grant_type=authorization_code"
```

### 2.4 Save Tokens

Save each account's tokens securely. You'll add them to the system later.

**One account = one set of tokens. Repeat for each sending account.**

## Step 3: OpenAI Setup

### 3.1 Get API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Go to **API Keys** > **Create new secret key**
3. Name it `gmail-outreach`
4. Copy the key (starts with `sk-`)
5. Set up billing (pay-as-you-go)

## Step 4: Backend Deployment (Render)

### 4.1 Connect Repository

1. Go to [render.com](https://render.com)
2. Click "New +" > **Web Service**
3. Connect your GitHub repository
4. Select `Gmail-Outreach` > `backend` folder

### 4.2 Configure Service

- **Region**: Choose closest to users
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Plan**: Free tier works for testing

### 4.3 Add Environment Variables

In Render dashboard, add these:

| Variable | Value |
|----------|-------|
| `SUPABASE_URL` | From Supabase (Project Settings > API) |
| `SUPABASE_KEY` | Service role key from Supabase |
| `OPENAI_API_KEY` | `sk-...` from OpenAI |
| `EST_TIMEZONE` | `America/New_York` |
| `SEND_WINDOW_START` | `9` |
| `SEND_WINDOW_END` | `17` |
| `SKIP_WEEKENDS` | `true` |
| `MAX_EMAILS_PER_DAY` | `12` |
| `MAX_EMAILS_PER_HOUR` | `3` |

### 4.4 Deploy

1. Click "Create Web Service"
2. Wait for build (~3 minutes)
3. Note your URL: `https://xxx.onrender.com`

## Step 5: Frontend Deployment (Vercel)

### 5.1 Connect Repository

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New..." > **Project**
3. Import `Gmail-Outreach` from GitHub
4. Framework: **Next.js** (auto-detected)

### 5.2 Configure Project

- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `/.next`

### 5.3 Add Environment Variable

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | Your Render backend URL |

### 5.4 Deploy

1. Click "Deploy"
2. Wait for deployment (~2 minutes)

## Step 6: Configure Google Sheets (Your Existing Sheet)

### 6.1 Create Service Account (Free - No Billing)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. **DO NOT enable billing** - service accounts work without it
3. Click "Select a project" > "New Project"
4. Name it `gmail-sheets-access`
5. Click "APIs & Services" > "Library"
6. Enable **Google Sheets API** (free tier)

### 6.2 Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Name it `sheet-reader`
4. Click "Create" > "Done"

### 6.3 Download Service Account JSON

1. Click on your new service account
2. Click "Keys" tab
3. "Add Key" > "JSON" (will download file)
4. Rename to `service-account.json`

### 6.4 Share Your Google Sheet

1. Open your Google Sheet
2. Click "Share"
3. Add the service account email (from JSON file: `client_email`)
4. Give "Viewer" access (read-only is fine)
5. Click "Send"

### 6.5 Upload Service Account JSON

Add the JSON file to your backend:
- Local development: save as `backend/service-account.json`
- Render: add as environment variable `SERVICE_ACCOUNT_JSON` with full JSON content

### 6.6 Sheet Structure

Your sheet should have these columns in row 1:
```
A: No | B: name | C: email | D: github_url | E: status | F: last_contacted_at | G: followup_stage
```

Add leads starting row 2:
- Column A: Number (1, 2, 3...)
- Column B: Lead name
- Column C: Lead email
- Column D: GitHub URL (optional)
- Column E: `pending`
- Column F: (empty)
- Column G: `none`

## Step 7: Add Gmail Sending Accounts

### 7.1 Add First Account

Using the tokens from Step 2:

```bash
curl -X POST https://xxx.onrender.com/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "email": "sender@gmail.com",
    "access_token": "ya29...",
    "refresh_token": "1//..."
  }'
```

### 7.2 Add More Accounts

Repeat for each Gmail account you want to use.

## Step 8: Start Campaign

### 8.1 Get Spreadsheet ID

From your Google Sheet URL:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

### 8.2 Start via API

```bash
curl -X POST https://xxx.onrender.com/campaign/start \
  -H "Content-Type: application/json" \
  -d '{"spreadsheet_id": "YOUR_SPREADSHEET_ID"}'
```

### 8.3 Start via Dashboard

1. Visit your Vercel dashboard URL
2. Enter Spreadsheet ID
3. Click "Start Campaign"

## Verification

### Check Status

```bash
curl https://xxx.onrender.com/campaign/status
```

### View Logs

```bash
curl https://xxx.onrender.com/logs/recent?hours=24
```

### Dashboard

Visit your Vercel URL to see:
- Campaign status
- Email logs
- Account stats

## Troubleshooting

### Backend Won't Start

1. Check Render logs for errors
2. Verify environment variables set correctly
3. Verify Supabase service role key valid

### Google Sheets Not Syncing

1. Verify service account email has access to sheet
2. Check `service-account.json` is valid
3. Verify spreadsheet ID correct

### Emails Not Sending

1. Verify EST time (9AM-5PM)
2. Check account limits haven't exceeded
3. Verify Gmail refresh tokens valid
4. Check `/logs` for errors

### OpenAI Errors

1. Verify API key starts with `sk-`
2. Check billing set up on OpenAI

## Production Checklist

- [ ] Supabase project created
- [ ] Database schema applied
- [ ] Gmail accounts added with OAuth tokens
- [ ] Google Sheet configured with service account access
- [ ] Campaign starts successfully
- [ ] Dashboard accessible
- [ ] Test email sends successfully

## Quick Reference

### Required Services (All Free Tier)

| Service | Cost | Purpose |
|---------|------|--------|
| Render | Free | Backend hosting |
| Vercel | Free | Frontend hosting |
| Supabase | Free tier | Database |
| Google Sheets API | **Free** | Reading leads |
| Gmail | **Free** | Sending emails |
| OpenAI | Pay-as-you-go | Email generation |

### No Billing Required For

- Google Cloud (service account for Sheets reading only)
- Gmail sending (individual account permissions)
- Sheets API (free quota for read operations)