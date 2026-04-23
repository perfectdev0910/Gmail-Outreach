"""FastAPI main application."""

import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts, campaign, leads, logs
from app.core.config import get_settings
from app.core.database import Database, db
from app.services.gmail import gmail_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("=" * 50)
    print("Starting Gmail Outreach API...")
    
    try:
        # Connect to database
        db.connect()
        print("✓ Database connected")
        
        # Load Gmail accounts into manager
        accounts_list = db.get_gmail_accounts()
        
        for account in accounts_list:
            account_id = str(account.get("id", ""))
            email = account.get("email", "")
            oauth_creds = account.get("oauth_credentials", {})
            
            if isinstance(oauth_creds, str):
                import json
                oauth_creds = json.loads(oauth_creds)
            
            gmail_manager.add_account(account_id, email, oauth_creds)
        
        print(f"✓ Loaded {len(accounts_list)} Gmail accounts")
        
    except Exception as e:
        print(f"✗ Startup error: {e}")
        print(traceback.format_exc())
    
    print("=" * 50)
    
    yield
    
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Gmail Outreach API",
    description="Production-grade email outreach automation system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(campaign.router)
app.include_router(accounts.router)
app.include_router(logs.router)
app.include_router(leads.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Gmail Outreach API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    try:
        # Test database connection
        state = db.get_campaign_state()
        return {
            "status": "healthy",
            "database": "connected",
            "campaign": {
                "is_running": state.get("is_running", False),
                "is_paused": state.get("is_paused", False),
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)