"""Stage 2 – Scoring: own HTML checks + PageSpeed Insights (mobile) + visual LLM rating -> score 0..100 + findings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup

from ..config import get_settings
from ..costs import BudgetExceeded, CostTracker
from ..db import Lead, LeadStatus, leads_in_status, session_scope, utcnow
from ..http import FetchResult, client as http_client, fetch
from ..industry import load_industry
from ..log import get_logger
from ..services.pagespeed import PageSpeedClient, PageSpeedResult, make_pagespeed_client
from ..services.visual import PlaywrightScreenshotter, Screenshotter, VisualRater, make_visual_rater, visual_points
from ..util import absolutize, same_site

log = get_logger("scoring")

BUILDERS = {
    "jimdo": "Jimdo-Baukasten",
    "wix.com": "Wix-Baukasten",
    "weebly": "Weebly-Baukasten",
    "1&1": "1&1/IONOS-Baukasten",
    "ionos": "IONOS-Baukasten",
    "mywebsite": "IONOS MyWebsite",
    "homepage-baukasten": "Homepage-Baukasten",
    "strato": "STRATO-Baukasten",
    "frontpage": "Microsoft FrontPage",
    "dreamweaver": "Dreamweaver",
    "netobjects": "NetObjects Fusion",
    "microsoft word": "Microsoft Word",
    "iweb": "Apple iWeb",
    "web to date": "Web to Date",
    "zeta producer": "Zeta Producer",
    "joomla! 1.": "Joomla 1.x",
    "joomla! 2.": "Joomla 2.x",
    "typo3 4.": "TYPO3 4.x",
    "wordpress 3.": "WordPress 3.x",
    "wordpress 4.": "WordPress 4.x",
}


@dataclass
class Finding:
    key: str
    points: int
    text: str  # German, factual, verifiable
    value: str | None = None
    internal: bool = False  # True = only steers qualification, never shown in emails
    email_weight: int | None = None  # ranking for email findings if it differs from the score points


@dataclass
class ScoreResult:
    score: int
    findings: list[Finding]
    details: dict = field(default_factory=dict)

    def top_findings(self, n: int = 3) -> list[str]:
        usable = [f for f in self.findings if not f.internal and f.points > 0]
        return [f.text for f in sorted(usable, key=lambda f: -(f.email_weight if f.email_weight is not None else f.points))[:n]]


def _copyright_year(text: str) -> int | None:
    years = []
    for m in re.finditer(r"(?:©|&copy;|\(c\)|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", text, re.I):
        y = int(m.group(1))
        if 1995 <= y <= 2100:
            years.append(y)
    return max(years) if years else None


def analyze_html(res: FetchResult, psi: PageSpeedResult | None, *, internal_checks: list[int] | None = None, now: datetime | None = None, industry_scoring: dict | None = None, visual: dict | None = None, mobile: dict | None = None) -> ScoreResult:
    """Pure function: turn a fetched home page (+ PSI) into a score and findings."""
    now = now or utcnow()
    f: list[Finding] = []
    details: dict = {}
    html = res.html or ""
    soup = BeautifulSoup(html, "lxml") if html else BeautifulSoup("", "lxml")
    text = soup.get_text(" ", strip=True)
    low_html = html.lower()

    # --- reachability
    if not res.ok:
        f.append(Finding("unreachable", 40, f"Ihre Website war bei unserem Test nicht erreichbar (Status {res.status or 'Fehler'})."))
        return ScoreResult(min(100, sum(x.points for x in f)), f, {"error": res.error, "status": res.status})
    details["status"] = res.status
    details["final_url"] = res.final_url

    # --- HTTPS
    if not res.final_url.lower().startswith("https://"):
        f.append(Finding("no_https", 18, "Ihre Website wird ohne HTTPS-Verschlüsselung ausgeliefert; Browser zeigen sie als „Nicht sicher“ an."))
    elif res.url.lower().startswith("http://") and not any(r.lower().startswith("http://") for r in res.redirects[:1]):
        pass
    if "http://" in low_html and res.final_url.lower().startswith("https://"):
        mixed = re.findall(r'(?:src|href)=["\']http://[^"\']+\.(?:js|css|png|jpg|jpeg|gif)', low_html)
        if mixed:
            f.append(Finding("mixed_content", 6, "Ihre Website lädt unverschlüsselte Dateien nach (Mixed Content); Browser blockieren oder warnen davor.", str(len(mixed))))

    # --- viewport / mobile
    viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    if viewport is None:
        f.append(Finding("no_viewport", 22, "Ihre Website hat keine mobile Darstellung (kein viewport-Meta-Tag) und wird auf dem Smartphone verkleinert angezeigt."))

    # --- copyright year
    year = _copyright_year(html)
    details["copyright_year"] = year
    if year and now.year - year >= 2:
        f.append(Finding("old_copyright", min(14, 4 + (now.year - year) * 2), f"Im Fußbereich Ihrer Website steht noch das Jahr {year}.", str(year)))

    # --- generator / builder
    gen = soup.find("meta", attrs={"name": re.compile("^generator$", re.I)})
    gen_content = (gen.get("content") if gen else "") or ""
    haystack = (gen_content + " " + low_html[:20000]).lower()
    for needle, label in BUILDERS.items():
        if needle in haystack:
            details["builder"] = label
            f.append(Finding("builder", 10, f"Ihre Website wurde mit {label} erstellt; solche Seiten sind meist nicht mehr zeitgemäß wartbar.", label))
            break

    # --- legacy markup
    tables = len(soup.find_all("table"))
    layout_tables = sum(1 for t in soup.find_all("table") if not t.find("th") and len(t.find_all("tr")) >= 3)
    if layout_tables >= 2 or (tables >= 1 and soup.find("table", attrs={"width": True}) is not None and viewport is None):
        f.append(Finding("table_layout", 14, "Das Layout Ihrer Website ist mit HTML-Tabellen gebaut, einer Technik aus den 2000er-Jahren."))
    legacy_tags = [t for t in ("font", "center", "marquee", "frameset", "frame", "blink") if soup.find(t)]
    if legacy_tags:
        f.append(Finding("legacy_tags", 10, f"Ihre Website verwendet veraltete HTML-Elemente ({', '.join('<' + t + '>' for t in legacy_tags)}), die moderne Browser nur noch eingeschränkt unterstützen."))
    if ".swf" in low_html or "shockwave-flash" in low_html:
        f.append(Finding("flash", 16, "Ihre Website bindet Flash ein, das seit 2021 in keinem Browser mehr läuft."))
    if "document.write(" in low_html:
        f.append(Finding("document_write", 3, "Ihre Website nutzt document.write, das von Browsern inzwischen blockiert werden kann."))
    jq = re.search(r"jquery[-.]?(1\.\d+)", low_html)
    if jq:
        f.append(Finding("old_jquery", 4, f"Ihre Website lädt eine jQuery-Version von 2016 oder älter ({jq.group(1)})."))

    # --- basic SEO/content hygiene
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not title:
        f.append(Finding("no_title", 6, "Ihre Startseite hat keinen Seitentitel; in Google-Ergebnissen erscheint dann nur die Adresse."))
    if not soup.find("meta", attrs={"name": re.compile("^description$", re.I)}):
        f.append(Finding("no_description", 4, "Ihre Startseite hat keine Meta-Beschreibung für Suchmaschinen."))
    if not soup.find("h1"):
        f.append(Finding("no_h1", 3, "Ihre Startseite hat keine Hauptüberschrift (H1)."))
    imgs = soup.find_all("img")
    no_alt = [i for i in imgs if not (i.get("alt") or "").strip()]
    if imgs and len(no_alt) / len(imgs) > 0.6 and len(imgs) >= 3:
        f.append(Finding("no_alt", 4, f"{len(no_alt)} von {len(imgs)} Bildern auf Ihrer Startseite haben keinen Alternativtext (Barrierefreiheit)."))
    if re.search(r"(im aufbau|under construction|coming soon|demnächst|wird überarbeitet)", text, re.I):
        f.append(Finding("under_construction", 12, "Auf Ihrer Startseite steht ein Hinweis „im Aufbau“ bzw. „under construction“."))
    if "<!doctype html>" not in low_html[:200] and "<!doctype" in low_html[:400]:
        f.append(Finding("old_doctype", 5, "Ihre Website nutzt noch einen HTML-4/XHTML-Doctype statt HTML5."))
    elif "<!doctype" not in low_html[:400]:
        f.append(Finding("no_doctype", 5, "Ihre Website hat keine Doctype-Angabe; Browser rendern sie im Kompatibilitätsmodus."))
    if soup.find(attrs={"bgcolor": True}) or re.search(r"<body[^>]+background=", low_html):
        f.append(Finding("bgcolor", 4, "Ihre Website nutzt Farbangaben direkt im HTML (bgcolor), ein Kennzeichen sehr alter Seiten."))
    if not soup.find("link", rel=re.compile("icon", re.I)) and "favicon" not in low_html:
        f.append(Finding("no_favicon", 2, "Ihre Website hat kein Favicon (Symbol im Browser-Tab)."))

    # --- broken internal links (sampled by caller)
    if internal_checks:
        broken = [c for c in internal_checks if c >= 400 or c == 0]
        details["internal_links_checked"] = len(internal_checks)
        details["internal_links_broken"] = len(broken)
        if broken:
            f.append(Finding("broken_links", min(12, 4 * len(broken)), f"{len(broken)} von {len(internal_checks)} geprüften Unterseiten Ihrer Website liefern einen Fehler (z. B. 404)."))

    # --- PageSpeed
    if psi is not None:
        details["psi"] = psi.as_dict()
        if psi.performance is not None:
            perf = int(round(psi.performance * 100))
            if perf < 50:
                f.append(Finding("psi_perf", 12, f"Google PageSpeed bewertet die mobile Ladeleistung Ihrer Website mit {perf} von 100 Punkten.", str(perf), email_weight=20))
            elif perf < 70:
                f.append(Finding("psi_perf", 6, f"Google PageSpeed bewertet die mobile Ladeleistung Ihrer Website mit {perf} von 100 Punkten.", str(perf), email_weight=10))
        if psi.lcp_ms and psi.lcp_ms >= 4000:
            secs = round(psi.lcp_ms / 1000)
            f.append(Finding("psi_lcp", 8 if psi.lcp_ms >= 6000 else 5, f"Ihre Website braucht auf dem Smartphone rund {secs} Sekunden, bis der Hauptinhalt sichtbar ist (gemessen mit Google PageSpeed).", str(secs), email_weight=14 if psi.lcp_ms >= 6000 else 8))
        if psi.cls is not None and psi.cls >= 0.25:
            f.append(Finding("psi_cls", 6, f"Beim Laden verschieben sich Inhalte Ihrer Website deutlich (Layout-Shift {psi.cls:.2f}, Google-Grenzwert 0,1)."))
        if psi.accessibility is not None and psi.accessibility < 0.7:
            f.append(Finding("psi_a11y", 5, f"Google PageSpeed bewertet die Barrierefreiheit Ihrer Website mit {int(round(psi.accessibility * 100))} von 100 Punkten."))
        if psi.seo is not None and psi.seo < 0.7:
            f.append(Finding("psi_seo", 4, f"Google PageSpeed bewertet die Suchmaschinen-Grundlagen Ihrer Website mit {int(round(psi.seo * 100))} von 100 Punkten."))
    else:
        # no PSI (offline / quota): fall back to a crude payload heuristic
        size_kb = len(html.encode("utf-8", "ignore")) // 1024
        details["html_kb"] = size_kb
        if res.elapsed_ms and res.elapsed_ms > 3000:
            f.append(Finding("slow_ttfb", 8, f"Ihre Startseite brauchte bei unserem Abruf {res.elapsed_ms / 1000:.1f} Sekunden, bis der Server geantwortet hat."))

    # --- industry specific
    ind = industry_scoring or {}
    if ind.get("missing_services_page") and not re.search(r"klasse|führerschein|fuehrerschein", text, re.I):
        f.append(Finding("no_services", int(ind["missing_services_page"]), "Auf Ihrer Startseite ist nicht erkennbar, welche Führerscheinklassen Sie ausbilden."))

    # --- measured mobile rendering (browser metrics, factual)
    if mobile:
        details["mobile"] = mobile
        has_no_viewport = any(x.key == "no_viewport" for x in f)
        # Mobile browsers either zoom out (layout viewport grows) or scroll sideways; both mean the page is wider than the phone.
        dw = mobile.get("device_width") or 390
        width = max(mobile.get("viewport_width") or 0, mobile.get("page_width") or 0)
        if not has_no_viewport and width > dw + 16:
            f.append(Finding("mobile_overflow", 18, f"Auf dem Smartphone passt Ihre Startseite nicht auf den Bildschirm: Sie ist {width} Pixel breit statt {dw} Pixel, der Browser verkleinert sie oder Besucher müssen seitlich scrollen.", str(width)))
        share = mobile.get("small_text_share") or 0
        if not has_no_viewport and share >= 0.3:
            f.append(Finding("small_text", 8, f"Rund {int(round(share * 100))} % des Textes auf Ihrer Startseite erscheint auf dem Smartphone kleiner als 12 Pixel.", str(int(round(share * 100)))))

    # --- visual first impression (LLM opinion on the mobile screenshot; internal only)
    if visual:
        details["visual"] = visual
        pts = visual_points(visual)
        if pts:
            key = "visual_outdated" if pts > 0 else "visual_modern"
            f.append(Finding(key, pts, "; ".join(visual.get("reasons") or []) or key, str(visual.get("outdated")), internal=True))

    score = max(0, min(100, sum(x.points for x in f)))
    details["checks"] = {x.key: x.points for x in f}
    return ScoreResult(score, f, details)


def sample_internal_links(res: FetchResult, domain: str, http, max_links: int = 5) -> list[int]:
    soup = BeautifulSoup(res.html or "", "lxml")
    seen: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = absolutize(res.final_url, href).split("#")[0]
        if same_site(url, domain) and url not in seen and url != res.final_url:
            seen.append(url)
        if len(seen) >= max_links:
            break
    codes = []
    for url in seen:
        try:
            r = http.head(url)
            if r.status_code in (405, 403):
                r = http.get(url)
            codes.append(r.status_code)
        except Exception:
            codes.append(0)
    return codes


def score_url(
    url: str,
    domain: str,
    psi_client: PageSpeedClient,
    industry_scoring: dict,
    screenshotter: Screenshotter | None = None,
    rater: VisualRater | None = None,
) -> tuple[ScoreResult, FetchResult]:
    with http_client() as http:
        res = fetch(url, http)
        internal = sample_internal_links(res, domain, http) if res.ok else None
    psi = None
    if res.ok:
        try:
            psi = psi_client.analyze(res.final_url)
        except BudgetExceeded as e:
            log.warning(str(e))
        except Exception as e:
            log.warning("pagespeed failed", url=url, err=str(e))
    visual = mobile = None
    if res.ok and screenshotter is not None:
        try:
            shot = screenshotter.capture(res.final_url)
            if shot is not None:
                mobile = shot.metrics()
                if rater is not None:
                    visual = rater.rate(shot.jpeg)
        except BudgetExceeded as e:
            log.warning(str(e))
        except Exception as e:  # noqa: BLE001 - visual check is optional
            log.warning("visual check failed", url=url, err=str(e)[:200])
    return analyze_html(res, psi, internal_checks=internal, industry_scoring=industry_scoring, visual=visual, mobile=mobile), res


def run(
    limit: int | None = None,
    costs: CostTracker | None = None,
    psi_client: PageSpeedClient | None = None,
    rater: VisualRater | None = None,
    screenshotter: Screenshotter | None = None,
) -> dict:
    costs = costs or CostTracker()
    rater = rater if rater is not None else make_visual_rater(costs)
    if screenshotter is None and get_settings().VISUAL_CHECK:
        with PlaywrightScreenshotter() as shooter:
            return _run(limit, costs, psi_client, rater, shooter)
    return _run(limit, costs, psi_client, rater, screenshotter)


def _run(limit, costs, psi_client, rater, screenshotter) -> dict:
    s = get_settings()
    industry = load_industry()
    psi_client = psi_client or make_pagespeed_client(costs)
    stats = {"scored": 0, "qualified": 0, "disqualified": 0, "errors": 0}
    with session_scope() as session:
        leads = leads_in_status(session, LeadStatus.DISCOVERED, limit, industry.name)
    for lead_id in [l.id for l in leads]:
        try:
            _score_one(lead_id, s, industry, psi_client, screenshotter, rater, stats)
        except Exception as e:  # noqa: BLE001 - one broken site must not stop the stage
            stats["errors"] += 1
            log.error("scoring failed", lead=lead_id, err=str(e)[:300])
    log.info("scoring done", **stats)
    return stats


def _score_one(lead_id, s, industry, psi_client, screenshotter, rater, stats) -> None:
    with session_scope() as session:
        lead = session.get(Lead, lead_id)
        try:
            result, res = score_url(lead.website, lead.domain, psi_client, industry.scoring, screenshotter, rater)
        except Exception as e:
            stats["errors"] += 1
            log.error("scoring failed", lead=lead_id, err=str(e))
            return
        lead.score = result.score
        lead.score_details = result.details
        lead.findings = result.top_findings(3)
        lead.scored_at = utcnow()
        if res.ok and res.final_url and len(res.final_url) <= 1000 and same_site(res.final_url, lead.domain or ""):
            lead.website = res.final_url
        lead.transition(LeadStatus.SCORED, f"score={result.score}", session)
        stats["scored"] += 1
        if not res.ok:
            lead.transition(LeadStatus.DISQUALIFIED, "Website nicht erreichbar", session)
            stats["disqualified"] += 1
        elif result.score >= s.SCORE_THRESHOLD:
            lead.transition(LeadStatus.QUALIFIED, None, session)
            stats["qualified"] += 1
        else:
            lead.transition(LeadStatus.DISQUALIFIED, f"Score {result.score} < {s.SCORE_THRESHOLD}", session)
            stats["disqualified"] += 1
        log.info(
            "scored",
            lead=lead_id,
            domain=lead.domain,
            score=result.score,
            checks=result.details.get("checks"),
            visual=(result.details.get("visual") or {}).get("outdated"),
            visual_usability=(result.details.get("visual") or {}).get("mobile_usability"),
            visual_reasons=(result.details.get("visual") or {}).get("reasons"),
        )
