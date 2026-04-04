from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load `.env` from project root so RESEND_*, TWILIO_*, etc. apply even when cwd is not the repo root.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./genie.db"
    claude_model: str = "claude-haiku-4-5"
    # Max completion tokens per Anthropic call (lower = cheaper/shorter replies)
    claude_max_tokens: int = 2048
    # Tool outputs are stringified into the next user message; cap avoids huge prompts
    tool_result_max_chars: int = 10000
    # Project manager: max Claude API round-trips per /orchestrate (each round may include multiple tools)
    max_agent_iterations: int = 10
    # Each specialist spawned via delegate_to_agent: max API round-trips (matching needs ~6–8)
    max_specialist_iterations: int = 10
    # How many delegate_to_agent calls the PM may make in one orchestration (API/UI can override)
    max_delegate_calls: int = 4
    # Upper bounds for request body overrides (API cannot exceed these)
    orchestrate_max_rounds_cap: int = 15
    orchestrate_max_delegate_cap: int = 8
    log_level: str = "INFO"

    # Twilio — real SMS sending
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""  # e.g. "+15125550100" (omit if using messaging service)
    twilio_messaging_service_sid: str = ""

    # Resend — real email sending (REST API: Bearer RESEND_API_KEY)
    resend_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("RESEND_API_KEY", "RESEND_KEY"),
    )
    # Default matches Resend docs for testing without a verified domain
    resend_from_email: str = "onboarding@resend.dev"

    # Supabase — Auth (JWT) + browser client (anon key / URL exposed via /api/config)
    supabase_jwt_secret: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    # When true, API routes (except health/config) require a valid Supabase JWT; SPA gates on login + onboarding
    require_auth: bool = False
    # Comma-separated OAuth provider names for signInWithOAuth (google, github, azure, etc.)
    supabase_oauth_providers: str = "google,github"
    # Optional: email domain for Supabase SAML / enterprise SSO (signInWithSSO). Requires Supabase SSO on project.
    supabase_sso_domain: str = ""


settings = Settings()
# Force reload again
