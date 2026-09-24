"""Whitelist с mods.holyworld.me через Scrapling (офлайн-first).

Сетевой refresh: StealthyFetcher + solve_cloudflare (plain GET даёт 403),
уважение к robots.txt, задержки. Без scrapling/сети — работаем по seed.
"""
from __future__ import annotations

import json
import os
import time
import urllib.robotparser as robotparser

from . import rules

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "whitelist_seed.json")

PAGES = ("visuals", "applications", "news")


def load_seed(path: str = SEED_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {"allowed_visuals": list(rules.ALLOWED_VISUALS),
                "banned_visuals": list(rules.BANNED_VISUALS),
                "tools": [t["name"] for t in rules.ML_TOOLS],
                "minimap_bans": list(rules.MINIMAP_BANS)}


def robots_allowed(url: str, ua: str = "ltscheck") -> bool:
    try:
        rp = robotparser.RobotFileParser()
        rp.set_url("https://mods.holyworld.me/robots.txt")
        rp.read()
        return rp.can_fetch(ua, url)
    except Exception:
        return True


def refresh_whitelist(out_path: str, delay_s: float = 3.0, timeout_ms: int = 60000) -> dict:
    """Сходить на сайт Scrapling-ом, сохранить JSON. Возвращает данные."""
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError as e:
        raise RuntimeError("нужен pip install 'scrapling[all]>=0.4.15'") from e
    data: dict = {"source": "mods.holyworld.me", "pages": {}}
    for page in PAGES:
        url = f"https://mods.holyworld.me/{page}"
        if not robots_allowed(url):
            data["pages"][page] = {"skipped": "robots.txt disallow"}
            continue
        time.sleep(delay_s)
        # ai_targeted=True режет мусор для LLM и включает adblock (требование скилла)
        fetched = StealthyFetcher.fetch(url, solve_cloudflare=True, timeout=timeout_ms)
        md = fetched.markdown() if hasattr(fetched, "markdown") else fetched.text
        data["pages"][page] = {"url": url, "markdown": (md or "")[:20000]}
    # нормализуем из правил (страницы JS-рендерные, эталон — rules + seed)
    seed = load_seed()
    data["allowed_visuals"] = seed.get("allowed_visuals", list(rules.ALLOWED_VISUALS))
    data["banned_visuals"] = seed.get("banned_visuals", list(rules.BANNED_VISUALS))
    data["tools"] = seed.get("tools", [t["name"] for t in rules.ML_TOOLS])
    data["minimap_bans"] = seed.get("minimap_bans", list(rules.MINIMAP_BANS))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
