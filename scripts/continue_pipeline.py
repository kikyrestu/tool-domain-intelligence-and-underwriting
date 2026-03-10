"""Continue pipeline from where it left off: Wayback (remaining) + Score."""
import asyncio, sys, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.WARNING)

from app.database import async_session
from sqlalchemy import select
from app.models.candidate import CandidateDomain
from app.services.wayback_service import check_candidates as wayback_check
from app.services.toxicity_service import scan_candidate
from app.services.scoring_service import score_candidates

async def run():
    print("Wayback (remaining unchecked)...")
    try:
        async with async_session() as db:
            n = await wayback_check(db)
            print(f"Wayback checked: {n}")
    except Exception as e:
        print(f"Wayback partial error: {e}")

    print("Scoring all...")
    try:
        import json
        async with async_session() as db:
            result = await db.execute(select(CandidateDomain))
            candidates = result.scalars().all()
            tox = {
                c.id: json.loads(c.toxicity_flags) if c.toxicity_flags else scan_candidate(c, [])
                for c in candidates
            }
            n = await score_candidates(db, toxicity_map=tox)
            print(f"Scored: {n}")
    except Exception as e:
        print(f"Score error: {e}")

    print("DONE")

asyncio.run(run())
