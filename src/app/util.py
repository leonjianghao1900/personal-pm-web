"""Small shared helpers. Timestamps are stored as UTC text."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# The ported UI is Chinese and the desktop app used the operator's local day
# for "this month". Shanghai keeps that dashboard boundary stable on Workers,
# which otherwise run in UTC.
# Asia/Shanghai has no DST; fixed offset avoids needing tzdata on Pyodide.
APP_ZONE = timezone(timedelta(hours=8), "Asia/Shanghai")


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")


def today_local() -> date:
    return datetime.now(APP_ZONE).date()


def chunks(items: list, size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]
