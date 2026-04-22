# Gmail Outreach Automation System

A production-grade email outreach automation system designed for safe, low-volume Gmail deliverability.

## Features

- **Multi-Account Gmail Sending** — Manage multiple Gmail accounts with OAuth2
- **Threaded Follow-ups** — Emails stay in the same thread using proper Gmail headers
- **OpenAI Personalization** — AI-generated personalized outreach emails
- **Google Sheets Integration** — Leads synced from Google Sheets only
- **Campaign Controls** — Start, pause, resume, stop from dashboard
- **Rate Limiting** — Built-in protection (12/day, 3/hour per account)
- **EST Timing** — Sends only between 9AM-5PM EST
- **Human Simulation** — Random delays to avoid spam patterns

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Vercel    │────▶│   Render   │────▶│ Supabase   │
│  Dashboard │     │   FastAPI  │     │ PostgreSQL │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────┐
              │  Gmail   │  │ Google   │
              │   API    │  │ Sheets   │
              └──────────┘  └──────────┘
```

## Quick Start

### 1. Prerequisites

- Node.js 18+
- Python 3.11+
- Supabase account
- Google Cloud account (for Gmail & Sheets APIs)
- OpenAI account

### 2. Database Setup

Run the SQL schema in Supabase SQL Editor:

```bash
# Go to Supabase Dashboard > SQL Editor > paste contents of backend/database/schema.sql
```

### 3. Backend Setup

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Frontend Setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Documentation

- [Deployment Guide](./deploy.md)
- [API Reference](./docs/api.md)
- [Google Sheets Setup](./docs/sheets.md)

## Safety Rules

| Rule | Limit |
|------|-------|
| Daily emails/account | 12 |
| Hourly emails/account | 3 |
| Send window | 9AM-5PM EST |
| Delay between emails | 10-15 min |

## License

MIT
