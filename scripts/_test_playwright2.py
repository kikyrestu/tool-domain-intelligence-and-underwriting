"""Quick test: Playwright+stealth on Cloudflare-protected sites."""
import asyncio
import re
from playwright.async_api import async_playwright


async def main():
    url = "https://www.virtualpetlist.com/threads/top-10-websites-that-defined-the-early-2000s-internet.4203/"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        try:
            from playwright_stealth import stealth_async
            await stealth_async(page)
            print("Stealth applied")
        except ImportError:
            print("No stealth plugin")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        html = await page.content()
        chall = bool(re.search(r"just a moment|please wait\.\.\.?|ddos protection|challenge-platform|turnstile", html, re.I))
        found_urls = re.findall(r"https?://[a-zA-Z0-9._~/?#@!$&()*+,;=%-]+", html)
        title = await page.title()
        print(f"title: {title!r}")
        print(f"chars={len(html)} challenge={chall} urls_in_page={len(found_urls)}")
        print(f"sample urls: {found_urls[5:12]}")
        await browser.close()


asyncio.run(main())
