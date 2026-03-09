"""
RDAP Service — domain availability check via RDAP protocol (ICANN standard).

Replaces python-whois with direct RDAP queries:
  - GET https://rdap.org/domain/{domain}
  - 200 = registered (parse registrar, dates, status)
  - 404 = available (not registered)
"""

import asyncio
import logging
from datetime import datetime, date, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateDomain
from app.config import get_settings

logger = logging.getLogger(__name__)

RDAP_BASE = "https://rdap.org/domain"
RDAP_TIMEOUT = 15


async def _rdap_lookup(domain: str) -> dict:
    """RDAP lookup for a single domain. Fully async, no threads needed."""
    result = {
        "status": "unknown",
        "registrar": None,
        "created_date": None,
        "expiry_date": None,
        "days_left": None,
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(f"{RDAP_BASE}/{domain}", timeout=RDAP_TIMEOUT)

        if resp.status_code == 404:
            result["status"] = "available"
            return result

        if resp.status_code != 200:
            result["status"] = "check_failed"
            logger.warning("RDAP HTTP %d for %s", resp.status_code, domain)
            return result

        data = resp.json()

        # Extract registrar from entities
        for entity in data.get("entities", []):
            if "registrar" in entity.get("roles", []):
                vcard = entity.get("vcardArray", [None, []])
                if len(vcard) > 1:
                    for field in vcard[1]:
                        if field[0] == "fn":
                            result["registrar"] = field[3]
                            break
                # fallback to handle
                if not result["registrar"]:
                    result["registrar"] = entity.get("handle")
                break

        # Extract dates from events
        for event in data.get("events", []):
            action = event.get("eventAction", "")
            date_str = event.get("eventDate", "")
            if not date_str:
                continue

            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            if action == "registration":
                result["created_date"] = dt.date()
            elif action == "expiration":
                result["expiry_date"] = dt.date()

                now = datetime.now(timezone.utc)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = dt - now
                result["days_left"] = delta.days

                if delta.days < 0:
                    result["status"] = "expired"
                elif delta.days < 30:
                    result["status"] = "expiring_soon"
                elif delta.days < 90:
                    result["status"] = "expiring_watchlist"
                else:
                    result["status"] = "registered"

        # If we got 200 but no expiration event, it's still registered
        if result["status"] == "unknown":
            result["status"] = "registered"

    except httpx.TimeoutException:
        result["status"] = "check_failed"
        logger.warning("RDAP timeout for %s", domain)
    except Exception as e:
        result["status"] = "check_failed"
        logger.warning("RDAP error for %s: %s", domain, e)

    return result


async def check_single(domain: str) -> dict:
    """Async RDAP lookup for a single domain."""
    return await _rdap_lookup(domain)


async def check_candidates(db: AsyncSession, source_id: int | None = None):
    """
    Batch RDAP check for all unchecked candidates.
    Updates DB directly.
    """
    settings = get_settings()

    query = select(CandidateDomain).where(CandidateDomain.whois_checked_at.is_(None))
    if source_id:
        query = query.where(CandidateDomain.source_id == source_id)

    result = await db.execute(query)
    candidates = result.scalars().all()

    if not candidates:
        logger.info("No unchecked candidates found")
        return 0

    logger.info("Starting RDAP check for %d candidates", len(candidates))
    checked = 0

    for candidate in candidates:
        try:
            data = await _rdap_lookup(candidate.domain)

            candidate.availability_status = data["status"]
            candidate.whois_registrar = data.get("registrar")
            candidate.whois_created_date = data.get("created_date")
            candidate.whois_expiry_date = data.get("expiry_date")
            candidate.whois_days_left = data.get("days_left")
            candidate.whois_checked_at = datetime.now(timezone.utc)

            checked += 1
            logger.info("  [%d/%d] %s → %s", checked, len(candidates), candidate.domain, data["status"])

        except Exception as e:
            candidate.availability_status = "check_failed"
            candidate.whois_checked_at = datetime.now(timezone.utc)
            logger.error("RDAP failed for %s: %s", candidate.domain, e)

        # Throttle
        await asyncio.sleep(settings.RDAP_DELAY_SECONDS)

        await db.commit()

    logger.info("RDAP check completed: %d/%d", checked, len(candidates))
    return checked
