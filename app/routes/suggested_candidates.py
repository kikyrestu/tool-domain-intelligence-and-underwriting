"""Suggested Candidates routes — review dan evaluate domain yang ditemukan sistem (Wayback, dll).

Alur:
  sistem menemukan domain → suggested_candidates → owner evaluate → candidate_domains → RDAP + Wayback check
"""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.suggested_candidate import SuggestedCandidate
from app.models.candidate import CandidateDomain

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

NICHES = [
    "General",
    "Technology", "Finance", "Health", "Education", "Travel",
    "Gaming", "News", "Entertainment", "Business", "Science",
    "Sports", "Lifestyle", "Food", "Real Estate", "Crypto",
    "Marketing", "Other",
]


@router.get("/candidates/suggested")
async def list_suggested_candidates(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SuggestedCandidate).order_by(SuggestedCandidate.created_at.desc())
    )
    suggestions = result.scalars().all()
    total = len(suggestions)
    return templates.TemplateResponse("candidates/suggested.html", {
        "request": request,
        "suggestions": suggestions,
        "total": total,
        "niches": NICHES,
    })


async def _promote_to_candidate(sc: SuggestedCandidate, niche: str, db: AsyncSession) -> bool:
    """Convert a SuggestedCandidate to a CandidateDomain. Returns True if created."""
    # Dedup check: don't create if domain already exists as candidate
    existing = await db.execute(
        select(CandidateDomain).where(CandidateDomain.domain == sc.domain)
    )
    if existing.scalar_one_or_none() is not None:
        # Already a candidate — just remove the suggestion
        await db.delete(sc)
        return False

    db.add(CandidateDomain(
        domain=sc.domain,
        source_id=None,        # no crawl source — promoted from suggested_candidates
        crawl_job_id=None,     # no crawl job
        niche=niche or sc.niche,
        source_url_found=f"https://{sc.discovered_from}/",
        original_link=f"https://{sc.domain}/",
        source_type=sc.discovery_source,
        parser_type="wayback_cdx" if sc.discovery_source == "wayback" else sc.discovery_source,
        source_origin=f"https://{sc.discovered_from}/",
        extraction_note=f"Auto-promoted from suggested candidates — discovered via {sc.discovery_source} from {sc.discovered_from}",
    ))
    await db.delete(sc)
    return True


@router.post("/candidates/suggested/{sid}/evaluate")
async def evaluate_suggestion(
    sid: int,
    niche: str = Form("General"),
    db: AsyncSession = Depends(get_db),
):
    sc = await db.get(SuggestedCandidate, sid)
    if sc:
        await _promote_to_candidate(sc, niche, db)
        await db.commit()
    return RedirectResponse(url="/candidates/suggested", status_code=303)


@router.post("/candidates/suggested/{sid}/dismiss")
async def dismiss_suggestion(sid: int, db: AsyncSession = Depends(get_db)):
    sc = await db.get(SuggestedCandidate, sid)
    if sc:
        await db.delete(sc)
        await db.commit()
    return RedirectResponse(url="/candidates/suggested", status_code=303)


@router.post("/candidates/suggested/bulk-evaluate")
async def bulk_evaluate(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("ids") if str(v).isdigit()]
    niche = form.get("niche", "General")

    promoted = 0
    for sid in ids:
        sc = await db.get(SuggestedCandidate, sid)
        if sc:
            created = await _promote_to_candidate(sc, niche, db)
            if created:
                promoted += 1

    await db.commit()
    return RedirectResponse(url="/candidates/suggested", status_code=303)


@router.post("/candidates/suggested/bulk-dismiss")
async def bulk_dismiss(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("ids") if str(v).isdigit()]

    for sid in ids:
        sc = await db.get(SuggestedCandidate, sid)
        if sc:
            await db.delete(sc)

    await db.commit()
    return RedirectResponse(url="/candidates/suggested", status_code=303)
