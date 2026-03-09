"""Quick test: check how many external domains each source URL yields."""
import httpx
import re
import sys
from urllib.parse import urlparse

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html",
}

urls = [
    "https://en.wikipedia.org/wiki/List_of_defunct_social_networking_services",
    "https://en.wikipedia.org/wiki/List_of_websites_founded_before_1995",
    "https://github.com/awesome-selfhosted/awesome-selfhosted",
    "https://news.ycombinator.com",
]

out = []
with httpx.Client(http2=True, headers=headers, follow_redirects=True, timeout=20) as c:
    for url in urls:
        try:
            r = c.get(url)
            links = re.findall(r'href="https?://[^"]+"', r.text)
            ext_domains = set()
            for m in links:
                href = m[6:-1]
                d = urlparse(href).hostname or ""
                skip = ["wikipedia", "github", "ycombinator", "wikimedia", "w3.org"]
                if d and not any(s in d for s in skip):
                    ext_domains.add(d)
            out.append(f"{r.status_code} | {len(ext_domains):>4} ext domains | {url}")
        except Exception as e:
            out.append(f"FAIL | {url} -> {e}")

with open("tests/test_sources_result.txt", "w") as f:
    f.write("\n".join(out))
print("Done - results in tests/test_sources_result.txt")
