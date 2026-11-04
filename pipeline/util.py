"""Small shared helpers: URLs, domains, slugs, text normalisation, retries."""

from __future__ import annotations

import hashlib
import random
import re
import secrets
import time
import unicodedata
from functools import wraps
from typing import Callable, Iterable, TypeVar
from urllib.parse import urljoin, urlparse, urlunparse

T = TypeVar("T")

_MULTI_PART_TLDS = {"co.uk", "com.au", "co.at"}


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))


def registered_domain(url_or_host: str) -> str:
    """Return the registrable domain (eTLD+1-ish) in lower case, without www."""
    host = url_or_host.strip().lower()
    path = ""
    if "://" in host or host.startswith("//"):
        parsed = urlparse(host if "://" in host else "http:" + host)
        host, path = parsed.netloc, parsed.path
    port = host.split(":")[1] if ":" in host.split("@")[-1] else ""
    host = host.split("@")[-1].split(":")[0].rstrip(".")
    if host in ("localhost", "127.0.0.1") or re.fullmatch(r"[\d.]+", host):
        # Local fixture servers: treat the first path segment as the "domain" so every
        # fixture site is its own business (used by `pipeline demo` and the tests).
        seg = path.strip("/").split("/")[0] if path else ""
        return f"{host}:{port}/{seg}" if port else f"{host}/{seg}"
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    tail = ".".join(parts[-2:])
    if tail in _MULTI_PART_TLDS and len(parts) >= 3:
        return ".".join(parts[-3:])
    return tail


def same_site(url: str, domain: str) -> bool:
    try:
        return registered_domain(url) == domain
    except Exception:
        return False


def absolutize(base: str, href: str) -> str:
    return urljoin(base, href.strip())


def slugify(value: str, max_len: int = 48) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.replace("ß", "ss").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:max_len].rstrip("-") or "firma"


def preview_slug(company_name: str) -> str:
    """Company slug plus a short random part so previews cannot be enumerated."""
    return f"{slugify(company_name, 40)}-{secrets.token_hex(3)}"


def stable_variant(seed: str, n: int) -> int:
    """Deterministic choice 0..n-1 for a seed (used for template variants)."""
    if n <= 1:
        return 0
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % n


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def retry(times: int = 3, base_delay: float = 1.0, exceptions: tuple[type[BaseException], ...] = (Exception,)):
    """Exponential backoff decorator with jitter."""

    def deco(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            delay = base_delay
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise
                    time.sleep(delay + random.uniform(0, delay / 2))
                    delay *= 2
            raise RuntimeError("unreachable")

        return wrapper

    return deco


def read_list_file(path) -> list[str]:
    """Read a config list file: one entry per line, '#' comments, blank lines ignored."""
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def chunked(items: Iterable[T], size: int) -> Iterable[list[T]]:
    batch: list[T] = []
    for it in items:
        batch.append(it)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
