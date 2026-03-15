import asyncio
from app.database import async_session
from app.services.crawl_service import check_alive_candidates
from app.models.candidate import CandidateDomain
from sqlalchemy import select

async def main():
    try:
        async with async_session() as db:
            cands = await db.execute(select(CandidateDomain).limit(2))
            cand_objs = cands.scalars().all()
            ids = [c.id for c in cand_objs]
            print("Trying to check ids:", ids)
            result = await check_alive_candidates(db, candidate_ids=ids)
            print("check_alive_candidates result:", result)
            
            # Check if updated
            for c in cand_objs:
                await db.refresh(c)
                print(f"ID: {c.id}, is_domain_alive: {c.is_domain_alive}")
    except Exception as e:
        print("EXCEPTION:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
