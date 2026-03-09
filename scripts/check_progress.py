import asyncio, sys
sys.path.insert(0, ".")
from app.database import async_session
from sqlalchemy import select, func
from app.models.candidate import CandidateDomain

async def check():
    async with async_session() as db:
        total = (await db.execute(select(func.count()).select_from(CandidateDomain))).scalar()
        has_whois = (await db.execute(select(func.count()).select_from(CandidateDomain).where(CandidateDomain.availability_status.is_not(None)))).scalar()
        has_wb = (await db.execute(select(func.count()).select_from(CandidateDomain).where(CandidateDomain.wayback_checked_at.is_not(None)))).scalar()
        has_score = (await db.execute(select(func.count()).select_from(CandidateDomain).where(CandidateDomain.score_total.is_not(None)))).scalar()
        print(f"Total={total} WHOIS={has_whois} Wayback={has_wb} Score={has_score}")

asyncio.run(check())
