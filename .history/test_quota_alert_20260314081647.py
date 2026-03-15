import asyncio
from app.database import engine, Base
from app.services.state_service import set_state
from app.models.system_state import SystemState  # noqa: F401

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("Forcing API quota state to TRUE for testing...")
    await set_state("zenrows_exhausted", "true")
    await set_state("scraperapi_exhausted", "true")
    await set_state("scrapingbee_exhausted", "true")
    await set_state("crawlbase_exhausted", "true")
    print("State updated. You can now refresh the dashboard.")

if __name__ == "__main__":
    asyncio.run(main())
