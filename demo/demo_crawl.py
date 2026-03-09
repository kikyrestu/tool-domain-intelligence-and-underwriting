"""
Demo MVP — Domain Underwriting Engine
Crawl source page → extract outbound links → detect dead links → tampilkan kandidat

Jalankan: python demo/demo_crawl.py <URL>
Contoh:  python demo/demo_crawl.py https://en.wikipedia.org/wiki/Web_crawler
"""

import asyncio
import sys
import time
from urllib.parse import urljoin, urlparse
from pathlib import Path
from ipaddress import ip_address, ip_network

import httpx
from bs4 import BeautifulSoup
import tldextract

# Tambah parent dir ke path agar bisa import proxy_rotator
sys.path.insert(0, str(Path(__file__).parent))
from proxy_rotator import ProxyRotator


# ============================================================
# KONFIGURASI
# ============================================================

TIMEOUT = 15  # detik
MAX_CONCURRENT = 5  # limit concurrent requests
DELAY_BETWEEN = 1.0  # detik antar batch

# User-Agent realistic
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# Domain blacklist — skip yang pasti bukan target beli
BLACKLIST = {
    "google.com", "google.co.id", "youtube.com", "facebook.com", "twitter.com",
    "x.com", "instagram.com", "linkedin.com", "github.com", "reddit.com",
    "amazon.com", "apple.com", "microsoft.com", "wikipedia.org", "wikimedia.org",
    "cloudflare.com", "jsdelivr.net", "cloudfront.net", "amazonaws.com",
    "w3.org", "schema.org", "creativecommons.org", "archive.org",
    "bit.ly", "t.co", "goo.gl", "tinyurl.com",
    "googleanalytics.com", "google-analytics.com", "googlesyndication.com",
    "doubleclick.net", "googletagmanager.com", "hotjar.com",
    "wordpress.com", "wordpress.org", "wp.com", "medium.com",
    "fontawesome.com", "bootstrapcdn.com", "fonts.googleapis.com",
}

# TLD yang bisa dibeli
VALID_TLDS = {"com", "net", "org", "io", "co", "info", "biz", "me", "xyz", "dev", "app"}

# Private IP ranges — untuk SSRF protection
PRIVATE_NETWORKS = [
    ip_network("127.0.0.0/8"),
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("169.254.0.0/16"),
    ip_network("0.0.0.0/8"),
]


# ============================================================
# SSRF PROTECTION
# ============================================================

def is_safe_url(url: str) -> bool:
    """Validasi URL agar tidak SSRF ke internal network."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Block localhost variants
        if hostname in ("localhost", "0.0.0.0", "[::]", "[::1]"):
            return False
        # Cek apakah hostname adalah IP address
        try:
            addr = ip_address(hostname)
            for network in PRIVATE_NETWORKS:
                if addr in network:
                    return False
        except ValueError:
            pass  # Hostname bukan IP, lanjut (domain name)
        return True
    except Exception:
        return False


# ============================================================
# CRAWL ENGINE
# ============================================================

async def crawl_source_page(url: str, client: httpx.AsyncClient) -> list[str]:
    """Crawl source page dan extract semua outbound links."""
    print(f"\n{'='*60}")
    print(f"🕷️  Crawling: {url}")
    print(f"{'='*60}")

    try:
        response = await client.get(url, follow_redirects=True, timeout=TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"   ❌ HTTP Error: {e.response.status_code}")
        return []
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        print(f"   ❌ Connection Error: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    source_domain = tldextract.extract(url).top_domain_under_public_suffix

    links = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        # Resolve relative URLs
        full_url = urljoin(url, href)
        parsed = urlparse(full_url)
        if parsed.scheme not in ("http", "https"):
            continue
        # Skip same-domain links
        ext = tldextract.extract(full_url)
        domain = ext.top_domain_under_public_suffix
        if domain and domain != source_domain:
            links.add(full_url)

    print(f"   ✅ Found {len(links)} outbound links")
    return list(links)


# ============================================================
# DOMAIN EXTRACTION + FILTER
# ============================================================

def extract_and_filter_domains(urls: list[str]) -> dict[str, str]:
    """Extract root domains, dedup, filter blacklist & TLD."""
    domain_map = {}  # domain → first URL seen

    for url in urls:
        ext = tldextract.extract(url)
        domain = ext.top_domain_under_public_suffix
        tld = ext.suffix.split(".")[-1] if ext.suffix else ""

        if not domain:
            continue
        if domain in BLACKLIST:
            continue
        if tld not in VALID_TLDS:
            continue
        if domain not in domain_map:
            domain_map[domain] = url

    return domain_map


# ============================================================
# DEAD LINK DETECTION
# ============================================================

async def check_link_status(
    url: str, domain: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore
) -> dict:
    """Cek apakah link dead atau alive."""
    async with semaphore:
        result = {
            "domain": domain,
            "url": url,
            "status": "unknown",
            "http_code": None,
            "response_time_ms": None,
        }

        if not is_safe_url(url):
            result["status"] = "blocked_ssrf"
            return result

        start = time.monotonic()
        try:
            response = await client.head(
                url, follow_redirects=True, timeout=TIMEOUT
            )
            elapsed = round((time.monotonic() - start) * 1000)
            result["http_code"] = response.status_code
            result["response_time_ms"] = elapsed

            if response.status_code < 400:
                result["status"] = "alive"
            elif response.status_code in (403, 405):
                # Beberapa server block HEAD, coba GET
                response = await client.get(
                    url, follow_redirects=True, timeout=TIMEOUT
                )
                elapsed = round((time.monotonic() - start) * 1000)
                result["http_code"] = response.status_code
                result["response_time_ms"] = elapsed
                result["status"] = "alive" if response.status_code < 400 else "dead"
            else:
                result["status"] = "dead"

        except httpx.ConnectError:
            result["status"] = "dead"
            result["response_time_ms"] = round((time.monotonic() - start) * 1000)
        except httpx.TimeoutException:
            result["status"] = "timeout"
            result["response_time_ms"] = TIMEOUT * 1000
        except Exception:
            result["status"] = "error"
            result["response_time_ms"] = round((time.monotonic() - start) * 1000)

        # Status icon
        icon = {"alive": "🟢", "dead": "💀", "timeout": "⏰", "error": "⚠️", "blocked_ssrf": "🛑"}
        print(f"   {icon.get(result['status'], '❓')} {domain:30s} → {result['status']:8s} (HTTP {result['http_code'] or '-':>3}  {result['response_time_ms'] or '-':>5}ms)")
        return result


# ============================================================
# MAIN DEMO
# ============================================================

async def main(source_url: str):
    # Load proxy
    proxy_file = Path(__file__).parent.parent / "proxies.txt"
    rotator = ProxyRotator(str(proxy_file))
    proxy = rotator.get_random()

    headers = {
        "User-Agent": USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    # Step 1: Crawl source page (coba proxy dulu, fallback direct)
    outbound_links = []
    for attempt_proxy in [proxy, None]:
        label = "proxy" if attempt_proxy else "direct"
        try:
            async with httpx.AsyncClient(headers=headers, proxy=attempt_proxy) as client:
                outbound_links = await crawl_source_page(source_url, client)
                if outbound_links:
                    break
        except Exception as e:
            print(f"   ⚠️  {label} gagal: {e}")
            if attempt_proxy:
                print(f"   🔄 Fallback ke direct connection...")
            continue

    if not outbound_links:
        print("\n❌ Tidak ada outbound links ditemukan. Coba URL lain.")
        return

    # Step 2: Extract + filter domains
    domain_map = extract_and_filter_domains(outbound_links)

    print(f"\n{'='*60}")
    print(f"🔍 Domain Candidates: {len(domain_map)} (setelah dedup + filter)")
    print(f"{'='*60}")

    if not domain_map:
        print("\n❌ Tidak ada domain kandidat setelah filter. Coba URL lain.")
        return

    # Step 3: Check dead links (pakai proxy, rotate per batch)
    print(f"\n{'='*60}")
    print(f"💀 Dead Link Detection")
    print(f"{'='*60}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results = []

    async with httpx.AsyncClient(headers=headers, proxy=proxy) as client:
        tasks = [
            check_link_status(url, domain, client, semaphore)
            for domain, url in domain_map.items()
        ]
        results = await asyncio.gather(*tasks)

    # Step 4: Summary
    dead = [r for r in results if r["status"] == "dead"]
    alive = [r for r in results if r["status"] == "alive"]
    timeout = [r for r in results if r["status"] == "timeout"]
    errors = [r for r in results if r["status"] in ("error", "blocked_ssrf")]

    print(f"\n{'='*60}")
    print(f"📊 HASIL")
    print(f"{'='*60}")
    print(f"   Total kandidat : {len(results)}")
    print(f"   🟢 Alive        : {len(alive)}")
    print(f"   💀 Dead         : {len(dead)}")
    print(f"   ⏰ Timeout      : {len(timeout)}")
    print(f"   ⚠️  Error        : {len(errors)}")

    if dead:
        print(f"\n{'='*60}")
        print(f"🎯 DOMAIN KANDIDAT (Dead Links = Potential Buy)")
        print(f"{'='*60}")
        for i, r in enumerate(dead, 1):
            print(f"   {i}. {r['domain']}")
            print(f"      URL: {r['url']}")
            print(f"      HTTP: {r['http_code'] or 'N/A'}")
            print()

    if alive:
        print(f"\n{'='*60}")
        print(f"📋 DOMAIN ALIVE (Masih aktif — skip atau watchlist)")
        print(f"{'='*60}")
        for i, r in enumerate(alive, 1):
            print(f"   {i}. {r['domain']:30s} ({r['response_time_ms']}ms)")

    print(f"\n✅ Demo selesai!")
    print(f"   Next step: Availability check (WHOIS) + Historical audit (Wayback)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python demo/demo_crawl.py <SOURCE_URL>")
        print("Contoh: python demo/demo_crawl.py https://en.wikipedia.org/wiki/List_of_search_engines")
        sys.exit(1)

    source_url = sys.argv[1]

    if not is_safe_url(source_url):
        print("❌ URL tidak valid atau tidak aman.")
        sys.exit(1)

    asyncio.run(main(source_url))
