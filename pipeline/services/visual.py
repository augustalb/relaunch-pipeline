"""Visual assessment of a website's mobile first impression.

The scoring stage takes a mobile screenshot of the homepage and asks the LLM how
outdated and how hard to use on a phone the page looks. The rating only steers
qualification (which leads are worth a preview). It is an opinion, not a measured
fact, so it is never used as an email finding.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Protocol

from ..config import get_settings
from ..costs import CostTracker
from ..log import get_logger

log = get_logger("visual")

VIEWPORT = {"width": 390, "height": 844}
CAPTURE_HEIGHT = 1600  # roughly two phone screens

RATING_SCHEMA = {
    "type": "object",
    "properties": {
        "outdated": {"type": "integer", "description": "1 = looks current (2023+), 10 = looks like the early 2000s"},
        "mobile_usability": {"type": "integer", "description": "1 = unusable on a phone, 10 = excellent on a phone"},
        "reasons": {"type": "array", "items": {"type": "string"}, "description": "max. 3 short German reasons"},
    },
    "required": ["outdated", "mobile_usability", "reasons"],
    "additionalProperties": False,
}

SYSTEM = (
    "You review screenshots of small-business websites (German driving schools) as they appear on a smartphone. "
    "Rate only what is visible: layout, typography, readability, tap targets, imagery, visual age. "
    "Ignore the business itself and its prices. Be consistent: a clean responsive site built with a modern "
    "template is not outdated even if it is plain. Tiny unscaled desktop layouts, table layouts, default "
    "fonts, clip-art, cluttered navigation and visible broken elements indicate an outdated site. "
    "Cookie/consent banners, chat widgets and pop-ups are overlays added by law or plugins: ignore them "
    "completely and judge the page design behind them. "
    "Write the reasons in German, each under 12 words."
)

# Measured in the browser, so the numbers are facts (unlike the LLM opinion).
METRICS_JS = """() => {
  const vw = window.innerWidth;
  const sw = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const scale = 1;  // measured in a 390 px window without mobile shrink-to-fit
  let total = 0, small = 0;
  if (document.body) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const text = walker.currentNode.textContent.trim();
      const el = walker.currentNode.parentElement;
      if (text.length < 3 || !el) continue;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const px = (parseFloat(cs.fontSize) || 0) * scale;
      total += text.length;
      if (px < 12) small += text.length;
    }
  }
  // Can the visitor actually scroll sideways? (Hidden off-canvas menus widen scrollWidth but are not scrollable.)
  const x0 = window.scrollX;
  window.scrollTo(100000, window.scrollY);
  let hScroll = Math.max(0, Math.round(window.scrollX - x0));
  // overflow-x hidden/clip on the root (or body, which propagates to the viewport) blocks user scrolling,
  // even though scripts can still scroll programmatically.
  const rootOx = getComputedStyle(document.documentElement).overflowX;
  const bodyOx = document.body ? getComputedStyle(document.body).overflowX : 'visible';
  const viewportOx = rootOx !== 'visible' ? rootOx : bodyOx;
  if (viewportOx === 'hidden' || viewportOx === 'clip') hScroll = 0;
  window.scrollTo(x0, window.scrollY);
  const hasViewportMeta = !!document.querySelector('meta[name="viewport" i]');
  return {device_width: 390, viewport_width: vw, page_width: sw, h_scroll: hScroll, has_viewport_meta: hasViewportMeta, small_text_share: total ? small / total : 0};
}"""


@dataclass
class Capture:
    jpeg: bytes
    device_width: int
    viewport_width: int
    page_width: int
    small_text_share: float
    h_scroll: int = 0

    def metrics(self) -> dict:
        return {"device_width": self.device_width, "viewport_width": self.viewport_width, "page_width": self.page_width, "h_scroll": self.h_scroll, "small_text_share": round(self.small_text_share, 3)}


class Screenshotter(Protocol):
    def capture(self, url: str) -> Capture | None: ...


class PlaywrightScreenshotter:
    """One headless Chromium for the whole scoring run."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None

    def __enter__(self) -> "PlaywrightScreenshotter":
        try:
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(args=["--no-sandbox"])
        except Exception as e:  # noqa: BLE001 - visual check is optional
            log.warning("playwright not available, visual check skipped", err=str(e)[:200])
            self.close()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:  # noqa: BLE001
                pass
            self._browser = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:  # noqa: BLE001
                pass
            self._pw = None

    def capture(self, url: str) -> Capture | None:
        if self._browser is None:
            return None
        s = get_settings()
        ctx = self._browser.new_context(viewport=VIEWPORT, device_scale_factor=1, is_mobile=True, has_touch=True, user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ))
        try:
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=s.HTTP_TIMEOUT_SECONDS * 1000)
            page.wait_for_timeout(800)
            mobile_layout = int(page.evaluate("window.innerWidth") or VIEWPORT["width"])
            height = min(CAPTURE_HEIGHT, int(page.evaluate("document.documentElement.scrollHeight") or VIEWPORT["height"]))
            jpeg = page.screenshot(type="jpeg", quality=70, full_page=True, clip={"x": 0, "y": 0, "width": VIEWPORT["width"], "height": max(height, 400)})
        except Exception as e:  # noqa: BLE001
            log.warning("screenshot failed", url=url, err=str(e)[:200])
            return None
        finally:
            ctx.close()
        # Mobile emulation zooms out whenever anything is wider than the screen, even hidden off-canvas menus.
        # A plain 390 px window shows what a visitor can actually scroll to and how big the text really is.
        m, narrow_jpeg = self._measure_narrow(url)
        m = m or {"page_width": 0, "h_scroll": 0, "small_text_share": 0.0, "has_viewport_meta": False}
        if mobile_layout > VIEWPORT["width"] + 16 and m.get("has_viewport_meta") and not m.get("h_scroll") and narrow_jpeg:
            jpeg = narrow_jpeg  # emulation zoomed out only because of hidden overflow: show the page as visitors see it
        return Capture(jpeg, VIEWPORT["width"], mobile_layout, int(m["page_width"]), float(m["small_text_share"]), int(m.get("h_scroll") or 0))

    def _measure_narrow(self, url: str) -> tuple[dict | None, bytes | None]:
        s = get_settings()
        ctx = self._browser.new_context(viewport=VIEWPORT, device_scale_factor=1, is_mobile=False)
        try:
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=s.HTTP_TIMEOUT_SECONDS * 1000)
            page.wait_for_timeout(500)
            m = page.evaluate(METRICS_JS)
            height = min(CAPTURE_HEIGHT, int(page.evaluate("document.documentElement.scrollHeight") or VIEWPORT["height"]))
            jpeg = page.screenshot(type="jpeg", quality=70, full_page=True, clip={"x": 0, "y": 0, "width": VIEWPORT["width"], "height": max(height, 400)})
            return m, jpeg
        except Exception as e:  # noqa: BLE001
            log.warning("narrow measurement failed", url=url, err=str(e)[:200])
            return None, None
        finally:
            ctx.close()


class VisualRater:
    def __init__(self, api_key: str, model: str, costs: CostTracker):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.costs = costs

    def rate(self, jpeg: bytes) -> dict | None:
        import anthropic

        s = get_settings()
        self.costs.check_eur("llm", s.LLM_MAX_COST_PER_RUN_EUR)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(jpeg).decode()}},
                        {"type": "text", "text": "Rate this homepage screenshot (iPhone width)."},
                    ],
                }],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": RATING_SCHEMA}},
            )
        except anthropic.APIStatusError as e:
            log.warning("visual rating failed", status=e.status_code, err=str(e)[:300])
            return None
        except anthropic.APIConnectionError as e:
            log.warning("visual rating failed", err=str(e)[:200])
            return None
        usage = response.usage
        eur = (usage.input_tokens / 1e6) * s.COST_LLM_INPUT_PER_MTOK_EUR + (usage.output_tokens / 1e6) * s.COST_LLM_OUTPUT_PER_MTOK_EUR
        self.costs.record("llm", eur, units=usage.input_tokens + usage.output_tokens, note=f"{self.model} visual")
        if response.stop_reason != "end_turn":
            log.warning("visual rating incomplete", stop_reason=response.stop_reason)
            return None
        text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        data["outdated"] = max(1, min(10, int(data.get("outdated", 5))))
        data["mobile_usability"] = max(1, min(10, int(data.get("mobile_usability", 5))))
        data["reasons"] = [str(r)[:120] for r in (data.get("reasons") or [])][:3]
        return data


def make_visual_rater(costs: CostTracker) -> VisualRater | None:
    s = get_settings()
    if not (s.VISUAL_CHECK and s.ANTHROPIC_API_KEY):
        return None
    return VisualRater(s.ANTHROPIC_API_KEY, s.LLM_MODEL, costs)


def visual_points(rating: dict | None) -> int:
    """Points added to the score. Negative for sites that look modern."""
    if not rating:
        return 0
    outdated = rating["outdated"]
    usability = rating["mobile_usability"]
    if outdated >= 8 or usability <= 3:
        return 30  # clearly outdated sites qualify even with few technical defects (DECISIONS 19)
    if outdated >= 6 or usability <= 5:
        return 10
    if outdated <= 3 and usability >= 7:
        return -15
    return 0
