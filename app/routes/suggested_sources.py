"""Suggested sources routes — review, approve, reject domain discoveries from Wayback."""

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.suggested_source import SuggestedSource
from app.models.source import Source

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

NICHES = [
    "General",
    "Technology", "Finance", "Health", "Education", "Travel",
    "Gaming", "News", "Entertainment", "Business", "Science",
    "Sports", "Lifestyle", "Food", "Real Estate", "Crypto",
    "Marketing", "Other",
]


@router.get("/sources/suggested")
async def list_suggested(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SuggestedSource).order_by(SuggestedSource.created_at.desc())
    )
    suggestions = result.scalars().all()
    return templates.TemplateResponse("sources/suggested.html", {
        "request": request,
        "suggestions": suggestions,
        "niches": NICHES,
    })


@router.post("/sources/suggested/{sid}/approve")
async def approve_suggestion(
    sid: int,
    niche: str = Form("General"),
    notes: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    sug = await db.get(SuggestedSource, sid)
    if not sug:
        return RedirectResponse(url="/sources/suggested", status_code=303)

    # Check not already a live source
    existing = await db.execute(select(Source).where(Source.url == sug.url))
    if existing.scalar_one_or_none() is None:
        db.add(Source(
            url=sug.url,
            niche=niche,
            notes=notes.strip() if notes else f"Approved from Wayback suggestion (found in {sug.discovered_from})",
            is_active=True,
        ))

    await db.delete(sug)
    await db.commit()
    return RedirectResponse(url="/sources/suggested", status_code=303)


@router.post("/sources/suggested/{sid}/reject")
async def reject_suggestion(sid: int, db: AsyncSession = Depends(get_db)):
    sug = await db.get(SuggestedSource, sid)
    if sug:
        await db.delete(sug)
        await db.commit()
    return RedirectResponse(url="/sources/suggested", status_code=303)


@router.post("/sources/suggested/bulk-approve")
async def bulk_approve(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("ids") if str(v).isdigit()]
    niche = form.get("niche", "General")

    for sid in ids:
        sug = await db.get(SuggestedSource, sid)
        if not sug:
            continue
        existing = await db.execute(select(Source).where(Source.url == sug.url))
        if existing.scalar_one_or_none() is None:
            db.add(Source(
                url=sug.url,
                niche=str(niche),
                notes=f"Approved from Wayback suggestion (found in {sug.discovered_from})",
                is_active=True,
            ))
        await db.delete(sug)

    await db.commit()
    return RedirectResponse(url="/sources/suggested", status_code=303)


@router.post("/sources/suggested/bulk-reject")
async def bulk_reject(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    ids = [int(v) for v in form.getlist("ids") if str(v).isdigit()]

    for sid in ids:
        sug = await db.get(SuggestedSource, sid)
        if sug:
            await db.delete(sug)

    await db.commit()
    return RedirectResponse(url="/sources/suggested", status_code=303)
