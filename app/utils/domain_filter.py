"""Domain filtering — blacklist + TLD validation."""

import tldextract

# Domain blacklist — major domains that are never purchase targets
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

# Purchasable TLDs
VALID_TLDS = {"com", "net", "org", "io", "co", "info", "biz", "me", "xyz", "dev", "app"}


def extract_domain(url: str) -> str | None:
    """Extract registrable domain from URL."""
    ext = tldextract.extract(url)
    return ext.registered_domain or None


def is_valid_candidate(domain: str) -> bool:
    """Check if domain passes blacklist + TLD filters."""
    if not domain:
        return False
    if domain.lower() in BLACKLIST:
        return False
    ext = tldextract.extract(domain)
    tld = ext.suffix.split(".")[-1] if ext.suffix else ""
    if tld not in VALID_TLDS:
        return False
    return True
