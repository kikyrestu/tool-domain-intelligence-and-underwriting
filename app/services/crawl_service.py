"""
Crawl Service — fetch source page, extract outbound links, detect dead links,
filter domains, and save candidates to DB.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.models.crawl_job import CrawlJob
from app.models.candidate import CandidateDomain
from app.services.proxy_service import proxy_service
from app.utils.ssrf_guard import is_safe_url
from app.utils.domain_filter import extract_domain, is_valid_candidate, BLACKLIST
from app.config import get_settings

logger = logging.getLogger(__name__)

TIMEOUT = 15
MAX_CONCURRENT = 5

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def _make_client() -> httpx.AsyncClient:
    """Create an httpx client with optional proxy."""
    proxy = proxy_service.get_next()
    return httpx.AsyncClient(proxy=proxy, headers=_get_headers(), follow_redirects=True)


async def _fetch_page(url: str) -> str | None:
    """Fetch a page with proxy, fallback to direct if proxy fails."""
    # Try with proxy first
    proxy = proxy_service.get_next()
    if proxy:
        try:
            async with httpx.AsyncClient(proxy=proxy, headers=_get_headers(), follow_redirects=True) as client:
                resp = await client.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                return resp.text
        except Exception:
            logger.debug("Proxy failed for %s, trying direct", url)

    # Fallback to direct
    try:
        async with httpx.AsyncClient(headers=_get_headers(), follow_redirects=True) as client:
            resp = await client.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None


def _extract_outbound_links(html: str, source_url: str) -> list[tuple[str, str]]:
    """Extract outbound links from HTML. Returns list of (url, domain)."""
    soup = BeautifulSoup(html, "html.parser")
    source_domain = extract_domain(source_url)

    results = []
    seen_domains = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        full_url = urljoin(source_url, href)
        parsed = urlparse(full_url)
        if parsed.scheme not in ("http", "https"):
            continue

        domain = extract_domain(full_url)
        if not domain or domain == source_domain:
            continue
        if not is_valid_candidate(domain):
            continue
        if domain in seen_domains:
            continue

        seen_domains.add(domain)
        results.append((full_url, domain))

    return results


async def _check_link(url: str, semaphore: asyncio.Semaphore) -> tuple[int | None, bool]:
    """Check if a link is dead. Returns (http_status, is_dead).

    A link is dead when:
    - Connection/DNS fails entirely (timeout, refused, DNS error)
    - Server returns 404, 410, or 5xx
    A link is alive when:
    - Server responds with 2xx/3xx
    - Server returns 403 (bot-protection like Cloudflare — site is live)
    """
    # Status codes that indicate the server is alive even if access is denied
    ALIVE_STATUSES = {401, 402, 403, 405, 407, 429}

    if not is_safe_url(url):
        return None, False

    async with semaphore:
        proxy = proxy_service.get_random()
        try:
            async with httpx.AsyncClient(proxy=proxy, headers=_get_headers(), follow_redirects=True) as client:
                resp = await client.head(url, timeout=TIMEOUT)
                if resp.status_code in (403, 405):
                    resp = await client.get(url, timeout=TIMEOUT)
                status = resp.status_code
                is_dead = status >= 400 and status not in ALIVE_STATUSES
                return status, is_dead
        except Exception:
            pass

        # Fallback direct
        try:
            async with httpx.AsyncClient(headers=_get_headers(), follow_redirects=True) as client:
                resp = await client.head(url, timeout=TIMEOUT)
                if resp.status_code in (403, 405):
                    resp = await client.get(url, timeout=TIMEOUT)
                status = resp.status_code
                is_dead = status >= 400 and status not in ALIVE_STATUSES
                return status, is_dead
        except Exception:
            return None, True  # Timeout/connection error → dead


async def run_crawl(source_id: int, db: AsyncSession):
    """
    Main crawl pipeline:
    1. Create CrawlJob
    2. Fetch source page
    3. Extract + filter outbound links
    4. Check dead links
    5. Save candidates to DB
    6. Update CrawlJob stats
    """
    settings = get_settings()

    # Get source
    source = await db.get(Source, source_id)
    if not source:
        raise ValueError(f"Source {source_id} not found")

    # Create crawl job
    job = CrawlJob(source_id=source_id, status="running", started_at=datetime.now(timezone.utc))
    db.add(job)
    await db.flush()

    try:
        # 1. Fetch source page
        html = await _fetch_page(source.url)
        if not html:
            job.status = "failed"
            job.error_message = "Failed to fetch source page"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return job

        # 2. Extract outbound links
        links = _extract_outbound_links(html, source.url)
        links = links[:settings.MAX_CANDIDATES_PER_CRAWL]
        job.total_links_found = len(links)

        # 3. Check dead links concurrently
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        check_tasks = [_check_link(url, semaphore) for url, _ in links]
        results = await asyncio.gather(*check_tasks)

        # 4. Save candidates
        dead_count = 0
        saved = 0
        for (url, domain), (http_status, is_dead) in zip(links, results):
            if is_dead:
                dead_count += 1

            # Check if domain already exists for this source
            existing = await db.execute(
                select(CandidateDomain).where(
                    CandidateDomain.domain == domain,
                    CandidateDomain.source_id == source_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            candidate = CandidateDomain(
                domain=domain,
                source_id=source_id,
                crawl_job_id=job.id,
                source_url_found=source.url,
                original_link=url,
                niche=source.niche,
                http_status=http_status,
                is_dead_link=is_dead,
            )
            db.add(candidate)
            saved += 1

        job.total_candidates = saved
        job.total_dead_links = dead_count
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info("Crawl completed: %d candidates, %d dead links", saved, dead_count)
        return job

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.error("Crawl failed: %s", e)
        return job
