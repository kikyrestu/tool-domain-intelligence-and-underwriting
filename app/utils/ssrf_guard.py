"""SSRF protection — validate URLs before fetching."""

from urllib.parse import urlparse
from ipaddress import ip_address, ip_network

PRIVATE_NETWORKS = [
    ip_network("127.0.0.0/8"),
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("169.254.0.0/16"),
    ip_network("0.0.0.0/8"),
]


def is_safe_url(url: str) -> bool:
    """Validate URL is not targeting internal/private networks."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname in ("localhost", "0.0.0.0", "[::]", "[::1]"):
            return False
        try:
            addr = ip_address(hostname)
            for network in PRIVATE_NETWORKS:
                if addr in network:
                    return False
        except ValueError:
            pass  # Domain name, not IP — OK
        return True
    except Exception:
        return False
