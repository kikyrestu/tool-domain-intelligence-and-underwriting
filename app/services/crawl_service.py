"""
Crawl Service — fetch source page, extract outbound links, check domain
liveness (DNS + HTTP root), filter domains, and save candidates to DB.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import dns.asyncresolver
import dns.exception
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

TIMEOUT = 20
MAX_CONCURRENT = 5

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def _make_client() -> httpx.AsyncClient:
    """Create an httpx client with optional proxy."""
    proxy = proxy_service.get_next()
    return httpx.AsyncClient(proxy=proxy, headers=_get_headers(), follow_redirects=True)


async def _fetch_page(url: str) -> str | None:
    """Fetch a page with proxy, fallback to direct if proxy fails.

    Uses HTTP/2 by default — many sites (Wikipedia, etc.) require it.
    Accepts any response that contains HTML content, even 403/404.
    """
    # Try with proxy first
    proxy = proxy_service.get_next()
    if proxy:
        try:
            async with httpx.AsyncClient(proxy=proxy, headers=_get_headers(),
                                         follow_redirects=True, http2=True) as client:
                resp = await client.get(url, timeout=TIMEOUT)
                if len(resp.text) > 500:
                    return resp.text
                resp.raise_for_status()
                return resp.text
        except Exception:
            logger.debug("Proxy failed for %s, trying direct", url)

    # Fallback to direct
    try:
        async with httpx.AsyncClient(headers=_get_headers(),
                                     follow_redirects=True, http2=True) as client:
            resp = await client.get(url, timeout=TIMEOUT)
            if len(resp.text) > 500:
                return resp.text
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


async def _check_domain(domain: str, semaphore: asyncio.Semaphore) -> dict:
    """Check if a DOMAIN is alive by checking DNS + HTTP root.
    If domain is dead, immediately check RDAP for buy availability.

    Returns dict with:
      - dns_resolves: bool — does the domain have A/AAAA records?
      - http_status: int|None — status code of GET https://domain/
      - is_domain_alive: bool — combined verdict
      - availability_status: str|None — RDAP result for dead domains
      - whois_registrar: str|None
      - whois_created_date: date|None
      - whois_expiry_date: date|None
      - whois_days_left: int|None
    """
    from app.services.whois_service import _rdap_lookup

    # HTTP status codes that mean server is alive (even if blocking)
    ALIVE_STATUSES = {200, 201, 204, 301, 302, 303, 307, 308,
                      401, 402, 403, 405, 407, 429}

    result = {"dns_resolves": False, "http_status": None, "is_domain_alive": False,
              "availability_status": None, "whois_registrar": None,
              "whois_created_date": None, "whois_expiry_date": None,
              "whois_days_left": None}

    async with semaphore:
        # --- Layer 1: DNS Resolution ---
        try:
            answers = await dns.asyncresolver.resolve(domain, "A")
            if answers:
                result["dns_resolves"] = True
        except (dns.exception.DNSException, Exception):
            pass

        if not result["dns_resolves"]:
            try:
                answers = await dns.asyncresolver.resolve(domain, "AAAA")
                if answers:
                    result["dns_resolves"] = True
            except (dns.exception.DNSException, Exception):
                pass

        # No DNS = domain is truly dead → check if buyable
        if not result["dns_resolves"]:
            rdap = await _rdap_lookup(domain)
            result["availability_status"] = rdap["status"]
            result["whois_registrar"] = rdap.get("registrar")
            result["whois_created_date"] = rdap.get("created_date")
            result["whois_expiry_date"] = rdap.get("expiry_date")
            result["whois_days_left"] = rdap.get("days_left")
            logger.info("  Dead domain %s → RDAP: %s", domain, rdap["status"])
            return result

        # --- Layer 2: HTTP root domain check ---
        root_url = f"https://{domain}/"
        if not is_safe_url(root_url):
            result["is_domain_alive"] = True  # DNS resolves, assume alive
            return result

        # Try HTTPS first
        for url in [f"https://{domain}/", f"http://{domain}/"]:
            try:
                async with httpx.AsyncClient(headers=_get_headers(),
                                             follow_redirects=True, http2=True) as client:
                    resp = await client.get(url, timeout=TIMEOUT)
                    result["http_status"] = resp.status_code
                    result["is_domain_alive"] = resp.status_code in ALIVE_STATUSES
                    if not result["is_domain_alive"]:
                        # Server responds but with error → dead, check buyable
                        rdap = await _rdap_lookup(domain)
                        result["availability_status"] = rdap["status"]
                        result["whois_registrar"] = rdap.get("registrar")
                        result["whois_created_date"] = rdap.get("created_date")
                        result["whois_expiry_date"] = rdap.get("expiry_date")
                        result["whois_days_left"] = rdap.get("days_left")
                        logger.info("  Dead domain %s (HTTP %s) → RDAP: %s", domain, resp.status_code, rdap["status"])
                    return result
            except Exception:
                continue

        # DNS resolves but HTTP completely failed → dead, check buyable
        result["is_domain_alive"] = False
        rdap = await _rdap_lookup(domain)
        result["availability_status"] = rdap["status"]
        result["whois_registrar"] = rdap.get("registrar")
        result["whois_created_date"] = rdap.get("created_date")
        result["whois_expiry_date"] = rdap.get("expiry_date")
        result["whois_days_left"] = rdap.get("days_left")
        logger.info("  Dead domain %s (HTTP fail) → RDAP: %s", domain, rdap["status"])
        return result


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

        # 3. Check domains concurrently (using ROOT domain, not specific URL)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        # Deduplicate domains for checking (avoid checking same domain twice)
        unique_domains = list({domain for _, domain in links})
        check_tasks = [_check_domain(d, semaphore) for d in unique_domains]
        check_results = await asyncio.gather(*check_tasks)
        domain_status = dict(zip(unique_domains, check_results))

        # 4. Save candidates
        dead_count = 0
        saved = 0
        for (url, domain) in links:
            status = domain_status[domain]
            if not status["is_domain_alive"]:
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
                http_status=status["http_status"],
                dns_resolves=status["dns_resolves"],
                is_domain_alive=status["is_domain_alive"],
                availability_status=status.get("availability_status"),
                whois_registrar=status.get("whois_registrar"),
                whois_created_date=status.get("whois_created_date"),
                whois_expiry_date=status.get("whois_expiry_date"),
                whois_days_left=status.get("whois_days_left"),
                whois_checked_at=datetime.now(timezone.utc) if status.get("availability_status") else None,
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
