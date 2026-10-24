"""Shared runtime helpers for investmcp provider modules."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import wraps
from pathlib import Path
from threading import RLock

YFINANCE_LOCK = RLock()


def synchronized(lock):
    """Guard short shared-state operations or one provider's synchronous work."""

    def decorate(fn):
        @wraps(fn)
        def guarded(*args, **kwargs):
            with lock:
                return fn(*args, **kwargs)

        return guarded

    return decorate


class NotConfiguredError(RuntimeError):
    """A provider is not configured; its tools cannot run until env vars are set."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(message)


def cache_dir() -> Path:
    """All persistent state belongs under the configured per-user data directory."""
    raw = os.environ.get("INVESTMCP_DATA_DIR", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".investmcp"


def retry_after_seconds(value: str | None) -> int | None:
    """Parse a bounded Retry-After without retaining arbitrary header text."""
    if not value:
        return None
    try:
        if value.isascii() and value.isdigit():
            delay = int(value)
        else:
            deadline = parsedate_to_datetime(value)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            delay = max(0, int((deadline - datetime.now(timezone.utc)).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return None
    return delay if 0 <= delay <= 86400 else None


def local_calendar_date(timestamp: str) -> str:
    """Convert an observation instant to the host calendar used by ledger windows.

    Date-only synthetic/legacy observations already name a local calendar day.
    Keep UTC timestamps intact in the response; convert only for date comparisons.
    """
    if not timestamp:
        return ""
    try:
        return (
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            .astimezone()
            .date()
            .isoformat()
        )
    except (ValueError, TypeError, AttributeError):
        return ""
