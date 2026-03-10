"""Test ZenRows on Cloudflare-protected sites."""
import asyncio
import re
from zenrows import ZenRowsClient

API_KEY = "6ac762fb7215361170e1685f3b6edfe9afb36ad6"

URLS = [
    "https://www.virtualpetlist.com/threads/top-10-websites-that-defined-the-early-2000s-internet.4203/",
    "https://gizmodo.com/100-websites-that-shaped-the-internet-as-we-know-it-1829634771",
]

async def main():
    client = ZenRowsClient(API_KEY)
    for url in URLS:
        try:
            resp = await client.get_async(url, params={"js_render": "true", "antibot": "true"})
            html = resp.text
            chall = bool(re.search(r"just a moment|one moment|please wait|challenge-platform|turnstile", html, re.I))
            found_urls = re.findall(r'https?://[a-zA-Z0-9._~/?#@!$&()*+,;=%-]+', html)
            print(f"URL: {url[:65]}")
            print(f"  status={resp.status_code} chars={len(html)} challenge={chall} urls={len(found_urls)}")
            print(f"  sample: {found_urls[5:9]}")
        except Exception as e:
            print(f"  ERROR: {e}")

asyncio.run(main())
