"""Genie FastAPI application entrypoint."""
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from genie.auth import get_current_user
from genie.config import settings
from sqlalchemy import text

from genie.tools.communication_tools import twilio_sms_configured
from genie.db.database import AsyncSessionLocal
from genie.db.database import engine
from genie.db.database import init_db
from genie.db.seed import seed_database

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(
    title="Genie — Autonomous Subcontractor Manager",
    description="Multi-agent AI system for managing subcontractors end-to-end.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    if settings.require_auth and not settings.supabase_jwt_secret.strip():
        logging.getLogger(__name__).warning(
            "REQUIRE_AUTH is true but SUPABASE_JWT_SECRET is empty — API will return 503 for protected routes."
        )
    if settings.twilio_account_sid.strip() and settings.twilio_auth_token.strip() and not twilio_sms_configured():
        logging.getLogger(__name__).warning(
            "Twilio account credentials are set but TWILIO_FROM_NUMBER and TWILIO_MESSAGING_SERVICE_SID are both empty — SMS will stay simulated until you set one."
        )
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    logging.getLogger(__name__).info("Genie is ready.")


# Register routes
from genie.api.routes import jobs, orchestrate, schedule, subcontractors  # noqa: E402
from genie.api.routes import delays, leads, profile, quote, wishes, predict, stream  # noqa: E402


def _protected_dependencies():
    if settings.require_auth:
        return [Depends(get_current_user)]
    return []


_deps = _protected_dependencies()
app.include_router(jobs.router, dependencies=_deps)
app.include_router(subcontractors.router, dependencies=_deps)
app.include_router(schedule.router, dependencies=_deps)
app.include_router(orchestrate.router, dependencies=_deps)
app.include_router(delays.router, dependencies=_deps)
app.include_router(leads.router, dependencies=_deps)
app.include_router(quote.router, dependencies=_deps)
app.include_router(wishes.router, dependencies=_deps)
app.include_router(predict.router, dependencies=_deps)
app.include_router(stream.router, dependencies=_deps)
app.include_router(profile.router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "Genie Autonomous Subcontractor Manager"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}


@app.get("/health/integrations", tags=["health"])
async def health_integrations():
    """Non-secret flags + DB ping for Resend, Twilio, Supabase, and Anthropic."""
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    return {
        "database_reachable": db_ok,
        "database_url_uses_supabase_pooler": "supabase" in settings.database_url.lower(),
        "anthropic_configured": bool(settings.anthropic_api_key.strip()),
        "resend_configured": bool(settings.resend_api_key.strip()),
        "twilio_sms_ready": twilio_sms_configured(),
        "supabase_url_configured": bool(settings.supabase_url.strip()),
        "supabase_anon_key_configured": bool(settings.supabase_anon_key.strip()),
        "supabase_jwt_secret_configured": bool(settings.supabase_jwt_secret.strip()),
    }


def _oauth_provider_list() -> list[str]:
    raw = settings.supabase_oauth_providers.strip()
    if not raw:
        return ["google", "github"]
    out = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return out if out else ["google", "github"]


@app.get("/api/config", tags=["config"])
async def public_config():
    """Non-secret values for the browser Supabase client (anon key is public by design)."""
    return {
        "supabase_url": settings.supabase_url or None,
        "supabase_anon_key": settings.supabase_anon_key or None,
        "auth_required": settings.require_auth,
        "oauth_providers": _oauth_provider_list(),
        "sso_domain": settings.supabase_sso_domain.strip() or None,
        "sms_enabled": twilio_sms_configured(),
    }


@app.get("/api/me", tags=["auth"])
async def current_user_profile(user: dict = Depends(get_current_user)):
    return {"sub": user.get("sub"), "email": user.get("email"), "role": user.get("role")}


# Serve frontend SPA at /app
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
