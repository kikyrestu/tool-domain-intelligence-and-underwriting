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
    # Web technology/language domains that appear in links but are not purchasable
    "asp.net", "php.net", "python.org", "ruby-lang.org", "golang.org",
    "nodejs.org", "perl.org", "java.com", "oracle.com", "coldfusion.com",
    "adobe.com", "macromedia.com", "iis.net", "nginx.org", "apache.org",
    "jquery.com", "reactjs.org", "vuejs.org", "angularjs.org", "angular.io",
    "stackoverflow.com", "stackexchange.com", "superuser.com",
    "w3schools.com", "developer.mozilla.org", "mdn.io",
}

# File-like pseudo-TLDs — strings that look like extensions, not real TLDs.
# tldextract sometimes misreads these as TLDs if the PSL cache is stale.
_FAKE_EXT_TLDS = {
    "asp", "aspx", "cfm", "cfml", "jsp", "jspx",
    "php", "php3", "php4", "php5", "phtml",
    "html", "htm", "xhtml", "shtml",
    "rb", "py", "pl", "cgi",
    "do", "action",
}

# Purchasable TLDs
VALID_TLDS = {
    # Generic / high-value
    "com", "net", "org", "io", "co", "info", "biz", "xyz", "dev", "app",
    # Tech / startup favourites
    "ai", "gg", "sh", "so", "to", "fm", "ws", "la", "is", "mn", "ly",
    # Country codes with broad secondary market
    "me", "tv", "cc", "am", "im", "ms", "pw", "gl", "vc",
    # New gTLDs with active resale market
    "click", "online", "site", "store", "tech", "space", "blog",
    "news", "media", "club", "top", "live", "digital", "network",
    "solutions", "services", "agency", "studio", "design", "plus",
    # Regional / language-neutral
    "us", "uk", "eu",
    # Australian second-level (tldextract returns last segment of suffix)
    "au",
}


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
    # Reject pseudo-TLDs that are actually file extensions
    if tld in _FAKE_EXT_TLDS:
        return False
    if tld not in VALID_TLDS:
        return False
    return True
