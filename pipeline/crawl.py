"""Shared crawling helpers: find relevant subpages, extract text/e-mails/phones, optional Playwright."""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .config import get_settings
from .http import FetchResult, client as http_client, fetch
from .log import get_logger
from .util import absolutize, collapse_ws, same_site

log = get_logger("crawl")

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
OBFUSCATED_RE = re.compile(
    r"([A-Za-z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\{at\}|\[ät\]|\(ät\)|\s@\s|&#64;| at |\[@\]|\(@\)|\sat\s)\s*([A-Za-z0-9\-]+(?:\s*(?:\[dot\]|\(dot\)|\[punkt\]|\(punkt\)|\.)\s*[A-Za-z0-9\-]+)+)",
    re.I,
)
PHONE_RE = re.compile(r"(?:\+49|0049|0)\s?[\d\s/\-()]{6,20}\d")
IGNORED_EMAIL_DOMAINS = ("example.com", "sentry.io", "wixpress.com", "jimdo.com", "ionos.de", "1und1.de", "strato.de", "googlemail.com.invalid")
IGNORED_EMAIL_PREFIXES = ("noreply", "no-reply", "datenschutz@", "privacy@", "webmaster@", "postmaster@", "abuse@", "hostmaster@")


@dataclass
class Page:
    url: str
    kind: str  # start | imprint | contact | services | prices | team | hours | about | other
    title: str
    text: str
    html: str
    links: list[tuple[str, str]] = field(default_factory=list)  # (text, absolute url)
    images: list[tuple[str, str]] = field(default_factory=list)  # (absolute url, alt)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)


def _decode_cf_email(encoded: str) -> str | None:
    """Cloudflare e-mail obfuscation (data-cfemail)."""
    try:
        key = int(encoded[:2], 16)
        return "".join(chr(int(encoded[i : i + 2], 16) ^ key) for i in range(2, len(encoded), 2))
    except ValueError:
        return None


def extract_emails(html: str, text: str | None = None) -> list[str]:
    found: list[str] = []
    raw = html_lib.unescape(html)
    # mailto links first (highest confidence)
    for m in re.finditer(r'mailto:([^"\'?\s>]+)', raw, re.I):
        found.append(m.group(1))
    for m in re.finditer(r'data-cfemail="([0-9a-f]+)"', raw, re.I):
        dec = _decode_cf_email(m.group(1))
        if dec:
            found.append(dec)
    text = text if text is not None else BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    found += EMAIL_RE.findall(text)
    for m in OBFUSCATED_RE.finditer(text):
        local, domain = m.group(1), m.group(2)
        domain = re.sub(r"\s*(?:\[dot\]|\(dot\)|\[punkt\]|\(punkt\))\s*", ".", domain, flags=re.I)
        domain = re.sub(r"\s+", "", domain)
        found.append(f"{local}@{domain}")
    # JS-split patterns like "info" + "@" + "fahrschule.de"
    for m in re.finditer(r'"([A-Za-z0-9._%+\-]+)"\s*\+\s*"@"\s*\+\s*"([A-Za-z0-9.\-]+\.[A-Za-z]{2,})"', raw):
        found.append(f"{m.group(1)}@{m.group(2)}")
    out: list[str] = []
    for e in found:
        e = e.strip().strip(".,;:()<>").lower()
        if not EMAIL_RE.fullmatch(e):
            continue
        if e.endswith(IGNORED_EMAIL_DOMAINS) or e.startswith(IGNORED_EMAIL_PREFIXES):
            continue
        if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js)$", e):
            continue
        if e not in out:
            out.append(e)
    return out


def extract_phones(text: str) -> list[str]:
    out = []
    for m in PHONE_RE.finditer(text):
        p = collapse_ws(m.group(0))
        digits = re.sub(r"\D", "", p)
        if 8 <= len(digits) <= 15 and p not in out:
            out.append(p)
    return out[:5]


def classify_link(text: str, url: str, keywords: dict[str, list[str]]) -> str | None:
    hay = f"{text} {url}".lower()
    for kind, words in keywords.items():
        for w in words:
            if w.lower() in hay:
                return kind
    return None


def parse_page(res: FetchResult, kind: str = "other") -> Page:
    soup = BeautifulSoup(res.html or "", "lxml")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    title = collapse_ws(soup.title.get_text()) if soup.title else ""
    links: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "javascript:", "tel:")):
            continue
        links.append((collapse_ws(a.get_text(" ")), absolutize(res.final_url, href)))
    images: list[tuple[str, str]] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or src.startswith("data:"):
            continue
        images.append((absolutize(res.final_url, src), collapse_ws(img.get("alt") or "")))
    # keep line structure for hours/prices extraction
    for br in soup.find_all(["br", "p", "li", "tr", "h1", "h2", "h3", "h4", "div"]):
        br.append("\n")
    text = soup.get_text(" ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return Page(
        url=res.final_url,
        kind=kind,
        title=title,
        text=text,
        html=res.html or "",
        links=links,
        images=images,
        emails=extract_emails(res.html or "", text),
        phones=extract_phones(text),
    )


def fetch_with_playwright(url: str) -> str | None:
    """Render a JS-heavy page. Returns None when Playwright is unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page(user_agent=get_settings().USER_AGENT)
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:  # pragma: no cover
        log.debug("playwright failed", url=url, err=str(e))
        return None


def looks_js_only(html: str) -> bool:
    soup = BeautifulSoup(html or "", "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    return len(soup.get_text(" ", strip=True)) < 200 and "<script" in (html or "").lower()


def crawl_site(start_url: str, domain: str, keywords: dict[str, list[str]], wanted_kinds: set[str], max_pages: int, use_playwright: bool = False) -> list[Page]:
    """Fetch the start page, then up to `max_pages` relevant subpages."""
    pages: list[Page] = []
    with http_client() as http:
        res = fetch(start_url, http)
        if not res.ok:
            return pages
        if use_playwright and looks_js_only(res.html):
            rendered = fetch_with_playwright(res.final_url)
            if rendered:
                res.html = rendered
        start = parse_page(res, "start")
        pages.append(start)
        seen = {start.url.rstrip("/")}
        queue: list[tuple[str, str]] = []
        for text, url in start.links:
            url = url.split("#")[0]
            if not same_site(url, domain) or url.rstrip("/") in seen:
                continue
            if re.search(r"\.(pdf|jpg|jpeg|png|gif|zip|doc|docx|mp4)$", url, re.I):
                continue
            kind = classify_link(text, url, keywords)
            if kind and kind in wanted_kinds:
                queue.append((kind, url))
                seen.add(url.rstrip("/"))
        # one page per kind first, then the rest
        queue.sort(key=lambda kv: list(keywords).index(kv[0]) if kv[0] in keywords else 99)
        for kind, url in queue[:max_pages]:
            r = fetch(url, http)
            if not r.ok:
                continue
            if use_playwright and looks_js_only(r.html):
                rendered = fetch_with_playwright(r.final_url)
                if rendered:
                    r.html = rendered
            pages.append(parse_page(r, kind))
    return pages
