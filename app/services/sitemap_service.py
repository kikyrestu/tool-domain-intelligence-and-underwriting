"""
Sitemap + robots.txt Discovery Service.

Supports:
- Parsing sitemap.xml (urlset) directly
- Parsing sitemap index files (sitemapindex) recursively
- Discovering sitemaps from robots.txt Sitemap: directives
- Gzip-compressed sitemaps (.xml.gz)
"""

import gzip
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from app.utils.domain_filter import extract_domain, is_valid_candidate
from app.utils.ssrf_guard import is_safe_url

logger = logging.getLogger(__name__)

_TIMEOUT = 30
_MAX_SITEMAP_URLS = 5000   # cap total page URLs collected per source
_MAX_INDEX_DEPTH = 3       # max recursion into sitemap index files
_MAX_SUB_SITEMAPS = 15     # max sub-sitemaps to follow per index


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------

async def _http_get(url: str) -> bytes:
    """Fetch URL, return raw bytes. Returns b'' on failure."""
    if not is_safe_url(url):
        logger.warning("SSRF guard blocked sitemap fetch: %s", url)
        return b""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DomainIQ/1.0; +sitemap)",
            "Accept": "application/xml,text/xml,*/*",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.content
    except Exception as e:
        logger.debug("Sitemap HTTP GET failed %s: %s", url, e)
    return b""


def _decompress(data: bytes, url: str) -> bytes:
    """Decompress gzip if URL ends with .gz or magic bytes match."""
    if url.endswith(".gz") or (len(data) >= 2 and data[:2] == b"\x1f\x8b"):
        try:
            return gzip.decompress(data)
        except Exception:
            pass
    return data


# ---------------------------------------------------------------------------
# XML parser (no extra deps — uses stdlib ET)
# ---------------------------------------------------------------------------

def _strip_ns(tag: str) -> str:
    """Strip XML namespace prefix: {http://...}urlset → urlset"""
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_sitemap_xml(data: bytes) -> tuple[list[str], list[str]]:
    """
    Parse sitemap XML bytes.
    Returns:
      page_urls     — list of <url><loc> values  (regular sitemap)
      sub_sitemaps  — list of <sitemap><loc> values  (sitemap index)
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        logger.debug("Sitemap XML parse error: %s", e)
        return [], []

    root_tag = _strip_ns(root.tag)
    page_urls: list[str] = []
    sub_sitemaps: list[str] = []

    if root_tag == "sitemapindex":
        for child in root:
            if _strip_ns(child.tag) == "sitemap":
                for loc in child:
                    if _strip_ns(loc.tag) == "loc" and loc.text:
                        sub_sitemaps.append(loc.text.strip())

    elif root_tag == "urlset":
        for child in root:
            if _strip_ns(child.tag) == "url":
                for loc in child:
                    if _strip_ns(loc.tag) == "loc" and loc.text:
                        page_urls.append(loc.text.strip())

    return page_urls, sub_sitemaps


# ---------------------------------------------------------------------------
# Recursive sitemap collector
# ---------------------------------------------------------------------------

async def _collect_sitemap_urls(url: str, depth: int = 0, _seen: set | None = None) -> list[str]:
    """
    Recursively collect all page URLs from a sitemap or sitemap-index.
    Returns at most _MAX_SITEMAP_URLS entries.
    """
    if _seen is None:
        _seen = set()
    if url in _seen or depth > _MAX_INDEX_DEPTH:
        return []
    _seen.add(url)

    data = await _http_get(url)
    if not data:
        return []

    data = _decompress(data, url)
    page_urls, sub_sitemaps = _parse_sitemap_xml(data)

    logger.info("Sitemap[depth=%d] %s: %d pages, %d sub-sitemaps",
                depth, url, len(page_urls), len(sub_sitemaps))

    all_urls = list(page_urls)

    for sub_url in sub_sitemaps[:_MAX_SUB_SITEMAPS]:
        if len(all_urls) >= _MAX_SITEMAP_URLS:
            break
        sub_urls = await _collect_sitemap_urls(sub_url, depth + 1, _seen)
        all_urls.extend(sub_urls)

    return all_urls[:_MAX_SITEMAP_URLS]


# ---------------------------------------------------------------------------
# robots.txt parser
# ---------------------------------------------------------------------------

async def _get_sitemaps_from_robots(url: str) -> list[str]:
    """
    Fetch robots.txt (at root of the given URL's domain) and extract
    all Sitemap: directives.
    """
    parsed = urlparse(url)
    # If the URL itself is robots.txt use it directly, else build root one
    if parsed.path.rstrip("/").endswith("robots.txt"):
        robots_url = url
    else:
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    data = await _http_get(robots_url)
    if not data:
        return []

    sitemaps = []
    for line in data.decode("utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("sitemap:"):
            sm_url = stripped[len("sitemap:"):].strip()
            if sm_url.startswith("http"):
                sitemaps.append(sm_url)

    logger.info("robots.txt %s: found %d sitemap(s)", robots_url, len(sitemaps))
    return sitemaps


# ---------------------------------------------------------------------------
# Shared domain extraction helper
# ---------------------------------------------------------------------------

def _urls_to_links(urls: list[str], source_domain: str) -> list[tuple[str, str]]:
    """Convert raw URL list to valid (url, domain) candidate tuples."""
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for url in urls:
        domain = extract_domain(url)
        if not domain or domain == source_domain:
            continue
        if not is_valid_candidate(domain):
            continue
        if domain in seen:
            continue
        seen.add(domain)
        results.append((url, domain))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_links_from_sitemap(sitemap_url: str) -> list[tuple[str, str]]:
    """
    Fetch and parse a sitemap URL (regular or index).
    Returns list of (page_url, domain) tuples for candidates.
    """
    source_domain = extract_domain(sitemap_url) or ""
    urls = await _collect_sitemap_urls(sitemap_url)
    links = _urls_to_links(urls, source_domain)
    logger.info("Sitemap discovery: %d page URLs → %d unique candidate domains from %s",
                len(urls), len(links), sitemap_url)
    return links


async def fetch_links_from_robots(robots_url: str) -> list[tuple[str, str]]:
    """
    Fetch robots.txt, discover all sitemap URLs, crawl them all,
    and return (page_url, domain) tuples for candidates.
    """
    source_domain = extract_domain(robots_url) or ""
    sitemap_urls = await _get_sitemaps_from_robots(robots_url)

    all_urls: list[str] = []
    seen_sitemaps: set[str] = set()
    for sm_url in sitemap_urls[:10]:
        if len(all_urls) >= _MAX_SITEMAP_URLS:
            break
        sub = await _collect_sitemap_urls(sm_url, _seen=seen_sitemaps)
        all_urls.extend(sub)

    links = _urls_to_links(all_urls, source_domain)
    logger.info("robots.txt discovery: %d total URLs → %d unique candidate domains from %s",
                len(all_urls), len(links), robots_url)
    return links
