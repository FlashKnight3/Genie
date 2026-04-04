from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./genie.db"
    claude_model: str = "claude-sonnet-4-6"
    # Max completion tokens per Anthropic call (lower = cheaper/shorter replies)
    claude_max_tokens: int = 2048
    # Tool outputs are stringified into the next user message; cap avoids huge prompts
    tool_result_max_chars: int = 10000
    # Project manager: max Claude API round-trips per /orchestrate (each round may include multiple tools)
    max_agent_iterations: int = 4
    # Each specialist spawned via delegate_to_agent: max API round-trips
    max_specialist_iterations: int = 3
    # How many delegate_to_agent calls the PM may make in one orchestration (API/UI can override)
    max_delegate_calls: int = 2
    # Upper bounds for request body overrides (API cannot exceed these)
    orchestrate_max_rounds_cap: int = 15
    orchestrate_max_delegate_cap: int = 8
    log_level: str = "INFO"

    # Twilio — real SMS sending
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""  # e.g. "+15125550100"

    # Resend — real email sending
    resend_api_key: str = ""
    resend_from_email: str = "genie@updates.yourdomain.com"

    # Supabase — Auth (JWT) + browser client (anon key / URL exposed via /api/config)
    supabase_jwt_secret: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""


settings = Settings()
