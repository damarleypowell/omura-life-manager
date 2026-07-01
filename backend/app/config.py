"""
Omura Configuration
All API keys, database URLs, and OAuth configs.
Loaded from environment variables for security — never hardcode secrets.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional

# Resolve .env path relative to this file so it works regardless of cwd
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")


class Settings(BaseSettings):
    # ── App ──
    APP_NAME: str = "Omura Life Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ENCRYPTION_KEY: str = "CHANGE-ME-32-BYTE-KEY-HERE-1234"  # AES-256 key (32 bytes)

    # ── Database ──
    DATABASE_URL: str = "postgresql://omura:omura@localhost:5432/omura"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── OAuth 2.0 Credentials ──
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "https://omura-life-manager-production.up.railway.app/auth/google/callback"

    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None

    INSTAGRAM_APP_ID: Optional[str] = None
    INSTAGRAM_APP_SECRET: Optional[str] = None

    TIKTOK_CLIENT_KEY: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None

    YOUTUBE_API_KEY: Optional[str] = None

    # ── AI Provider Keys (Claude only — Gemini removed) ──
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    # Optional model overrides (swap to a local OpenAI-compatible server later).
    OMURA_SUPERVISOR_MODEL: str = "claude-sonnet-4-6"
    OMURA_WORKER_MODEL: str = "claude-haiku-4-5-20251001"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── External Services ──
    TODOIST_API_KEY: Optional[str] = None
    NOTION_API_KEY: Optional[str] = None
    QUICKBOOKS_CLIENT_ID: Optional[str] = None
    QUICKBOOKS_CLIENT_SECRET: Optional[str] = None

    # ── Apollo.io ──
    APOLLO_API_KEY: Optional[str] = None

    # ── Hunter.io (email finder) ──
    HUNTER_API_KEY: Optional[str] = None

    # ── Google Drive ──
    GDRIVE_FOLDER_ID: Optional[str] = None  # Root folder ID for Omura in Drive

    # ── Scheduling ──
    SCHEDULER_ENABLED: bool = True

    # ── Auth ──
    JWT_SECRET: str = "change-me-in-production"

    # ── Email (Resend primary; Gmail API/SMTP fallback) ──
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM: Optional[str] = None  # must be a Resend-verified sender/domain
    SENDGRID_API_KEY: Optional[str] = None
    DEFAULT_FROM_EMAIL: str = "noreply@omura.app"
    GMAIL_USER: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None

    # ── Google Maps ──
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unknown .env fields


settings = Settings()
