"""
Proxy Rotator — load proxies dari file dan rotate per request.
"""

import random
from pathlib import Path


class ProxyRotator:
    """Rotate proxy dari list file. Format: ip:port:user:pass per baris."""

    def __init__(self, proxy_file: str = "proxies.txt"):
        self.proxies = self._load_proxies(proxy_file)
        self._index = 0

    def _load_proxies(self, proxy_file: str) -> list[dict]:
        path = Path(proxy_file)
        if not path.exists():
            print(f"[!] Proxy file '{proxy_file}' tidak ditemukan. Jalan tanpa proxy.")
            return []

        proxies = []
        for line in path.read_text().strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) == 4:
                ip, port, user, password = parts
                proxies.append(f"http://{user}:{password}@{ip}:{port}")
            elif len(parts) == 2:
                ip, port = parts
                proxies.append(f"http://{ip}:{port}")

        print(f"[+] Loaded {len(proxies)} proxies")
        return proxies

    def get_next(self) -> str | None:
        """Ambil proxy berikutnya secara round-robin."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy

    def get_random(self) -> str | None:
        """Ambil proxy random."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    @property
    def count(self) -> int:
        return len(self.proxies)
