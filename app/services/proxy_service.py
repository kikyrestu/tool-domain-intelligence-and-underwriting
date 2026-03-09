"""Proxy rotation service — loads proxies from file, rotates per request."""

import random
from pathlib import Path

from app.config import get_settings


class ProxyService:
    """Rotate proxies from a proxy list file. Format: ip:port:user:pass per line."""

    def __init__(self):
        settings = get_settings()
        self.enabled = settings.PROXY_ENABLED
        self.proxies: list[str] = []
        self._index = 0

        if self.enabled:
            self._load(settings.PROXY_FILE)

    def _load(self, proxy_file: str):
        path = Path(proxy_file)
        if not path.exists():
            return
        for line in path.read_text().strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) == 4:
                ip, port, user, password = parts
                self.proxies.append(f"http://{user}:{password}@{ip}:{port}")
            elif len(parts) == 2:
                ip, port = parts
                self.proxies.append(f"http://{ip}:{port}")

    def get_next(self) -> str | None:
        """Round-robin proxy selection."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy

    def get_random(self) -> str | None:
        """Random proxy selection."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    @property
    def count(self) -> int:
        return len(self.proxies)


# Singleton instance
proxy_service = ProxyService()
