"""Общие утилиты: даты, обход дерева, чтение файлов."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta


def resource_path(*parts: str) -> str:
    """Путь к данным: во frozen-сборке — sys._MEIPASS, иначе корень репо."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, *parts)  # type: ignore[attr-defined]
    return os.path.join(os.path.dirname(__file__), "..", *parts)


def days_old(mtime_ts: float, now: datetime | None = None) -> float:
    now = now or datetime.now()
    return (now - datetime.fromtimestamp(mtime_ts)).total_seconds() / 86400.0


def is_fresh(path: str, days: int = 14) -> bool:
    try:
        return days_old(os.path.getmtime(path)) < days
    except OSError:
        return False


def fmt_mtime(path: str) -> str:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return ""


def iter_files(root: str):
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def read_head(path: str, size: int = 2_000_000) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(size)
    except OSError:
        return b""


def fresh_cutoff(days: int = 14) -> datetime:
    return datetime.now() - timedelta(days=days)
