"""
Certificate Transparency Log Discovery via crt.sh public API.

Usage:
  - Add a source with URL:  crtsh://technology
  - On crawl, the system queries https://crt.sh/?q=%technology%&output=json
  - All valid domain names from issued certificates are returned as candidates.

No API key required. Free public API.
Rate limit: ~1 req/sec recommended.
"""

import logging
import re

import httpx

from app.utils.domain_filter import extract_domain, is_valid_candidate

logger = logging.getLogger(__name__)

_CRTSH_URL = "https://crt.sh/"
_TIMEOUT = 45
_MAX_RESULTS = 2000


def parse_crtsh_keyword(source_url: str) -> str | None:
    """
    Extract keyword from a crtsh:// synthetic source URL.
    e.g.  crtsh://technology    → 'technology'
          crtsh://health+blog   → 'health blog'
    Returns None if URL does not match crtsh:// scheme.
    """
    if source_url.lower().startswith("crtsh://"):
        return source_url[len("crtsh://"):].strip().replace("+", " ")
    return None


# Simple domain label regex: allows letters, digits, hyphens
_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)"
    r"+[a-zA-Z]{2,}$"
)


async def fetch_domains_from_crtsh(keyword: str) -> list[tuple[str, str]]:
    """
    Query crt.sh for all certificates whose Subject/SAN contains *keyword*.
    Returns list of (url, domain) tuples — each domain appears at most once.

    keyword: plain string, % wildcards are added automatically.
    """
    q = f"%{keyword}%" if "%" not in keyword else keyword

    logger.info("crt.sh query: q=%s", q)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=_TIMEOUT) as client:
            resp = await client.get(
                _CRTSH_URL,
                params={"q": q, "output": "json"},
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; DomainIQ/1.0; +crt.sh)",
                    "Accept": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.warning("crt.sh returned HTTP %d for q=%s", resp.status_code, q)
            return []

        data = resp.json()

    except Exception as e:
        logger.error("crt.sh API error for q=%s: %s", q, e)
        return []

    results: list[tuple[str, str]] = []
    seen_domains: set[str] = set()

    for entry in data:
        # name_value can be a single name or newline-separated list of SANs
        raw = (entry.get("name_value") or "") + "\n" + (entry.get("common_name") or "")
        for name in raw.splitlines():
            name = name.strip().lstrip("*.")   # strip wildcard prefix (* .)
            if not name or " " in name:
                continue
            if not _DOMAIN_RE.match(name):
                continue
            domain = extract_domain(name)
            if not domain:
                continue
            if not is_valid_candidate(domain):
                continue
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            results.append((f"https://{domain}/", domain))
            if len(results) >= _MAX_RESULTS:
                break

        if len(results) >= _MAX_RESULTS:
            break

    logger.info("crt.sh '%s': %d certificate entries → %d unique valid domains",
                keyword, len(data), len(results))
    return results
