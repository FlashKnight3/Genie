"""Genie FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from genie.config import settings
from genie.db.database import init_db
from genie.db.seed import seed_database
from genie.db.database import AsyncSessionLocal

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
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    logging.getLogger(__name__).info("Genie is ready.")


# Register routes
from genie.api.routes import jobs, orchestrate, schedule, subcontractors  # noqa: E402

app.include_router(jobs.router)
app.include_router(subcontractors.router)
app.include_router(schedule.router)
app.include_router(orchestrate.router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "Genie Autonomous Subcontractor Manager"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
