"""Quick check: dead domains and their availability."""
import asyncio, sys
sys.path.insert(0, ".")
from app.database import async_session
from sqlalchemy import select
from app.models.candidate import CandidateDomain

async def main():
    async with async_session() as db:
        r = await db.execute(select(CandidateDomain).where(CandidateDomain.is_domain_alive == False))
        dead = r.scalars().all()
        print(f"=== DEAD DOMAINS ({len(dead)}) ===")
        for d in dead:
            buy = "YES" if d.availability_status in ("available", "expired", "expiring_soon") else "NO"
            print(f"  {d.domain}: avail={d.availability_status} label={d.label} buyable={buy}")

asyncio.run(main())
