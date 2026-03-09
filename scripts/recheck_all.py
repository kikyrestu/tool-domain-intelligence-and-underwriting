"""Re-check all domains with DNS+HTTP root logic, re-run RDAP, re-score."""
import asyncio
import sys
import logging

sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# Suppress noisy httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)

from app.database import async_session
from sqlalchemy import select
from app.models.candidate import CandidateDomain
from app.services.crawl_service import _check_domain, _get_headers, TIMEOUT
from app.services.whois_service import _rdap_lookup
from app.services.toxicity_service import scan_candidate
from app.services.scoring_service import score_candidates


async def step1_recheck_domains():
    """Re-check all domains using DNS + HTTP root. Dead domains get RDAP checked automatically."""
    print("=== STEP 1: Re-check all domains (DNS + HTTP root + RDAP for dead) ===")
    async with async_session() as db:
        result = await db.execute(select(CandidateDomain))
        candidates = result.scalars().all()
        print(f"  Checking {len(candidates)} domains...")

        sem = asyncio.Semaphore(5)
        total = len(candidates)
        checked = 0
        from datetime import datetime, timezone

        for c in candidates:
            status = await _check_domain(c.domain, sem)
            c.dns_resolves = status["dns_resolves"]
            c.http_status = status["http_status"]
            c.is_domain_alive = status["is_domain_alive"]

            # Save RDAP data if dead domain was checked
            if status.get("availability_status"):
                c.availability_status = status["availability_status"]
                c.whois_registrar = status.get("whois_registrar")
                c.whois_created_date = status.get("whois_created_date")
                c.whois_expiry_date = status.get("whois_expiry_date")
                c.whois_days_left = status.get("whois_days_left")
                c.whois_checked_at = datetime.now(timezone.utc)

            checked += 1

            alive_str = "ALIVE" if status["is_domain_alive"] else "DEAD"
            dns_str = "DNS:yes" if status["dns_resolves"] else "DNS:no"
            http_str = f"HTTP:{status['http_status']}" if status["http_status"] else "HTTP:none"
            avail_str = f" → {status['availability_status']}" if status.get("availability_status") else ""
            print(f"  [{checked}/{total}] {c.domain}: {alive_str} ({dns_str}, {http_str}){avail_str}")

            await db.commit()

    print(f"  Done: {checked}/{total} checked\n")


async def step2_fix_rdap():
    """Re-run RDAP for ALL domains (replace old WHOIS data)."""
    print("=== STEP 2: Re-run RDAP for all domains ===")
    async with async_session() as db:
        result = await db.execute(select(CandidateDomain))
        candidates = result.scalars().all()
        if not candidates:
            print("  No domains to check\n")
            return

        print(f"  Checking {len(candidates)} domains via RDAP...")
        from datetime import datetime, timezone

        for i, c in enumerate(candidates, 1):
            data = await _rdap_lookup(c.domain)
            c.availability_status = data["status"]
            c.whois_registrar = data.get("registrar")
            c.whois_created_date = data.get("created_date")
            c.whois_expiry_date = data.get("expiry_date")
            c.whois_days_left = data.get("days_left")
            c.whois_checked_at = datetime.now(timezone.utc)
            print(f"  [{i}/{len(candidates)}] {c.domain}: {data['status']}")
            await db.commit()
            await asyncio.sleep(0.5)

    print(f"  Done\n")


async def step3_rescore():
    """Re-score all candidates."""
    print("=== STEP 3: Re-score all candidates ===")
    async with async_session() as db:
        result = await db.execute(select(CandidateDomain))
        candidates = result.scalars().all()
        tox = {c.id: scan_candidate(c, []) for c in candidates}
        n = await score_candidates(db, toxicity_map=tox)
        print(f"  Scored: {n}\n")


async def main():
    await step1_recheck_domains()
    await step2_fix_rdap()
    await step3_rescore()

    # Summary
    print("=== SUMMARY ===")
    async with async_session() as db:
        result = await db.execute(select(CandidateDomain))
        candidates = result.scalars().all()
        labels = {}
        alive_count = 0
        dead_count = 0
        for c in candidates:
            labels[c.label] = labels.get(c.label, 0) + 1
            if c.is_domain_alive:
                alive_count += 1
            else:
                dead_count += 1

        print(f"  Total: {len(candidates)}")
        print(f"  Alive: {alive_count}, Dead: {dead_count}")
        for lbl, cnt in sorted(labels.items(), key=lambda x: -x[1]):
            print(f"  {lbl}: {cnt}")

        # Show l-ware.com specifically
        r = await db.execute(select(CandidateDomain).where(CandidateDomain.domain == 'l-ware.com'))
        lw = r.scalar_one_or_none()
        if lw:
            print(f"\n  l-ware.com: alive={lw.is_domain_alive} avail={lw.availability_status} label={lw.label} score={lw.score_total}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
