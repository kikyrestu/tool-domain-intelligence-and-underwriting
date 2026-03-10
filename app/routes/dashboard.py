"""Dashboard route — homepage summary."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.source import Source
from app.models.crawl_job import CrawlJob
from app.models.candidate import CandidateDomain

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    # Counts
    source_count = (await db.execute(select(func.count()).select_from(Source))).scalar()
    candidate_count = (await db.execute(select(func.count()).select_from(CandidateDomain))).scalar()
    dead_count = (await db.execute(
        select(func.count()).where(CandidateDomain.is_domain_alive == False)
    )).scalar()
    alive_count = (await db.execute(
        select(func.count()).where(CandidateDomain.is_domain_alive == True)
    )).scalar()

    # Availability counts
    avail_count = (await db.execute(
        select(func.count()).where(CandidateDomain.availability_status == "available")
    )).scalar()
    registered_count = (await db.execute(
        select(func.count()).where(CandidateDomain.availability_status == "registered")
    )).scalar()

    # Label counts
    available_label_count = (await db.execute(
        select(func.count()).where(CandidateDomain.label == "Available")
    )).scalar()
    watchlist_count = (await db.execute(
        select(func.count()).where(CandidateDomain.label == "Watchlist")
    )).scalar()
    uncertain_count = (await db.execute(
        select(func.count()).where(CandidateDomain.label == "Uncertain")
    )).scalar()
    discard_count = (await db.execute(
        select(func.count()).where(CandidateDomain.label == "Discard")
    )).scalar()

    # Niche breakdown
    niche_stats_result = await db.execute(
        select(
            CandidateDomain.niche,
            func.count().label("count"),
        ).group_by(CandidateDomain.niche)
    )
    niche_stats = [{"niche": r[0], "count": r[1]} for r in niche_stats_result.all()]

    # Recent crawl jobs
    recent_jobs_result = await db.execute(
        select(CrawlJob).order_by(CrawlJob.created_at.desc()).limit(5)
    )
    recent_jobs = recent_jobs_result.scalars().all()

    # Top scored candidates
    top_candidates_result = await db.execute(
        select(CandidateDomain)
        .where(CandidateDomain.score_total.isnot(None))
        .order_by(CandidateDomain.score_total.desc())
        .limit(10)
    )
    top_candidates = top_candidates_result.scalars().all()

    # Recent candidates (unscored)
    recent_candidates_result = await db.execute(
        select(CandidateDomain).order_by(CandidateDomain.created_at.desc()).limit(10)
    )
    recent_candidates = recent_candidates_result.scalars().all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "source_count": source_count,
        "candidate_count": candidate_count,
        "dead_count": dead_count,
        "alive_count": alive_count,
        "avail_count": avail_count,
        "registered_count": registered_count,
        "available_label_count": available_label_count,
        "watchlist_count": watchlist_count,
        "uncertain_count": uncertain_count,
        "discard_count": discard_count,
        "niche_stats": niche_stats,
        "recent_jobs": recent_jobs,
        "top_candidates": top_candidates,
        "recent_candidates": recent_candidates,
    })


@router.get("/api/notifications")
async def get_notifications(db: AsyncSession = Depends(get_db)):
    """Return notifications for starred domains that are expiring or newly available."""
    alerts = []

    # Starred + expiring soon (< 30 days)
    result = await db.execute(
        select(CandidateDomain).where(
            CandidateDomain.is_starred == True,
            CandidateDomain.availability_status == "expiring_soon",
        )
    )
    for c in result.scalars().all():
        alerts.append({
            "type": "warning",
            "message": f"⚠️ {c.domain} expires in {c.whois_days_left} days!",
            "url": f"/candidates/{c.id}",
        })

    # Starred + expired
    result = await db.execute(
        select(CandidateDomain).where(
            CandidateDomain.is_starred == True,
            CandidateDomain.availability_status == "expired",
        )
    )
    for c in result.scalars().all():
        alerts.append({
            "type": "danger",
            "message": f"🔴 {c.domain} has EXPIRED — check if available to buy!",
            "url": f"/candidates/{c.id}",
        })

    # Starred + now available (drop domain — was registered before)
    result = await db.execute(
        select(CandidateDomain).where(
            CandidateDomain.is_starred == True,
            CandidateDomain.availability_status == "available",
        )
    )
    for c in result.scalars().all():
        alerts.append({
            "type": "success",
            "message": f"🟢 {c.domain} is now AVAILABLE to buy!",
            "url": f"/candidates/{c.id}",
        })

    # Expiring watchlist starred (< 90 days)
    result = await db.execute(
        select(CandidateDomain).where(
            CandidateDomain.is_starred == True,
            CandidateDomain.availability_status == "expiring_watchlist",
        )
    )
    for c in result.scalars().all():
        alerts.append({
            "type": "info",
            "message": f"📅 {c.domain} expires in {c.whois_days_left} days (watchlist)",
            "url": f"/candidates/{c.id}",
        })

    return JSONResponse({"alerts": alerts})
