"""Quick test: can Playwright bypass Cloudflare on virtualpetlist?"""
import asyncio
import re
from playwright.async_api import async_playwright


async def main():
    urls = [
        "https://www.virtualpetlist.com/threads/top-10-websites-that-defined-the-early-2000s-internet.4203/",
        "https://gizmodo.com/100-websites-that-shaped-the-internet-as-we-know-it-1829634771",
    ]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        for url in urls:
            try:
                page = await (await browser.new_context(locale="en-US")).new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                chall = bool(re.search(r"just a moment|please wait|ddos protection|challenge-platform", html, re.I))
                found_urls = re.findall(r"https?://[a-zA-Z0-9._~/?#@!$&()*+,;=%-]+", html)
                print(f"URL: {url[:70]}")
                print(f"  chars={len(html)} challenge={chall} urls_in_page={len(found_urls)}")
                print(f"  sample urls: {found_urls[10:15]}")
            except Exception as e:
                print(f"  ERROR: {e}")
        await browser.close()


asyncio.run(main())
