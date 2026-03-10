"""
Scheduler — background task yang jalan otomatis.

Re-check RDAP + re-score untuk SEMUA domain, dengan interval berbeda per status:
  expiring_soon / expired  → setiap 6 jam
  available / expiring_watchlist → setiap 24 jam
  registered               → setiap 7 hari
  unchecked / lainnya      → setiap 24 jam
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import async_session
from app.models.candidate import CandidateDomain
from app.services.whois_service import _rdap_lookup
from app.services.scoring_service import calculate_score
from app.services.toxicity_service import check_language_mismatch, check_young_domain

logger = logging.getLogger(__name__)

# How often each availability_status is re-checked
_RECHECK_INTERVALS: dict[str, timedelta] = {
    "expiring_soon":      timedelta(hours=6),
    "expired":            timedelta(hours=6),
    "available":          timedelta(hours=24),
    "expiring_watchlist": timedelta(hours=24),
    "registered":         timedelta(days=7),
}
_DEFAULT_INTERVAL = timedelta(hours=24)

# Scheduler poll interval — check every hour which domains are due
_POLL_INTERVAL_SECONDS = 3600


async def _recheck_one(candidate_id: int) -> None:
    """RDAP re-check + re-score a single candidate (fresh DB session each time)."""
    async with async_session() as db:
        c = await db.get(CandidateDomain, candidate_id)
        if not c:
            return

        try:
            data = await _rdap_lookup(c.domain)
            old_status = c.availability_status

            c.availability_status = data["status"]
            c.whois_registrar = data.get("registrar")
            c.whois_expiry_date = data.get("expiry_date")
            c.whois_days_left = data.get("days_left")
            c.whois_checked_at = datetime.now(timezone.utc)
            if data.get("created_date"):
                c.whois_created_date = data["created_date"]

            # Use stored toxicity_flags from Wayback scan; fall back to metadata-only
            import json
            if c.toxicity_flags:
                flags = json.loads(c.toxicity_flags)
            else:
                flags = []
                lang_flag = check_language_mismatch(c.dominant_language, c.niche)
                if lang_flag:
                    flags.append(lang_flag)
                young_flag = check_young_domain(c.whois_created_date)
                if young_flag:
                    flags.append(young_flag)

            scores = calculate_score(c, flags)
            c.score_availability = scores["score_availability"]
            c.score_continuity = scores["score_continuity"]
            c.score_cleanliness = scores["score_cleanliness"]
            c.score_total = scores["score_total"]
            c.label = scores["label"]
            c.label_reason = scores["label_reason"]

            await db.commit()

            if old_status != data["status"]:
                logger.info("[Scheduler] %s: %s → %s (label: %s)",
                            c.domain, old_status, data["status"], scores["label"])
            else:
                logger.debug("[Scheduler] %s: tetap %s", c.domain, data["status"])

        except Exception as e:
            logger.warning("[Scheduler] Error re-check %s: %s", c.domain, e)


async def _recheck_due() -> None:
    """Find domains that are due for a re-check and process them."""
    now = datetime.now(timezone.utc)

    async with async_session() as db:
        result = await db.execute(select(CandidateDomain.id,
                                         CandidateDomain.availability_status,
                                         CandidateDomain.whois_checked_at))
        rows = result.all()

    due_ids: list[int] = []
    for cid, status, checked_at in rows:
        interval = _RECHECK_INTERVALS.get(status or "", _DEFAULT_INTERVAL)
        if checked_at is None:
            due_ids.append(cid)
        else:
            checked_utc = checked_at if checked_at.tzinfo else checked_at.replace(tzinfo=timezone.utc)
            if (now - checked_utc) >= interval:
                due_ids.append(cid)

    if not due_ids:
        logger.debug("[Scheduler] No domains due for re-check.")
        return

    logger.info("[Scheduler] Re-checking %d/%d domains…", len(due_ids), len(rows))
    for cid in due_ids:
        await _recheck_one(cid)
        await asyncio.sleep(1)  # light throttle

    logger.info("[Scheduler] Batch re-check selesai.")


async def run_scheduler(interval_hours: float = 6.0):  # interval_hours kept for API compat
    """
    Loop tak terbatas — poll setiap jam, re-check domain yang sudah due.
    Dijalankan sebagai asyncio background task dari lifespan main.py.
    """
    logger.info("[Scheduler] Aktif — polling setiap jam, interval per-status.")

    while True:
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        try:
            await _recheck_due()
        except Exception as e:
            logger.error("[Scheduler] Unexpected error: %s", e)
