from __future__ import annotations

from datetime import datetime


def now_local() -> datetime:
    return datetime.now().astimezone()


def iso_timestamp() -> str:
    return now_local().isoformat(timespec="seconds")


def filename_timestamp() -> str:
    return now_local().strftime("%Y%m%d_%H%M%S")
