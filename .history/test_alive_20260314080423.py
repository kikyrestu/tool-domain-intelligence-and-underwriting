import asyncio
from app.database import async_session
from app.services.crawl_service import check_alive_candidates

async def main():
    try:
        async with async_session() as db:
            result = await check_alive_candidates(db, candidate_ids=[1, 2, 3, 4, 5])
            print("check_alive_candidates result:", result)
    except Exception as e:
        print("EXCEPTION:", e)

if __name__ == "__main__":
    asyncio.run(main())
