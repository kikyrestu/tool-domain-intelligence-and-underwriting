import asyncio
from app.database import async_session
from app.models.candidate import CandidateDomain
from sqlalchemy import select

async def main():
    domains = ["hdmediaventures.com", "printninja.com", "securepaynet.net", "issuu.com", "hotjar.com"]
    try:
        async with async_session() as db:
            result = await db.execute(select(CandidateDomain).where(CandidateDomain.domain.in_(domains)))
            cands = result.scalars().all()
            for c in cands:
                print(f"Domain: {c.domain}, ID: {c.id}, is_domain_alive: {c.is_domain_alive}")
    except Exception as e:
        print("EXCEPTION:", e)

if __name__ == "__main__":
    asyncio.run(main())
