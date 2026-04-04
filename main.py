"""Genie FastAPI application entrypoint."""
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from genie.auth import get_current_user
from genie.config import settings
from genie.db.database import AsyncSessionLocal
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
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    logging.getLogger(__name__).info("Genie is ready.")


# Register routes
from genie.api.routes import jobs, orchestrate, schedule, subcontractors  # noqa: E402
from genie.api.routes import delays, leads, profile, quote  # noqa: E402


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
app.include_router(profile.router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "Genie Autonomous Subcontractor Manager"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}


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
    }


@app.get("/api/me", tags=["auth"])
async def current_user_profile(user: dict = Depends(get_current_user)):
    return {"sub": user.get("sub"), "email": user.get("email"), "role": user.get("role")}


# Serve frontend SPA at /app
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
