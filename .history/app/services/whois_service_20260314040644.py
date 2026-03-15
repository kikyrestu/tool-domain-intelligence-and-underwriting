"""
RDAP Service — domain availability check via RDAP protocol (ICANN standard).

Uses IANA bootstrap (data.iana.org/rdap/dns.json) to find the authoritative
RDAP server for ANY TLD automatically, then falls back to rdap.org.
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

# IANA RDAP bootstrap — cached at module level after first fetch
# Maps TLD -> list of RDAP base URLs
_BOOTSTRAP_CACHE: dict[str, list[str]] = {}
_BOOTSTRAP_LOADED = False
_BOOTSTRAP_LOCK = asyncio.Lock()

# Hard-coded fallbacks for common ccTLDs (used before bootstrap loads)
_CCTLD_RDAP = {
    "me": "https://rdap.nic.me/domain",
    "io": "https://rdap.nic.io/domain",
    "ai": "https://rdap.nic.ai/domain",
    "co": "https://rdap.nic.co/domain",
    "app": "https://rdap.nic.google/domain",
    "dev": "https://rdap.nic.google/domain",
    "ly": "https://rdap.lydomains.com/domain",
    "tv": "https://rdap.verisign.com/tv/v1/domain",
    "cc": "https://rdap.verisign.com/cc/v1/domain",
    "sh": "https://rdap.nic.sh/domain",
    "ac": "https://rdap.nic.ac/domain",
    "fm": "https://rdap.nic.fm/domain",
    "gg": "https://rdap.gg/domain",
    "je": "https://rdap.je/domain",
    "im": "https://rdap.im/domain",
    "ws": "https://rdap.nic.ws/domain",
    "ag": "https://rdap.nic.ag/domain",
    "sc": "https://rdap.nic.sc/domain",
    "ms": "https://rdap.nic.ms/domain",
    "tc": "https://rdap.nic.tc/domain",
    "vg": "https://rdap.nic.vg/domain",
    "ky": "https://rdap.nic.ky/domain",
    "bz": "https://rdap.nic.bz/domain",
    "lc": "https://rdap.nic.lc/domain",
    "vc": "https://rdap.nic.vc/domain",
    "mn": "https://rdap.nic.mn/domain",
    "so": "https://rdap.nic.so/domain",
    "id": "https://rdap.id/domain",
    "my": "https://rdap.mynic.my/domain",
    "sg": "https://rdap.sgnic.sg/domain",
    "com.au": "https://rdap.auda.org.au/domain",
    "net.au": "https://rdap.auda.org.au/domain",
    "ch": "https://rdap.nic.ch/domain",
    "li": "https://rdap.nic.li/domain",
    "at": "https://rdap.nic.at/domain",
    "nl": "https://rdap.sidn.nl/domain",
    "de": "https://rdap.denic.de/domain",
    "fr": "https://rdap.nic.fr/domain",
    "be": "https://rdap.dnsbelgium.be/domain",
    "nu": "https://rdap.nic.nu/domain",
    "se": "https://rdap.iis.se/domain",
    "no": "https://rdap.norid.no/domain",
    "dk": "https://rdap.dk-hostmaster.dk/domain",
    "fi": "https://rdap.ficora.fi/domain",
    "uk": "https://rdap.nominet.uk/domain",
    "to": "https://rdap.tonic.to/domain",
    "la": "https://rdap.nic.la/domain",
    "pe": "https://rdap.nic.pe/domain",
    "mx": "https://rdap.mx/domain",
    "br": "https://rdap.registro.br/domain",
    "ca": "https://rdap.cira.ca/domain",
    "nz": "https://rdap.srs.net.nz/domain",
    "in": "https://rdap.registry.in/domain",
    "ru": "https://rdap.tcinet.ru/domain",
    "is": "https://rdap.isnic.is/domain",
    "pw": "https://rdap.nic.pw/domain",
    "click": "https://rdap.namecheap.com/domain",
    "link": "https://rdap.uniregistry.net/domain",
    "blog": "https://rdap.donuts.co/domain",
    "online": "https://rdap.centralnic.com/domain",
    "site": "https://rdap.centralnic.com/domain",
    "store": "https://rdap.centralnic.com/domain",
    "tech": "https://rdap.centralnic.com/domain",
    "space": "https://rdap.centralnic.com/domain",
    "fun": "https://rdap.centralnic.com/domain",
    "press": "https://rdap.centralnic.com/domain",
    "host": "https://rdap.centralnic.com/domain",
    "website": "https://rdap.centralnic.com/domain",
}

# gTLDs that rdap.org handles reliably — skip bootstrap for these
_GTLD_RDAP_OK = {
    "com", "net", "org", "info", "biz", "name", "pro", "mobi", "tel", "coop",
    "aero", "museum", "travel", "xxx", "edu", "gov", "mil", "int",
    "xyz", "club", "top", "win", "vip", "one", "live", "world", "today",
    "news", "media", "digital", "studio", "network", "group", "plus",
}


async def _load_iana_bootstrap() -> None:
    """Fetch IANA RDAP bootstrap data and cache it (called once per process)."""
    global _BOOTSTRAP_LOADED
    async with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP_LOADED:
            return
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(
                    "https://data.iana.org/rdap/dns.json",
                    timeout=10,
                )
            if resp.status_code == 200:
                data = resp.json()
                for service in data.get("services", []):
                    tld_list, url_list = service[0], service[1]
                    if not url_list:
                        continue
                    base = url_list[0].rstrip("/") + "/domain"
                    for tld in tld_list:
                        _BOOTSTRAP_CACHE[tld.lower().strip(".")] = base
                logger.info("[RDAP] IANA bootstrap loaded: %d TLDs cached", len(_BOOTSTRAP_CACHE))
        except Exception as e:
            logger.warning("[RDAP] IANA bootstrap fetch failed: %s — using fallback table", e)
        _BOOTSTRAP_LOADED = True


async def _find_rdap_endpoint(tld: str) -> str | None:
    """Find authoritative RDAP endpoint for a TLD. Returns base URL or None."""
    # 1. Hard-coded table (fastest)
    if tld in _CCTLD_RDAP:
        return _CCTLD_RDAP[tld]
    # 2. IANA bootstrap cache
    await _load_iana_bootstrap()
    return _BOOTSTRAP_CACHE.get(tld)


async def _rdap_lookup(domain: str, dns_resolves: bool = False) -> dict:
    """RDAP lookup for a single domain. Fully async, no threads needed."""
    result = {
        "status": "unknown",
        "registrar": None,
        "created_date": None,
        "expiry_date": None,
        "days_left": None,
    }

    parts = domain.lower().split(".")
    tld = parts[-1] if parts else ""
    # Check 2nd-level TLDs first (e.g. "com.au", "net.au")
    tld2 = ".".join(parts[-2:]) if len(parts) >= 3 else None
    if tld2 and tld2 in _CCTLD_RDAP:
        tld = tld2
    is_known_gtld = tld in _GTLD_RDAP_OK

    # Build ordered list of endpoints to try
    endpoints: list[str] = []
    authoritative = await _find_rdap_endpoint(tld)
    if authoritative and authoritative != RDAP_BASE:
        endpoints.append(authoritative)
    endpoints.append(RDAP_BASE)

    last_status_code = None
    resp = None

    for idx, base_url in enumerate(endpoints):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(f"{base_url}/{domain}", timeout=RDAP_TIMEOUT)
            last_status_code = resp.status_code

            if resp.status_code == 200:
                break
            # 404 from this endpoint — try next
        except Exception:
            continue
    else:
        # All endpoints returned non-200 or timed out
        if last_status_code == 404:
            # Only mark "available" if:
            # - We successfully queried the authoritative ccTLD RDAP (reliable 404)
            # - OR it's a well-known gTLD (rdap.org is reliable for these)
            # - AND DNS does NOT resolve (DNS is the final truth)
            authoritative_confirmed = (
                (authoritative and authoritative != RDAP_BASE)
                or is_known_gtld
            )
            if dns_resolves:
                result["status"] = "registered"
                logger.debug("RDAP 404 but DNS resolves %s → registered", domain)
            elif authoritative_confirmed:
                result["status"] = "available"
                logger.debug("RDAP 404 (authoritative) %s → available", domain)
            else:
                # ccTLD without reliable RDAP + no DNS → mark unknown, not available
                result["status"] = "unknown"
                logger.debug("RDAP 404 (unreliable endpoint) %s → unknown", domain)
            return result

        # Non-404 failure (timeout, 5xx, etc.)
        if dns_resolves:
            result["status"] = "registered"
        else:
            result["status"] = "check_failed"
        logger.warning("RDAP all endpoints failed for %s (last=%s)", domain, last_status_code)
        return result

    # resp.status_code == 200 here
    if resp is None or resp.status_code != 200:
        result["status"] = "check_failed"
        return result

    # Also handle 404 from the loop break (should not happen, but safety)
    if resp.status_code == 404:
        if dns_resolves:
            result["status"] = "registered"
        else:
            result["status"] = "available"
        return result

    data = resp.json()

    # Extract registrar from entities — try multiple fallback strategies
    for entity in data.get("entities", []):
        if "registrar" in entity.get("roles", []):
            # Strategy 1: vcardArray fn field
            vcard = entity.get("vcardArray", [None, []])
            if len(vcard) > 1:
                for field in vcard[1]:
                    if field[0] == "fn":
                        result["registrar"] = field[3]
                        break
            # Strategy 2: ldhName or handle
            if not result["registrar"]:
                result["registrar"] = entity.get("ldhName") or entity.get("handle")
            break

    # Strategy 3: if no registrar-role entity, check nested entities
    if not result["registrar"]:
        for entity in data.get("entities", []):
            for nested in entity.get("entities", []):
                if "registrar" in nested.get("roles", []):
                    vcard = nested.get("vcardArray", [None, []])
                    if len(vcard) > 1:
                        for field in vcard[1]:
                            if field[0] == "fn":
                                result["registrar"] = field[3]
                                break
                    if not result["registrar"]:
                        result["registrar"] = nested.get("ldhName") or nested.get("handle")
                    break
            if result["registrar"]:
                break

    # Strategy 4: top-level port43 whois server as last resort hint
    if not result["registrar"] and data.get("port43"):
        result["registrar"] = data["port43"]

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

        if action in ("registration", "creation", "registered"):
            result["created_date"] = dt.date()
        elif action in ("expiration", "expiry", "expires"):
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

    return result


async def check_single(domain: str) -> dict:
    """Async RDAP lookup for a single domain."""
    return await _rdap_lookup(domain)


async def check_candidates(db: AsyncSession, source_id: int | None = None, candidate_ids: list[int] | None = None):
    """
    Batch RDAP check for candidates that:
    - have never been checked (whois_checked_at IS NULL), OR
    - previously failed (availability_status IN ('check_failed', 'unknown'))
    Updates DB directly.
    """
    settings = get_settings()

    from sqlalchemy import or_
    query = select(CandidateDomain).where(
        or_(
            CandidateDomain.whois_checked_at.is_(None),
            CandidateDomain.availability_status.in_(["check_failed", "unknown"]),
        )
    )
    if candidate_ids:
        query = query.where(CandidateDomain.id.in_(candidate_ids))
    elif source_id:
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
