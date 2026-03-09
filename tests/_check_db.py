import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import select
from app.database import async_session
from app.models.candidate import CandidateDomain

async def check():
    async with async_session() as db:
        r = await db.execute(select(CandidateDomain).order_by(CandidateDomain.created_at.desc()).limit(15))
        for c in r.scalars().all():
            print(f"{c.id:>3} | {c.domain:<30} | dead={str(c.is_dead_link):<5} | http={c.http_status} | avail={c.availability_status} | score={c.score_total} | label={c.label} | snaps={c.wayback_total_snapshots} | lang={c.dominant_language} | src={c.source_id}")

asyncio.run(check())
