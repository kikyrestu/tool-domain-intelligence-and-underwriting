"""
Wayback Machine service — CDX snapshot retrieval, content analysis,
language detection, and content drift measurement.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, date, timezone
from urllib.parse import urlparse

import httpx
import tldextract
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateDomain
from app.models.source import Source
from app.config import get_settings
from app.services.proxy_service import ProxyService
from app.services.toxicity_service import scan_candidate
from app.utils.ssrf_guard import is_safe_url
from app.utils.domain_filter import is_valid_candidate

logger = logging.getLogger(__name__)

WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"
WAYBACK_WEB_URL = "https://web.archive.org/web"
TIMEOUT = 30


async def _get_snapshots(domain: str, client: httpx.AsyncClient) -> list[dict]:
    """Fetch snapshot list from Wayback CDX API.

    Primary query: statuscode:200 only.
    Fallback query (no statuscode filter): used when primary returns 0 results,
    because some domains only have redirect (301/302) snapshots archived.
    """
    base_params = {
        "url": domain,
        "output": "json",
        "fl": "timestamp,statuscode,mimetype,original",
        "collapse": "timestamp:6",  # 1 per month
        "limit": 50,
    }

    async def _fetch_cdx(params: dict) -> list[dict]:
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

    # Primary: only successful page loads
    snapshots = await _fetch_cdx({**base_params, "filter": "statuscode:200"})
    if snapshots:
        return snapshots

    # Fallback: include 301/302 redirects — domain may have only redirected historically
    logger.debug("CDX primary (statuscode:200) returned 0 for %s — retrying without statuscode filter", domain)
    snapshots = await _fetch_cdx(base_params)
    return snapshots


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
    """Fetch snapshot content from Wayback Machine. Retries once on failure."""
    url = f"{WAYBACK_WEB_URL}/{timestamp}id_/{domain}"
    for attempt in range(2):
        try:
            resp = await client.get(url, timeout=TIMEOUT, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        if attempt == 0:
            await asyncio.sleep(2)  # brief backoff before retry
    return None


def _extract_text(html: str) -> str:
    """Extract visible text from HTML."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_outbound_domains(html: str, current_domain: str) -> set[str]:
    """Extract unique outbound root domains from snapshot HTML (excludes current domain and Wayback wrapper URLs)."""
    found: set[str] = set()
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            # Strip Wayback wrapper prefix (e.g. /web/20050101000000id_/https://...)
            if href.startswith("/web/"):
                m = re.search(r'/web/\d+(?:id_)?/(https?://.+)', href)
                if m:
                    href = m.group(1)
            try:
                parsed = urlparse(href if href.startswith("http") else f"https://{href}")
                # Use parsed.hostname to strip userinfo (user:pass@) and port — prevents
                # mailto:user@domain.com leaking through as a netloc candidate.
                hostname = (parsed.hostname or "").lower().lstrip("www.")
                if not hostname or hostname == current_domain.lower().lstrip("www."):
                    continue
                # Validate TLD — filters .php, .html, .aspx, .asp, etc.
                if not is_valid_candidate(hostname):
                    continue
                candidate_url = f"https://{hostname}/"
                if is_safe_url(candidate_url):
                    found.add(hostname)
            except Exception:
                continue
    except Exception:
        pass
    return found


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
            # Minimum 1 so "has history in one year" is distinguishable from "no history" (None)
            result["years_active"] = max(1, int(last_ts[:4]) - int(first_ts[:4]))
        except (ValueError, IndexError):
            pass

        # Select and analyze key snapshots
        selected = _select_snapshots(all_snapshots, settings.WAYBACK_SAMPLE_SIZE)
        texts = []
        discovered_domains: set[str] = set()

        for snap in selected:
            ts = snap["timestamp"]
            content = await _fetch_content(domain, ts, client)
            detail = {"timestamp": ts, "language": "unknown", "content_length": 0}

            if content:
                text = _extract_text(content)
                detail["content_length"] = len(text)
                detail["language"] = _detect_language(text)
                texts.append(text)
                # Collect outbound domains from this snapshot (Layer 4b)
                discovered_domains |= _extract_outbound_domains(content, domain)

            result["snapshot_details"].append(detail)
            await asyncio.sleep(settings.WAYBACK_DELAY_SECONDS)

        # Dominant language
        langs = [d["language"] for d in result["snapshot_details"] if d["language"] != "unknown"]
        if langs:
            result["dominant_language"] = max(set(langs), key=langs.count)

        # Content drift
        result["content_drift"] = _content_drift(texts)

        # Return snapshot texts so caller can run toxicity scan
        result["snapshot_texts"] = texts

        # Return collected outbound domains for source auto-creation
        result["discovered_domains"] = discovered_domains

    return result


async def check_single(domain: str) -> dict:
    """Async convenience wrapper."""
    return await analyze_domain(domain)


async def check_candidates(db: AsyncSession, source_id: int | None = None, candidate_ids: list[int] | None = None):
    """
    Batch Wayback check for candidates that:
    - have never been checked (wayback_checked_at IS NULL), OR
    - previously failed (wayback_check_failed = True)
    Updates DB directly.
    """
    from sqlalchemy import or_
    query = select(CandidateDomain).where(
        or_(
            CandidateDomain.wayback_checked_at.is_(None),
            CandidateDomain.wayback_check_failed == True,
        )
    )
    if candidate_ids:
        query = query.where(CandidateDomain.id.in_(candidate_ids))
    elif source_id:
        query = query.where(CandidateDomain.source_id == source_id)

    result = await db.execute(query)
    candidates = result.scalars().all()

    if not candidates:
        logger.info("No unchecked candidates for Wayback")
        return 0

    logger.info("Starting Wayback check for %d candidates", len(candidates))
    checked = 0
    new_sources = 0

    for candidate in candidates:
        try:
            data = await analyze_domain(candidate.domain)

            candidate.wayback_total_snapshots = data["total_snapshots"]
            candidate.wayback_first_seen = data.get("first_seen")
            candidate.wayback_last_seen = data.get("last_seen")
            candidate.wayback_years_active = data.get("years_active")
            candidate.dominant_language = data.get("dominant_language")
            candidate.content_drift_detected = data.get("content_drift", False)

            snapshot_texts = data.get("snapshot_texts", [])

            # If CDX found snapshots but all individual fetches failed, mark for retry
            if data["total_snapshots"] > 0 and not snapshot_texts:
                logger.warning("Wayback %s: %d CDX snapshots but 0 fetched — will retry",
                               candidate.domain, data["total_snapshots"])
                candidate.wayback_check_failed = True
                await db.commit()
                continue

            candidate.wayback_checked_at = datetime.now(timezone.utc)
            candidate.wayback_check_failed = False

            # Run toxicity scan with real snapshot texts and persist to DB
            flags = scan_candidate(candidate, snapshot_texts)
            candidate.toxicity_flags = json.dumps(flags)

            checked += 1
            logger.info("Wayback [%d/%d] %s: %d snapshots, lang=%s, toxicity=%d flags, discovered=%d",
                        checked, len(candidates), candidate.domain,
                        data["total_snapshots"], data.get("dominant_language"),
                        len(flags), len(data.get("discovered_domains", set())))

            # --- Layer 4b: save discovered outbound domains as suggested_candidates ---
            from app.models.suggested_candidate import SuggestedCandidate
            from app.models.candidate import CandidateDomain as _CD
            for disc_domain in data.get("discovered_domains", set()):
                # Normalize to registered root domain — strips subdomains (blog.x.com → x.com)
                ext = tldextract.extract(disc_domain)
                if not ext.domain or not ext.suffix:
                    continue
                root_domain = f"{ext.domain}.{ext.suffix}"

                # Skip if already a live candidate
                existing_cand = await db.execute(
                    select(_CD).where(_CD.domain == root_domain)
                )
                if existing_cand.scalar_one_or_none() is not None:
                    continue
                # Skip if already suggested
                existing_sug = await db.execute(
                    select(SuggestedCandidate).where(SuggestedCandidate.domain == root_domain)
                )
                if existing_sug.scalar_one_or_none() is None:
                    db.add(SuggestedCandidate(
                        domain=root_domain,
                        discovered_from=candidate.domain,
                        niche=candidate.niche or "General",
                        discovery_source="wayback",
                    ))
                    new_sources += 1
                    logger.info("  [Wayback] Suggested candidate: %s (from %s)", root_domain, candidate.domain)

        except Exception as e:
            logger.error("Wayback error for %s: %s", candidate.domain, e)
            # Mark as failed (not as checked) so it will be retried next run
            candidate.wayback_check_failed = True

        await db.commit()

    logger.info("Wayback check complete: %d/%d candidates, %d new sources discovered",
                checked, len(candidates), new_sources)
    return checked
