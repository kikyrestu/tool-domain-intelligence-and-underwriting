"""
WHOIS Service — availability check + DNS resolution + status tagging.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timezone

import whois
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateDomain
from app.config import get_settings

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=3)


def _whois_lookup(domain: str) -> dict:
    """Blocking WHOIS lookup for a single domain."""
    result = {
        "status": "unknown",
        "registrar": None,
        "created_date": None,
        "expiry_date": None,
        "days_left": None,
    }

    try:
        w = whois.whois(domain)

        if not w or not w.domain_name:
            result["status"] = "available"
            return result

        creation = w.creation_date
        expiration = w.expiration_date
        if isinstance(creation, list):
            creation = creation[0]
        if isinstance(expiration, list):
            expiration = expiration[0]

        result["registrar"] = w.registrar

        if creation:
            result["created_date"] = creation.date() if isinstance(creation, datetime) else creation

        if expiration:
            if isinstance(expiration, datetime):
                exp_dt = expiration
            else:
                exp_dt = datetime.combine(expiration, datetime.min.time())

            result["expiry_date"] = exp_dt.date() if isinstance(exp_dt, datetime) else expiration

            now = datetime.now(timezone.utc)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            delta = exp_dt - now
            result["days_left"] = delta.days

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
    except Exception as e:
        result["status"] = "check_failed"
        logger.warning("WHOIS error for %s: %s", domain, e)

    return result


def _dns_check(domain: str) -> bool:
    """Check if domain has DNS records (simple socket resolution)."""
    import socket
    try:
        socket.getaddrinfo(domain, None, socket.AF_INET)
        return True
    except socket.gaierror:
        return False


def _check_domain(domain: str) -> dict:
    """Combined WHOIS + DNS check with status tagging."""
    whois_data = _whois_lookup(domain)
    dns_has_records = _dns_check(domain)

    # Refine status with DNS data
    if whois_data["status"] == "available" and not dns_has_records:
        whois_data["status"] = "available"  # confirmed
    elif whois_data["status"] == "available" and dns_has_records:
        whois_data["status"] = "registered"  # WHOIS missed it but DNS resolves

    whois_data["dns_has_records"] = dns_has_records
    return whois_data


async def check_single(domain: str) -> dict:
    """Async wrapper for single domain check."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _check_domain, domain)


async def check_candidates(db: AsyncSession, source_id: int | None = None):
    """
    Batch WHOIS check for all unchecked candidates.
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

    logger.info("Starting WHOIS check for %d candidates", len(candidates))
    checked = 0

    for candidate in candidates:
        try:
            data = await check_single(candidate.domain)

            candidate.availability_status = data["status"]
            candidate.whois_registrar = data.get("registrar")
            candidate.whois_created_date = data.get("created_date")
            candidate.whois_expiry_date = data.get("expiry_date")
            candidate.whois_days_left = data.get("days_left")
            candidate.dns_has_records = data.get("dns_has_records")
            candidate.whois_checked_at = datetime.now(timezone.utc)

            checked += 1
            logger.info("  [%d/%d] %s → %s", checked, len(candidates), candidate.domain, data["status"])

        except Exception as e:
            candidate.availability_status = "check_failed"
            candidate.whois_checked_at = datetime.now(timezone.utc)
            logger.error("WHOIS failed for %s: %s", candidate.domain, e)

        # Throttle
        await asyncio.sleep(settings.WHOIS_DELAY_SECONDS)

    await db.commit()
    logger.info("WHOIS check completed: %d/%d", checked, len(candidates))
    return checked
