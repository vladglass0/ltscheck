"""Maintainer-утилита: обновить data/tools_manifest.json с mods.holyworld.me.

Кликает каждую кнопку «Скачать *» на /applications в stealth-браузере
(Cloudflare обходится автоматизацией, plain GET даёт 403) и пишет
пойманные прямые URL в манифест. Сами файлы НЕ качаются (запросы рвутся
после захвата URL). Требует `pip install 'scrapling[all]'` + браузеры.
"""
from __future__ import annotations

import json
import time

BIN = (".zip", ".exe", ".msi", ".rar", ".7z")
SKIP_HOSTS = ("yandex", "doubleclick", "gstatic", "google")


def resolve_manifest(click_pause: float = 4.0, timeout_ms: int = 60000) -> list[dict]:
    """Вернуть [{name, filename, urls}] для всех кнопок «Скачать»."""
    from scrapling.fetchers import StealthySession

    by_label: dict[str, list[str]] = {}
    order: list[str] = []
    with StealthySession(headless=True, solve_cloudflare=True, timeout=timeout_ms) as session:
        session.fetch("https://mods.holyworld.me/applications")
        pool = session.page_pool
        info = pool.pages[0] if isinstance(pool.pages, (list, tuple)) else list(pool.pages.values())[0]
        pg = info.page

        def on_req(r):
            u = r.url
            if u.lower().split("?", 1)[0].endswith(BIN) and not any(h in u for h in SKIP_HOSTS):
                cur = getattr(pg, "_lts_cur", None)
                if cur is not None and u not in by_label.get(cur, []):
                    by_label.setdefault(cur, []).append(u)

        def on_dl(d):
            cur = getattr(pg, "_lts_cur", None)
            if cur is not None and d.url not in by_label.get(cur, []):
                by_label.setdefault(cur, []).append(d.url)

        pg.on("request", on_req)
        pg.on("download", on_dl)

        def route(rt):
            u = rt.request.url
            if u.lower().split("?", 1)[0].endswith(BIN):
                rt.abort()  # URL уже захвачен — файл не тянем
            else:
                rt.continue_()

        pg.route("**/*", route)
        labels = pg.evaluate(
            """() => [...document.querySelectorAll('button')]
               .map(b => b.getAttribute('aria-label'))
               .filter(a => a && a.startsWith('Скачать'))""")
        for label in labels:
            order.append(label)
            by_label.setdefault(label, [])
            pg._lts_cur = label  # до клика: сетевые события придут уже с меткой
            pg.evaluate(
                """(label) => { const b = [...document.querySelectorAll('button')]
                   .find(x => x.getAttribute('aria-label') === label);
                   if (b) { b.scrollIntoView({block:'center'}); } }""", label)
            time.sleep(0.5)
            pg.evaluate(
                """(label) => { const b = [...document.querySelectorAll('button')]
                   .find(x => x.getAttribute('aria-label') === label);
                   if (b) b.click(); }""", label)
            time.sleep(click_pause)
        time.sleep(2)

    tools = []
    for label in order:
        name = label.replace("Скачать", "").strip()
        urls = by_label.get(label, [])
        fname = urls[0].rsplit("/", 1)[-1].split("?", 1)[0] if urls else ""
        tools.append({"name": name, "filename": fname, "urls": urls, "level": "ml"})
    return tools


def main(out_path: str, click_pause: float = 4.0) -> list[dict]:
    tools = resolve_manifest(click_pause=click_pause)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"generated_by": "tools resolve (Scrapling StealthySession, click mapping)",
                   "note": "Источники ссылок — кнопки «Скачать» на mods.holyworld.me/applications.",
                   "tools": tools}, f, ensure_ascii=False, indent=2)
    return tools
