"""Crawl routes — trigger crawl, RDAP, Wayback, Score."""

import logging
import os
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.models.crawl_job import CrawlJob
from app.models.candidate import CandidateDomain
from app.services.crawl_service import run_crawl
from app.services.whois_service import check_candidates as whois_check
from app.services.wayback_service import check_candidates as wayback_check
from app.services.toxicity_service import scan_candidate
from app.services.scoring_service import score_candidates

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Pipeline file logger — writes to logs/pipeline.log
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")

_pipeline_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_pipeline_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
for _mod in ("app.services.crawl_service", "app.services.whois_service",
             "app.services.wayback_service", "app.services.scoring_service",
             "app.routes.crawl"):
    _log = logging.getLogger(_mod)
    _log.addHandler(_pipeline_handler)
    _log.setLevel(logging.INFO)


async def _background_crawl(source_id: int):
    """Run full pipeline in background: crawl → WHOIS → Wayback → Score."""
    async with async_session() as db:
        await run_crawl(source_id, db)

    logger.info("Crawl done for source %d, starting RDAP check…", source_id)
    async with async_session() as db:
        await whois_check(db, source_id=source_id)

    logger.info("RDAP done for source %d, starting Wayback check…", source_id)
    async with async_session() as db:
        await wayback_check(db, source_id=source_id)

    logger.info("Wayback done for source %d, starting scoring…", source_id)
    async with async_session() as db:
        query = select(CandidateDomain)
        query = query.where(CandidateDomain.source_id == source_id)
        result = await db.execute(query)
        candidates = result.scalars().all()

        toxicity_map: dict[int, list[dict]] = {}
        for c in candidates:
            flags = scan_candidate(c, [])
            toxicity_map[c.id] = flags

        await score_candidates(db, source_id=source_id, toxicity_map=toxicity_map)

    logger.info("Full pipeline complete for source %d ✓", source_id)


async def _background_whois(source_id: int | None = None):
    """Run RDAP batch check in background."""
    async with async_session() as db:
        await whois_check(db, source_id=source_id)


async def _background_wayback(source_id: int | None = None):
    """Run Wayback batch check in background."""
    async with async_session() as db:
        await wayback_check(db, source_id=source_id)


async def _background_score(source_id: int | None = None):
    """Run scoring pipeline: toxicity scan → score calculation."""
    async with async_session() as db:
        # Collect toxicity flags per candidate
        query = select(CandidateDomain)
        if source_id:
            query = query.where(CandidateDomain.source_id == source_id)
        result = await db.execute(query)
        candidates = result.scalars().all()

        toxicity_map: dict[int, list[dict]] = {}
        for c in candidates:
            flags = scan_candidate(c, [])  # Text flags already processed during Wayback
            toxicity_map[c.id] = flags

        await score_candidates(db, source_id=source_id, toxicity_map=toxicity_map)


@router.post("/crawl/{source_id}")
async def trigger_crawl(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    background_tasks.add_task(_background_crawl, source_id)
    return RedirectResponse(url=f"/sources/{source_id}", status_code=303)


@router.post("/whois/{source_id}")
async def trigger_whois(
    source_id: int,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(_background_whois, source_id)
    return RedirectResponse(url=f"/sources/{source_id}", status_code=303)


@router.post("/whois-all")
async def trigger_whois_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(_background_whois, None)
    return RedirectResponse(url="/candidates", status_code=303)


@router.post("/wayback/{source_id}")
async def trigger_wayback(
    source_id: int,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(_background_wayback, source_id)
    return RedirectResponse(url=f"/sources/{source_id}", status_code=303)


@router.post("/wayback-all")
async def trigger_wayback_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(_background_wayback, None)
    return RedirectResponse(url="/candidates", status_code=303)


@router.post("/score/{source_id}")
async def trigger_score(
    source_id: int,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(_background_score, source_id)
    return RedirectResponse(url=f"/sources/{source_id}", status_code=303)


@router.post("/score-all")
async def trigger_score_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(_background_score, None)
    return RedirectResponse(url="/candidates", status_code=303)


@router.get("/crawl/status/{job_id}")
async def crawl_status(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(CrawlJob, job_id)
    if not job:
        return {"status": "not_found"}
    return templates.TemplateResponse("partials/crawl_status.html", {
        "request": request,
        "job": job,
    })
