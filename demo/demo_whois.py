"""
Demo WHOIS Availability Check
Cek status domain: available / registered / expiring / error

Jalankan: python demo/demo_whois.py domain1.com domain2.net domain3.org
Atau pipe dari crawl: python demo/demo_whois.py --from-list domains.txt
"""

import asyncio
import sys
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import whois


# ============================================================
# WHOIS ENGINE
# ============================================================

def check_whois(domain: str) -> dict:
    """Cek WHOIS untuk satu domain. Return dict status."""
    result = {
        "domain": domain,
        "status": "unknown",
        "registrar": None,
        "creation_date": None,
        "expiration_date": None,
        "days_until_expiry": None,
        "name_servers": None,
        "error": None,
        "check_time_ms": None,
    }

    start = time.monotonic()
    try:
        w = whois.whois(domain)
        elapsed = round((time.monotonic() - start) * 1000)
        result["check_time_ms"] = elapsed

        # WHOIS bisa return None kalau domain tidak terdaftar
        if not w or not w.domain_name:
            result["status"] = "available"
            return result

        # Parse dates
        creation = w.creation_date
        expiration = w.expiration_date
        if isinstance(creation, list):
            creation = creation[0]
        if isinstance(expiration, list):
            expiration = expiration[0]

        result["registrar"] = w.registrar
        result["creation_date"] = str(creation) if creation else None
        result["expiration_date"] = str(expiration) if expiration else None
        result["name_servers"] = (
            list(set(ns.lower() for ns in w.name_servers)) if w.name_servers else None
        )

        # Hitung sisa hari sebelum expire
        if expiration:
            now = datetime.now(timezone.utc)
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=timezone.utc)
            delta = expiration - now
            result["days_until_expiry"] = delta.days

            if delta.days < 0:
                result["status"] = "expired"
            elif delta.days < 30:
                result["status"] = "expiring_soon"
            elif delta.days < 90:
                result["status"] = "expiring_watchlist"
            else:
                result["status"] = "registered"
        else:
            result["status"] = "registered"

    except whois.parser.PywhoisError:
        result["status"] = "available"
        result["check_time_ms"] = round((time.monotonic() - start) * 1000)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["check_time_ms"] = round((time.monotonic() - start) * 1000)

    return result


async def check_whois_batch(domains: list[str], max_workers: int = 3) -> list[dict]:
    """Batch WHOIS check dengan ThreadPool (WHOIS is blocking I/O)."""
    results = []
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = []
        for domain in domains:
            task = loop.run_in_executor(executor, check_whois, domain)
            tasks.append(task)
            # Throttle: delay antar submit untuk avoid rate limit
            await asyncio.sleep(1.5)

        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    final = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            final.append({
                "domain": domains[i],
                "status": "error",
                "error": str(r),
            })
        else:
            final.append(r)

    return final


# ============================================================
# DISPLAY
# ============================================================

STATUS_ICONS = {
    "available": "🟢",
    "expired": "🔥",
    "expiring_soon": "⚡",
    "expiring_watchlist": "👀",
    "registered": "🔒",
    "error": "⚠️",
    "unknown": "❓",
}

STATUS_LABELS = {
    "available": "AVAILABLE — Bisa dibeli langsung!",
    "expired": "EXPIRED — Bisa diambil segera!",
    "expiring_soon": "EXPIRING <30 HARI — Pantau ketat!",
    "expiring_watchlist": "EXPIRING <90 HARI — Masuk watchlist",
    "registered": "REGISTERED — Tidak available",
    "error": "ERROR — Gagal cek",
    "unknown": "UNKNOWN",
}


def display_results(results: list[dict]):
    """Tampilkan hasil WHOIS check."""
    print(f"\n{'='*70}")
    print(f"📋 HASIL WHOIS AVAILABILITY CHECK")
    print(f"{'='*70}\n")

    # Group by status
    available = [r for r in results if r["status"] in ("available", "expired")]
    watchlist = [r for r in results if r["status"] in ("expiring_soon", "expiring_watchlist")]
    registered = [r for r in results if r["status"] == "registered"]
    errors = [r for r in results if r["status"] in ("error", "unknown")]

    # Summary
    print(f"   Total dicek   : {len(results)}")
    print(f"   🟢 Available   : {len(available)}")
    print(f"   👀 Watchlist   : {len(watchlist)}")
    print(f"   🔒 Registered  : {len(registered)}")
    print(f"   ⚠️  Error       : {len(errors)}")

    # Detail per domain
    print(f"\n{'─'*70}")
    for r in results:
        icon = STATUS_ICONS.get(r["status"], "❓")
        label = STATUS_LABELS.get(r["status"], "UNKNOWN")
        print(f"\n   {icon} {r['domain']}")
        print(f"      Status     : {label}")
        if r.get("registrar"):
            print(f"      Registrar  : {r['registrar']}")
        if r.get("creation_date"):
            print(f"      Created    : {r['creation_date']}")
        if r.get("expiration_date"):
            print(f"      Expires    : {r['expiration_date']}")
        if r.get("days_until_expiry") is not None:
            days = r["days_until_expiry"]
            if days < 0:
                print(f"      Expired    : {abs(days)} hari lalu")
            else:
                print(f"      Sisa       : {days} hari lagi")
        if r.get("name_servers"):
            ns_display = ", ".join(r["name_servers"][:3])
            print(f"      NS         : {ns_display}")
        if r.get("check_time_ms"):
            print(f"      Check time : {r['check_time_ms']}ms")
        if r.get("error"):
            print(f"      Error      : {r['error']}")

    # Actionable summary
    if available or watchlist:
        print(f"\n{'='*70}")
        print(f"🎯 ACTIONABLE DOMAINS")
        print(f"{'='*70}")
        for r in available:
            print(f"   🟢 {r['domain']:30s} → {STATUS_LABELS[r['status']]}")
        for r in watchlist:
            days = r.get("days_until_expiry", "?")
            print(f"   👀 {r['domain']:30s} → Expires in {days} days")


# ============================================================
# MAIN
# ============================================================

async def main(domains: list[str]):
    print(f"\n{'='*70}")
    print(f"🔍 WHOIS Availability Check — {len(domains)} domains")
    print(f"{'='*70}")
    print(f"   ⏳ Checking with 1.5s delay per domain (rate limit protection)...\n")

    results = await check_whois_batch(domains)
    display_results(results)

    print(f"\n✅ WHOIS check selesai!")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python demo/demo_whois.py domain1.com domain2.net ...")
        print("       python demo/demo_whois.py --from-list domains.txt")
        sys.exit(1)

    if sys.argv[1] == "--from-list":
        filepath = sys.argv[2]
        domains = Path(filepath).read_text().strip().splitlines()
    else:
        domains = sys.argv[1:]

    asyncio.run(main(domains))
