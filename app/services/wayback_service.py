"""
Wayback Machine service — CDX snapshot retrieval, content analysis,
language detection, and content drift measurement.
"""

import asyncio
import logging
import re
from datetime import datetime, date, timezone

import httpx
from langdetect import detect, LangDetectException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateDomain
from app.config import get_settings
from app.services.proxy_service import ProxyService

logger = logging.getLogger(__name__)

WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"
WAYBACK_WEB_URL = "https://web.archive.org/web"
TIMEOUT = 30


async def _get_snapshots(domain: str, client: httpx.AsyncClient) -> list[dict]:
    """Fetch snapshot list from Wayback CDX API."""
    params = {
        "url": domain,
        "output": "json",
        "fl": "timestamp,statuscode,mimetype,original",
        "filter": "statuscode:200",
        "collapse": "timestamp:6",  # 1 per month
        "limit": 50,
    }
    try:
        resp = await client.get(WAYBACK_CDX_URL, params=params, timeout=TIMEOUT, follow_redirects=True)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if not data or len(data) < 2:
            return []
        headers = data[0]
        return [dict(zip(headers, row)) for row in data[1:]]
    except Exception as e:
        logger.warning("CDX API error for %s: %s", domain, e)
        return []


def _select_snapshots(snapshots: list[dict], count: int = 5) -> list[dict]:
    """Pick evenly-spaced snapshots from timeline."""
    if len(snapshots) <= count:
        return snapshots
    indices = [0]
    step = (len(snapshots) - 1) / (count - 1)
    for i in range(1, count - 1):
        indices.append(round(step * i))
    indices.append(len(snapshots) - 1)
    return [snapshots[i] for i in indices]


async def _fetch_content(domain: str, timestamp: str, client: httpx.AsyncClient) -> str | None:
    """Fetch snapshot content from Wayback Machine."""
    url = f"{WAYBACK_WEB_URL}/{timestamp}id_/{domain}"
    try:
        resp = await client.get(url, timeout=TIMEOUT, follow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def _extract_text(html: str) -> str:
    """Extract visible text from HTML."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _detect_language(text: str) -> str:
    """Detect language from text. Returns ISO 639-1 code or 'unknown'."""
    if not text or len(text) < 50:
        return "unknown"
    try:
        return detect(text[:5000])
    except LangDetectException:
        return "unknown"


def _content_drift(texts: list[str]) -> bool:
    """
    Detect content drift by comparing keyword overlap between first and last
    substantial snapshots. Returns True if significant drift detected.
    """
    substantial = [t for t in texts if len(t) > 100]
    if len(substantial) < 2:
        return False

    def keywords(t: str) -> set[str]:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', t.lower())
        return set(words[:200])

    first_kw = keywords(substantial[0])
    last_kw = keywords(substantial[-1])

    if not first_kw or not last_kw:
        return False

    overlap = len(first_kw & last_kw) / max(len(first_kw | last_kw), 1)
    return overlap < 0.2  # Less than 20% overlap = drift


async def analyze_domain(domain: str) -> dict:
    """
    Full Wayback analysis for a single domain.
    Returns dict with snapshot data, language, drift info.
    """
    settings = get_settings()
    proxy_svc = ProxyService()

    transport_kwargs = {}
    if settings.PROXY_ENABLED and proxy_svc.proxies:
        proxy_url = proxy_svc.get_next()
        if proxy_url:
            transport_kwargs["proxy"] = proxy_url

    async with httpx.AsyncClient(**transport_kwargs) as client:
        # Get all snapshots
        all_snapshots = await _get_snapshots(domain, client)

        result = {
            "total_snapshots": len(all_snapshots),
            "first_seen": None,
            "last_seen": None,
            "years_active": None,
            "dominant_language": None,
            "content_drift": False,
            "snapshot_details": [],
        }

        if not all_snapshots:
            return result

        # Timeline info
        first_ts = all_snapshots[0]["timestamp"]
        last_ts = all_snapshots[-1]["timestamp"]
        try:
            result["first_seen"] = date(int(first_ts[:4]), int(first_ts[4:6]), int(first_ts[6:8]))
            result["last_seen"] = date(int(last_ts[:4]), int(last_ts[4:6]), int(last_ts[6:8]))
            result["years_active"] = int(last_ts[:4]) - int(first_ts[:4])
        except (ValueError, IndexError):
            pass

        # Select and analyze key snapshots
        selected = _select_snapshots(all_snapshots, settings.WAYBACK_SAMPLE_SIZE)
        texts = []

        for snap in selected:
            ts = snap["timestamp"]
            content = await _fetch_content(domain, ts, client)
            detail = {"timestamp": ts, "language": "unknown", "content_length": 0}

            if content:
                text = _extract_text(content)
                detail["content_length"] = len(text)
                detail["language"] = _detect_language(text)
                texts.append(text)

            result["snapshot_details"].append(detail)
            await asyncio.sleep(settings.WAYBACK_DELAY_SECONDS)

        # Dominant language
        langs = [d["language"] for d in result["snapshot_details"] if d["language"] != "unknown"]
        if langs:
            result["dominant_language"] = max(set(langs), key=langs.count)

        # Content drift
        result["content_drift"] = _content_drift(texts)

    return result


async def check_single(domain: str) -> dict:
    """Async convenience wrapper."""
    return await analyze_domain(domain)


async def check_candidates(db: AsyncSession, source_id: int | None = None):
    """
    Batch Wayback check for all candidates that haven't been checked yet.
    Updates DB directly.
    """
    query = select(CandidateDomain).where(CandidateDomain.wayback_checked_at.is_(None))
    if source_id:
        query = query.where(CandidateDomain.source_id == source_id)

    result = await db.execute(query)
    candidates = result.scalars().all()

    if not candidates:
        logger.info("No unchecked candidates for Wayback")
        return 0

    logger.info("Starting Wayback check for %d candidates", len(candidates))
    checked = 0

    for candidate in candidates:
        try:
            data = await analyze_domain(candidate.domain)

            candidate.wayback_total_snapshots = data["total_snapshots"]
            candidate.wayback_first_seen = data.get("first_seen")
            candidate.wayback_last_seen = data.get("last_seen")
            candidate.wayback_years_active = data.get("years_active")
            candidate.dominant_language = data.get("dominant_language")
            candidate.content_drift_detected = data.get("content_drift", False)
            candidate.wayback_checked_at = datetime.now(timezone.utc)

            checked += 1
            logger.info("Wayback [%d/%d] %s: %d snapshots, lang=%s",
                        checked, len(candidates), candidate.domain,
                        data["total_snapshots"], data.get("dominant_language"))

        except Exception as e:
            logger.error("Wayback error for %s: %s", candidate.domain, e)
            candidate.wayback_checked_at = datetime.now(timezone.utc)

        await db.commit()

    logger.info("Wayback check complete: %d/%d", checked, len(candidates))
    return checked
