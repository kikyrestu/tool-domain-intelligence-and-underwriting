"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.routes import dashboard, sources, crawl, candidates, export, logs
from app.auth import BasicAuthMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables (dev only — use Alembic in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
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
app.include_router(sources.router)
app.include_router(crawl.router)
app.include_router(candidates.router)
app.include_router(export.router)
app.include_router(logs.router)
