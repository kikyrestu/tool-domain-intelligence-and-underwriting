"""One-off script to run WHOIS → Wayback → Score pipeline for all candidates."""
import asyncio
import sys
import logging

sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from app.database import async_session
from sqlalchemy import select
from app.models.candidate import CandidateDomain
from app.services.whois_service import check_candidates as whois_check
from app.services.wayback_service import check_candidates as wayback_check
from app.services.toxicity_service import scan_candidate
from app.services.scoring_service import score_candidates


async def run_all():
    print("=== STEP 1: WHOIS check ===")
    try:
        async with async_session() as db:
            n = await whois_check(db)
            print(f"WHOIS checked: {n}")
    except Exception as e:
        print(f"WHOIS error (partial data saved): {e}")

    print("=== STEP 2: Wayback check ===")
    try:
        async with async_session() as db:
            n = await wayback_check(db)
            print(f"Wayback checked: {n}")
    except Exception as e:
        print(f"Wayback error (partial data saved): {e}")

    print("=== STEP 3: Scoring ===")
    try:
        import json
        async with async_session() as db:
            result = await db.execute(select(CandidateDomain))
            candidates = result.scalars().all()
            toxicity_map = {
                c.id: json.loads(c.toxicity_flags) if c.toxicity_flags else scan_candidate(c, [])
                for c in candidates
            }
            n = await score_candidates(db, toxicity_map=toxicity_map)
            print(f"Scored: {n}")
    except Exception as e:
        print(f"Score error: {e}")

    print("=== DONE ===")


if __name__ == "__main__":
    asyncio.run(run_all())
