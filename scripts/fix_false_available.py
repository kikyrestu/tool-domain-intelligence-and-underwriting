"""Re-check semua candidate yang saat ini ber-status 'available' tapi DNS masih resolve."""
import asyncio
import sys
sys.path.insert(0, '.')

import dns.asyncresolver
from sqlalchemy import select, update
from app.database import engine
from app.models.candidate import CandidateDomain
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def main():
    async with AsyncSessionLocal() as db:
        # Ambil semua yang ditandai available
        result = await db.execute(
            select(CandidateDomain).where(CandidateDomain.availability_status == "available")
        )
        candidates = result.scalars().all()
        print(f"Found {len(candidates)} 'available' candidates to re-check")

        fixed = 0
        for c in candidates:
            dns_ok = False
            try:
                ans = await dns.asyncresolver.resolve(c.domain, "A")
                if ans:
                    dns_ok = True
            except Exception:
                pass
            if not dns_ok:
                try:
                    ans = await dns.asyncresolver.resolve(c.domain, "AAAA")
                    if ans:
                        dns_ok = True
                except Exception:
                    pass

            if dns_ok:
                c.availability_status = "registered"
                c.whois_checked_at = None  # force re-check RDAP on next run
                fixed += 1
                print(f"  FIXED: {c.domain} → registered (DNS resolves)")
            else:
                print(f"  OK: {c.domain} → truly available (no DNS)")

        await db.commit()
        print(f"\nDone. Fixed {fixed}/{len(candidates)} false-positive 'available' domains.")


asyncio.run(main())
