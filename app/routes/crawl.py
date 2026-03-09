"""Crawl routes — trigger crawl, WHOIS, Wayback, Score."""

import logging
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


async def _background_crawl(source_id: int):
    """Run crawl in background with its own DB session."""
    async with async_session() as db:
        await run_crawl(source_id, db)


async def _background_whois(source_id: int | None = None):
    """Run WHOIS batch check in background."""
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
