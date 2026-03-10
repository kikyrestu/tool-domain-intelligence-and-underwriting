"""Source routes — add, list, detail."""

import asyncio
from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.source import Source
from app.models.crawl_job import CrawlJob
from app.models.candidate import CandidateDomain
from app.schemas.source import SourceCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

NICHES = [
    "General",
    "Technology", "Finance", "Health", "Education", "Travel",
    "Gaming", "News", "Entertainment", "Business", "Science",
    "Sports", "Lifestyle", "Food", "Real Estate", "Crypto",
    "Marketing", "Other",
]


@router.get("/sources")
async def list_sources(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Source).order_by(Source.created_at.desc())
    )
    sources = result.scalars().all()

    # Get last crawl job per source
    source_stats = {}
    for source in sources:
        job_result = await db.execute(
            select(CrawlJob)
            .where(CrawlJob.source_id == source.id)
            .order_by(CrawlJob.created_at.desc())
            .limit(1)
        )
        last_job = job_result.scalar_one_or_none()

        count_result = await db.execute(
            select(func.count()).where(CandidateDomain.source_id == source.id)
        )
        candidate_count = count_result.scalar()

        source_stats[source.id] = {
            "last_job": last_job,
            "candidate_count": candidate_count,
        }

    return templates.TemplateResponse("sources/list.html", {
        "request": request,
        "sources": sources,
        "stats": source_stats,
        "niches": NICHES,
    })


@router.get("/sources/add")
async def add_source_form(request: Request):
    return templates.TemplateResponse("sources/add.html", {
        "request": request,
        "niches": NICHES,
    })


@router.post("/sources")
async def create_source(
    request: Request,
    url: str = Form(...),
    niche: str = Form("General"),
    notes: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate
    existing = await db.execute(select(Source).where(Source.url == url))
    if existing.scalar_one_or_none():
        return templates.TemplateResponse("sources/add.html", {
            "request": request,
            "niches": NICHES,
            "error": "Source URL sudah ada.",
            "url": url,
            "niche": niche,
        })

    source = Source(url=url, niche=niche, notes=notes or None)
    db.add(source)
    await db.commit()
    return RedirectResponse(url="/sources", status_code=303)


@router.get("/sources/{source_id}")
async def source_detail(request: Request, source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        return RedirectResponse(url="/sources", status_code=303)

    jobs_result = await db.execute(
        select(CrawlJob)
        .where(CrawlJob.source_id == source_id)
        .order_by(CrawlJob.created_at.desc())
    )
    jobs = jobs_result.scalars().all()

    candidates_result = await db.execute(
        select(CandidateDomain)
        .where(CandidateDomain.source_id == source_id)
        .order_by(CandidateDomain.created_at.desc())
    )
    candidates = candidates_result.scalars().all()

    return templates.TemplateResponse("sources/detail.html", {
        "request": request,
        "source": source,
        "jobs": jobs,
        "candidates": candidates,
    })


@router.post("/sources/bulk-delete")
async def bulk_delete_sources(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("ids") if str(v).isdigit()]
    for source_id in ids:
        source = await db.get(Source, source_id)
        if source:
            await db.delete(source)
    await db.commit()
    return RedirectResponse(url="/sources", status_code=303)


@router.post("/sources/{source_id}/toggle")
async def toggle_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if source:
        source.is_active = not source.is_active
        await db.commit()
    return RedirectResponse(url="/sources", status_code=303)


@router.post("/sources/{source_id}/edit")
async def edit_source(
    source_id: int,
    url: str = Form(...),
    niche: str = Form("General"),
    notes: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(Source, source_id)
    if source:
        source.url = url.strip()
        source.niche = niche
        source.notes = notes.strip() if notes else None
        await db.commit()
    return RedirectResponse(url="/sources", status_code=303)


@router.post("/sources/{source_id}/delete")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if source:
        await db.delete(source)
        await db.commit()
    return RedirectResponse(url="/sources", status_code=303)
