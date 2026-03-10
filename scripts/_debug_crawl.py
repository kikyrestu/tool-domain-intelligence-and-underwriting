"""Debug kenapa crawl return 0 untuk forum URL."""
import asyncio
import httpx
from bs4 import BeautifulSoup
from app.utils.domain_filter import extract_domain, is_valid_candidate

URL = "https://www.virtualpetlist.com/threads/top-10-websites-that-defined-the-early-2000s-internet.4203/"

async def main():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        resp = await client.get(URL, timeout=20)

    print(f"Status: {resp.status_code}, panjang: {len(resp.text)}")
    soup = BeautifulSoup(resp.text, "html.parser")
    source_domain = extract_domain(URL)

    print("\n--- Anchor tags ---")
    seen = set()
    valid = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            continue
        domain = extract_domain(href)
        if not domain or domain == source_domain or domain in seen:
            continue
        seen.add(domain)
        ok = is_valid_candidate(domain)
        print(f"  {'OK ' if ok else 'NO '} {domain:40s} ({href[:80]})")
        if ok:
            valid.append(domain)

    print(f"\nTotal valid: {len(valid)}")
    print(valid)

asyncio.run(main())
