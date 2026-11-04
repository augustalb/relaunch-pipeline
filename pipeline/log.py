"""Structured logging. Plain text in dev, JSON lines when LOG_JSON=true (GitHub Actions)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

_configured = False


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "ctx", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = f"{datetime.now().strftime('%H:%M:%S')} {record.levelname:<7} {record.name}: {record.getMessage()}"
        extra = getattr(record, "ctx", None)
        if extra:
            base += " " + " ".join(f"{k}={v}" for k, v in extra.items())
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure_logging(level: str = "INFO", as_json: bool = False) -> None:
    global _configured
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter() if as_json else _TextFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> "ContextLogger":
    return ContextLogger(logging.getLogger(name))


class ContextLogger:
    """Thin wrapper so call sites can pass key/value context: log.info("sent", lead=3)."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log(self, level: int, msg: str, exc_info=None, **ctx):
        if self._logger.isEnabledFor(level):
            self._logger.log(level, msg, exc_info=exc_info, extra={"ctx": ctx} if ctx else None)

    def debug(self, msg, **ctx):
        self._log(logging.DEBUG, msg, **ctx)

    def info(self, msg, **ctx):
        self._log(logging.INFO, msg, **ctx)

    def warning(self, msg, **ctx):
        self._log(logging.WARNING, msg, **ctx)

    def error(self, msg, exc_info=None, **ctx):
        self._log(logging.ERROR, msg, exc_info=exc_info, **ctx)
