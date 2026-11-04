"""Outbound channel abstraction.

`Sender` is deliberately channel-agnostic: a `Campaign` consists of one or more
`OutboundMessage`s (initial + follow-ups) for one recipient. Today there are two
implementations:

* `DryRunSender`   – default; writes RFC-822 `.eml` files to `outbox/`.
* `InstantlySender` – pushes the lead into an Instantly campaign; Instantly does
  warm-up, mailbox rotation, scheduling and follow-ups.

A postal `LetterSender` can be added later by implementing the same protocol
(the `channel` field on `OutboundMessage` already allows "letter").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from pathlib import Path
from typing import Literal, Protocol

import httpx

from ..config import get_settings
from ..log import get_logger

log = get_logger("sender")

Channel = Literal["email", "letter"]


@dataclass
class OutboundMessage:
    step: int  # 1 = initial, 2 = follow-up 1, ...
    subject: str
    body: str
    send_after_days: int = 0
    channel: Channel = "email"


@dataclass
class Recipient:
    email: str
    company: str
    first_name: str = ""
    last_name: str = ""
    website: str = ""
    city: str = ""
    lead_id: int | None = None


@dataclass
class Campaign:
    recipient: Recipient
    messages: list[OutboundMessage]
    reply_to: str
    variables: dict[str, str] = field(default_factory=dict)


@dataclass
class SendResult:
    ok: bool
    reference: str | None = None
    error: str | None = None


@dataclass
class InboundEvent:
    """Something that happened on the sequencer side: reply, bounce, unsubscribe."""

    email: str
    kind: Literal["replied", "bounced", "unsubscribed", "interested", "not_interested"]
    at: datetime
    excerpt: str | None = None
    reference: str | None = None


class Sender(Protocol):
    name: str

    def send(self, campaign: Campaign) -> SendResult: ...

    def sync(self, since: datetime) -> list[InboundEvent]: ...


class DryRunSender:
    name = "dryrun"

    def __init__(self, outbox: Path | None = None):
        self.outbox = outbox or get_settings().OUTBOX_DIR
        self.outbox.mkdir(parents=True, exist_ok=True)

    def send(self, campaign: Campaign) -> SendResult:
        s = get_settings()
        ref = f"dryrun-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        paths = []
        for m in campaign.messages:
            msg = EmailMessage()
            msg["From"] = f"{s.SENDER_NAME} <versand@{s.PREVIEW_DOMAIN}>"  # placeholder; real sending domain lives in the sequencer
            msg["To"] = campaign.recipient.email
            msg["Reply-To"] = campaign.reply_to
            msg["Subject"] = m.subject
            msg["Date"] = format_datetime(now + timedelta(days=m.send_after_days))
            msg["Message-ID"] = make_msgid(domain=s.PREVIEW_DOMAIN)
            msg["X-Pipeline-Ref"] = ref
            msg["X-Pipeline-Step"] = str(m.step)
            msg["X-Pipeline-Channel"] = m.channel
            msg["X-Pipeline-Send-After-Days"] = str(m.send_after_days)
            msg.set_content(m.body, charset="utf-8")
            fname = f"{now:%Y%m%d}-{campaign.recipient.lead_id or 'x'}-step{m.step}-{ref}.eml"
            path = self.outbox / fname
            path.write_bytes(bytes(msg))
            paths.append(path)
        log.info("dry-run e-mails written", to=campaign.recipient.email, files=len(paths))
        return SendResult(ok=True, reference=str(paths[0]) if paths else ref)

    def sync(self, since: datetime) -> list[InboundEvent]:
        return []


class InstantlySender:
    """Instantly API v2 (https://developer.instantly.ai).

    Each lead is added to one campaign with the fully rendered texts as custom
    variables. The Instantly sequence therefore only contains:

        Step 1 subject: {{subject}}            body: {{body_1}}
        Step 2 (+3 d)  subject: {{subject_fu}}  body: {{body_2}}
        Step 3 (+7 d)  subject: {{subject_fu}}  body: {{body_3}}

    so the copy stays versioned in this repository.
    """

    name = "instantly"
    BASE = "https://api.instantly.ai/api/v2"

    def __init__(self, api_key: str, campaign_id: str):
        self.campaign_id = campaign_id
        self.http = httpx.Client(base_url=self.BASE, timeout=30, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    def send(self, campaign: Campaign) -> SendResult:
        r = campaign.recipient
        variables = {
            "subject": campaign.messages[0].subject if campaign.messages else "",
            "subject_fu": campaign.messages[1].subject if len(campaign.messages) > 1 else "",
        }
        for m in campaign.messages:
            variables[f"body_{m.step}"] = m.body
        variables.update(campaign.variables)
        payload = {
            "campaign": self.campaign_id,
            "email": r.email,
            "first_name": r.first_name,
            "last_name": r.last_name,
            "company_name": r.company,
            "website": r.website,
            "custom_variables": variables,
            "skip_if_in_workspace": True,
            "skip_if_in_campaign": True,
        }
        try:
            resp = self.http.post("/leads", json=payload)
        except httpx.HTTPError as e:
            return SendResult(ok=False, error=str(e))
        if resp.status_code >= 400:
            return SendResult(ok=False, error=f"{resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return SendResult(ok=True, reference=data.get("id"))

    def sync(self, since: datetime) -> list[InboundEvent]:
        events: list[InboundEvent] = []
        # 1) replies (received e-mails in this campaign)
        try:
            resp = self.http.get("/emails", params={"campaign_id": self.campaign_id, "email_type": "received", "limit": 100})
            if resp.status_code < 400:
                for item in resp.json().get("items", []):
                    ts = _parse_ts(item.get("timestamp_created"))
                    if ts and ts < since:
                        continue
                    sender = (item.get("from_address_email") or "").lower()
                    body = item.get("body", {}) or {}
                    excerpt = (body.get("text") or "")[:400]
                    kind: str = "replied"
                    ue = item.get("ue_type")  # 1 = received, 2 = bounce, 3 = OOO, 4 = unsub (per docs)
                    if ue == 2:
                        kind = "bounced"
                    elif ue == 4 or _looks_like_unsubscribe(excerpt):
                        kind = "unsubscribed"
                    if sender:
                        events.append(InboundEvent(email=sender, kind=kind, at=ts or datetime.now(timezone.utc), excerpt=excerpt, reference=item.get("id")))
        except httpx.HTTPError as e:
            log.warning("instantly sync (emails) failed", err=str(e))
        # 2) lead-level interest status (set manually in Instantly or by its AI)
        try:
            resp = self.http.post("/leads/list", json={"campaign": self.campaign_id, "limit": 100})
            if resp.status_code < 400:
                for lead in resp.json().get("items", []):
                    email = (lead.get("email") or "").lower()
                    status = lead.get("lt_interest_status")
                    if status == 1:
                        events.append(InboundEvent(email=email, kind="interested", at=datetime.now(timezone.utc), reference=lead.get("id")))
                    elif status in (-1, -2, -3):  # not interested / wrong person / lost
                        events.append(InboundEvent(email=email, kind="not_interested", at=datetime.now(timezone.utc), reference=lead.get("id")))
        except httpx.HTTPError as e:
            log.warning("instantly sync (leads) failed", err=str(e))
        return events


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _looks_like_unsubscribe(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ("kein interesse", "nicht mehr kontaktieren", "keine weiteren", "abmelden", "unsubscribe", "nicht mehr anschreiben", "bitte streichen"))


def make_sender() -> Sender:
    s = get_settings()
    if s.SENDER_BACKEND == "instantly":
        if not (s.INSTANTLY_API_KEY and s.INSTANTLY_CAMPAIGN_ID):
            log.warning("SENDER_BACKEND=instantly but INSTANTLY_API_KEY/INSTANTLY_CAMPAIGN_ID missing – falling back to dry run")
            return DryRunSender()
        return InstantlySender(s.INSTANTLY_API_KEY, s.INSTANTLY_CAMPAIGN_ID)
    return DryRunSender()
