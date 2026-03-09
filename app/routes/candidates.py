"""Candidates routes — list, detail, notes."""

from datetime import date
from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.candidate import CandidateDomain
from app.services.toxicity_service import check_language_mismatch, check_young_domain

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PAGE_SIZE = 50


@router.get("/candidates")
async def list_candidates(
    request: Request,
    page: int = Query(1, ge=1),
    status: str = Query(None),
    availability: str = Query(None),
    label: str = Query(None),
    niche: str = Query(None),
    q: str = Query(None),
    sort: str = Query("created_at"),
    db: AsyncSession = Depends(get_db),
):
    query = select(CandidateDomain)

    # Filters
    if status == "dead":
        query = query.where(CandidateDomain.is_domain_alive == False)
    elif status == "alive":
        query = query.where(CandidateDomain.is_domain_alive == True)

    if availability:
        query = query.where(CandidateDomain.availability_status == availability)

    if label:
        query = query.where(CandidateDomain.label == label)

    if niche:
        query = query.where(CandidateDomain.niche == niche)

    if q:
        query = query.where(CandidateDomain.domain.ilike(f"%{q}%"))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Sort
    if sort == "domain":
        query = query.order_by(CandidateDomain.domain)
    elif sort == "score":
        query = query.order_by(CandidateDomain.score_total.desc().nulls_last())
    else:
        query = query.order_by(CandidateDomain.created_at.desc())

    # Pagination
    offset = (page - 1) * PAGE_SIZE
    query = query.offset(offset).limit(PAGE_SIZE)

    result = await db.execute(query)
    candidates = result.scalars().all()

    # Summary counts
    total_all = (await db.execute(select(func.count()).select_from(CandidateDomain))).scalar()
    dead_all = (await db.execute(
        select(func.count()).where(CandidateDomain.is_domain_alive == False)
    )).scalar()
    alive_all = total_all - dead_all

    # Availability counts
    avail_count = (await db.execute(
        select(func.count()).where(CandidateDomain.availability_status == "available")
    )).scalar()
    registered_count = (await db.execute(
        select(func.count()).where(CandidateDomain.availability_status == "registered")
    )).scalar()
    unchecked_count = (await db.execute(
        select(func.count()).where(CandidateDomain.availability_status.is_(None))
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

    # Niches for filter dropdown
    niche_result = await db.execute(
        select(CandidateDomain.niche).distinct()
    )
    niches = [r[0] for r in niche_result.all()]

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    return templates.TemplateResponse("candidates/shortlist.html", {
        "request": request,
        "candidates": candidates,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "total_all": total_all,
        "dead_all": dead_all,
        "alive_all": alive_all,
        "avail_count": avail_count,
        "registered_count": registered_count,
        "unchecked_count": unchecked_count,
        "available_label_count": available_label_count,
        "watchlist_count": watchlist_count,
        "uncertain_count": uncertain_count,
        "discard_count": discard_count,
        "niches": niches,
        "current_status": status,
        "current_availability": availability,
        "current_label": label,
        "current_niche": niche,
        "current_q": q,
        "current_sort": sort,
    })


@router.get("/candidates/{candidate_id}")
async def candidate_detail(
    request: Request,
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    candidate = await db.get(CandidateDomain, candidate_id)
    if not candidate:
        return RedirectResponse(url="/candidates", status_code=303)

    # Build toxicity flags for display
    flags = []
    lang_flag = check_language_mismatch(candidate.dominant_language, candidate.niche)
    if lang_flag:
        flags.append(lang_flag)
    young_flag = check_young_domain(candidate.whois_created_date)
    if young_flag:
        flags.append(young_flag)

    # Domain age
    domain_age = None
    if candidate.whois_created_date:
        age_days = (date.today() - candidate.whois_created_date).days
        if age_days >= 365:
            years = age_days // 365
            months = (age_days % 365) // 30
            domain_age = f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months != 1 else ''}"
        elif age_days >= 30:
            months = age_days // 30
            domain_age = f"{months} month{'s' if months > 1 else ''}"
        else:
            domain_age = f"{age_days} day{'s' if age_days != 1 else ''}"

    return templates.TemplateResponse("candidates/detail.html", {
        "request": request,
        "c": candidate,
        "flags": flags,
        "domain_age": domain_age,
    })


@router.post("/candidates/{candidate_id}/notes")
async def update_notes(
    candidate_id: int,
    owner_notes: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    candidate = await db.get(CandidateDomain, candidate_id)
    if candidate:
        candidate.owner_notes = owner_notes
        await db.commit()
    return RedirectResponse(url=f"/candidates/{candidate_id}", status_code=303)


@router.post("/candidates/{candidate_id}/delete")
async def delete_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    candidate = await db.get(CandidateDomain, candidate_id)
    if candidate:
        await db.delete(candidate)
        await db.commit()
    return RedirectResponse(url="/candidates", status_code=303)


@router.post("/candidates/bulk-delete")
async def bulk_delete_candidates(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    ids = form.getlist("ids")
    if ids:
        int_ids = [int(i) for i in ids]
        result = await db.execute(
            select(CandidateDomain).where(CandidateDomain.id.in_(int_ids))
        )
        for candidate in result.scalars().all():
            await db.delete(candidate)
        await db.commit()
    return RedirectResponse(url="/candidates", status_code=303)


@router.post("/candidates/bulk-label")
async def bulk_label_candidates(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    ids = form.getlist("ids")
    new_label = form.get("label", "")
    valid_labels = {"Available", "Watchlist", "Uncertain", "Discard"}
    if ids and new_label in valid_labels:
        int_ids = [int(i) for i in ids]
        result = await db.execute(
            select(CandidateDomain).where(CandidateDomain.id.in_(int_ids))
        )
        for candidate in result.scalars().all():
            candidate.label = new_label
            candidate.label_reason = f"Manually set to {new_label}"
        await db.commit()
    return RedirectResponse(url="/candidates", status_code=303)
