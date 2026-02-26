from __future__ import annotations

import re
from urllib.parse import urlparse

DOMAIN_PATTERN = re.compile(r"\b(?:https?://)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)\b")


def extract_domain(text: str) -> str:
    if not text:
        return ""
    match = DOMAIN_PATTERN.search(text)
    if not match:
        return ""
    domain = match.group(1).strip().lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    host = host.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host.split("/")[0]


def short_snippet(text: str, max_len: int = 180) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3] + "..."
