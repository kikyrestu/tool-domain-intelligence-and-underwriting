"""FastAPI application factory."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.database import engine, Base
from app.services.scheduler_service import run_scheduler
from app.routes import dashboard, sources, crawl, candidates, export, logs, suggested_sources
from app.auth import BasicAuthMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables + auto-migrate new columns
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Auto-add new columns that may not exist on older DBs
        migrations = [
            "ALTER TABLE crawl_jobs ADD COLUMN IF NOT EXISTS current_step VARCHAR(20)",
            "ALTER TABLE candidate_domains ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT FALSE",
            "ALTER TABLE candidate_domains ADD COLUMN IF NOT EXISTS dns_mx_records BOOLEAN",
            "ALTER TABLE candidate_domains ADD COLUMN IF NOT EXISTS is_parked BOOLEAN DEFAULT FALSE",
            "ALTER TABLE candidate_domains ADD COLUMN IF NOT EXISTS toxicity_flags TEXT",
            "ALTER TABLE candidate_domains ADD COLUMN IF NOT EXISTS wayback_check_failed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE candidate_domains ADD COLUMN IF NOT EXISTS label_reason TEXT",
            "ALTER TABLE candidate_domains ADD COLUMN IF NOT EXISTS owner_notes TEXT",
        ]
        for sql in migrations:
            await conn.execute(text(sql))

        # Create new tables that may not exist yet
        from app.models.suggested_source import SuggestedSource  # noqa: F401 — ensure table registered
        await conn.run_sync(Base.metadata.create_all)

    # Start background scheduler (re-check starred domains)
    from app.config import get_settings
    settings = get_settings()
    scheduler_task = asyncio.create_task(
        run_scheduler(interval_hours=settings.STARRED_RECHECK_HOURS)
    )

    yield

    # Shutdown
    scheduler_task.cancel()
    await engine.dispose()


app = FastAPI(
    title="Domain Intelligence & Underwriting Engine",
    version="0.1.0",
    lifespan=lifespan,
)

# Auth middleware
app.add_middleware(BasicAuthMiddleware)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routes
app.include_router(dashboard.router)
app.include_router(suggested_sources.router)  # must be before sources (avoids /sources/{id} capturing /sources/suggested)
app.include_router(sources.router)
app.include_router(crawl.router)
app.include_router(candidates.router)
app.include_router(export.router)
app.include_router(logs.router)
