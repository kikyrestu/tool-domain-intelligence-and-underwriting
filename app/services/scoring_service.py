"""
Scoring engine — 3-component weighted score + label + reason.

Components:
  1. Availability (30%) — based on WHOIS status
  2. Continuity  (40%) — Wayback snapshots, language consistency, drift
  3. Cleanliness (30%) — toxicity flags

Labels (intent-based):
  Available  — domain benar-benar bisa ditindaklanjuti (dead link + available/expired)
  Watchlist  — domain menarik tapi masih aktif/taken, perlu dipantau
  Uncertain  — data belum cukup / status belum yakin
  Discard    — jelas tidak layak (live+registered, toxic, dll)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateDomain
from app.config import get_settings

logger = logging.getLogger(__name__)

# Availability status → score mapping
AVAILABILITY_SCORES = {
    "available": 100,
    "expired": 90,
    "expiring_soon": 70,
    "expiring_watchlist": 50,
    "registered": 10,
    "check_failed": 30,
}


def _score_availability(candidate: CandidateDomain) -> float:
    """Component 1: Availability score (0-100)."""
    return float(AVAILABILITY_SCORES.get(candidate.availability_status or "", 30))


def _score_continuity(candidate: CandidateDomain) -> float:
    """
    Component 2: Continuity score (0-100).
    Sub-components: snapshot quantity, language consistency, content drift.
    """
    # Snapshot quantity (40% of continuity)
    snaps = candidate.wayback_total_snapshots or 0
    if snaps >= 5:
        snap_score = 100
    elif snaps >= 3:
        snap_score = 70
    elif snaps >= 1:
        snap_score = 40
    else:
        snap_score = 0

    # Language consistency (30% of continuity)
    if candidate.dominant_language and candidate.dominant_language != "unknown":
        lang_score = 80
    elif snaps == 0:
        lang_score = 0
    else:
        lang_score = 50

    # Content drift (30% of continuity)
    if snaps == 0:
        drift_score = 0
    elif candidate.content_drift_detected:
        drift_score = 30
    else:
        drift_score = 100

    return snap_score * 0.4 + lang_score * 0.3 + drift_score * 0.3


def _score_cleanliness(toxicity_flags: list[dict]) -> float:
    """
    Component 3: Cleanliness score (0-100).
    Starts at 100, each medium flag -30, any high flag = 0.
    """
    score = 100.0
    for flag in toxicity_flags:
        if flag.get("severity") == "high":
            return 0.0
        score -= 30

    return max(0.0, score)


def _determine_label(candidate: CandidateDomain, total: float,
                     toxicity_flags: list[dict]) -> str:
    """
    Determine label based on domain context, not just score.

    Available  = dead link + (available/expired) — benar-benar bisa dibeli
    Watchlist  = expiring soon/watchlist, atau dead link + registered — pantau
    Uncertain  = data belum cukup (no WHOIS, check_failed, no wayback)
    Discard    = live link + registered, high toxicity, skor sangat rendah
    """
    has_high_toxicity = any(f.get("severity") == "high" for f in toxicity_flags)
    status = candidate.availability_status or ""
    is_dead = candidate.is_dead_link

    # AUTO-DISCARD: high-severity toxicity
    if has_high_toxicity:
        return "Discard"

    # AUTO-DISCARD: link masih live + domain registered (bukan kandidat beli)
    if not is_dead and status == "registered":
        return "Discard"

    # UNCERTAIN: belum ada data WHOIS atau check gagal
    if not status or status == "check_failed":
        return "Uncertain"

    # AVAILABLE: dead link + domain bisa diambil
    if is_dead and status in ("available", "expired"):
        return "Available"

    # AVAILABLE: link down + expiring_soon (sangat dekat expired)
    if is_dead and status == "expiring_soon":
        return "Available"

    # WATCHLIST: domain expiring (tapi belum pasti bisa diambil)
    if status in ("expiring_soon", "expiring_watchlist"):
        return "Watchlist"

    # WATCHLIST: dead link + registered — domain menarik tapi belum bisa dibeli
    if is_dead and status == "registered":
        return "Watchlist"

    # AVAILABLE: not dead but available/expired (rare edge case)
    if status in ("available", "expired"):
        return "Available"

    # Fallback
    if total < 30:
        return "Discard"

    return "Uncertain"


def calculate_score(candidate: CandidateDomain, toxicity_flags: list[dict]) -> dict:
    """
    Calculate final score from three components.
    Returns dict with individual scores, total, label, reason.
    """
    s_avail = _score_availability(candidate)
    s_cont = _score_continuity(candidate)
    s_clean = _score_cleanliness(toxicity_flags)

    total = round(s_avail * 0.3 + s_cont * 0.4 + s_clean * 0.3, 1)

    label = _determine_label(candidate, total, toxicity_flags)

    # Build reason
    reasons = []
    status = candidate.availability_status or "unknown"
    is_dead = candidate.is_dead_link

    # Link status context
    reasons.append("Dead link" if is_dead else "Live link")
    reasons.append(status.replace("_", " ").title())

    snaps = candidate.wayback_total_snapshots or 0
    if snaps > 0:
        years = candidate.wayback_years_active or 0
        reasons.append(f"{years}yr history" if years else f"{snaps} snapshots")

    if candidate.dominant_language and candidate.dominant_language != "unknown":
        reasons.append(candidate.dominant_language.upper())

    has_high_toxicity = any(f.get("severity") == "high" for f in toxicity_flags)
    if has_high_toxicity:
        high_cats = [f["category"] for f in toxicity_flags if f["severity"] == "high"]
        reasons.append("🔴 " + ", ".join(high_cats))
    elif toxicity_flags:
        med_cats = [f["category"] for f in toxicity_flags]
        reasons.append("⚠️ " + ", ".join(med_cats))
    else:
        reasons.append("clean")

    reason = ", ".join(reasons)

    return {
        "score_availability": s_avail,
        "score_continuity": round(s_cont, 1),
        "score_cleanliness": s_clean,
        "score_total": total,
        "label": label,
        "label_reason": reason,
    }


async def score_candidates(db: AsyncSession, source_id: int | None = None,
                           toxicity_map: dict[int, list[dict]] | None = None):
    """
    Score all candidates. If toxicity_map provided, use it;
    otherwise score without toxicity data (clean assumed).
    """
    query = select(CandidateDomain)
    if source_id:
        query = query.where(CandidateDomain.source_id == source_id)

    result = await db.execute(query)
    candidates = result.scalars().all()

    scored = 0
    for candidate in candidates:
        flags = (toxicity_map or {}).get(candidate.id, [])
        scores = calculate_score(candidate, flags)

        candidate.score_availability = scores["score_availability"]
        candidate.score_continuity = scores["score_continuity"]
        candidate.score_cleanliness = scores["score_cleanliness"]
        candidate.score_total = scores["score_total"]
        candidate.label = scores["label"]
        candidate.label_reason = scores["label_reason"]

        scored += 1

    await db.commit()
    logger.info("Scored %d candidates", scored)
    return scored
