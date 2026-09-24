"""Автозагрузчик тулзов мл. сотрудника.

Источники ссылок — кнопки «Скачать» на mods.holyworld.me/applications
(правило сайта: качать только оттуда). Сами URL хранятся в
data/tools_manifest.json и обновляются maintainer-командой
`tools resolve` (Scrapling + браузер, см. tools_resolve.py).
Здесь — только многопоточное скачивание: ретраи, докачка пропусков,
распаковка .zip в подпапку, отчёт ok/failed/skipped.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import tempfile
import time
import urllib.request
import zipfile

from . import rules

BASE = "https://mods.holyworld.me"
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tools_manifest.json")
UA = "ltscheck/1.0"


def load_manifest(path: str = MANIFEST_PATH) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("tools", [])
    except OSError:
        return []


def tool_manifest() -> list[dict]:
    """Manifest для отображения: сначала URL из tools_manifest.json, затем остаток из rules."""
    items = []
    known = {t["name"].lower(): t for t in load_manifest()}
    for t in rules.ML_TOOLS:
        item = {"name": t["name"], "use": t["use"], "page": f"{BASE}/applications"}
        if t["name"].lower() in known:
            item.update({k: known[t["name"].lower()][k] for k in ("urls", "filename") if k in known[t["name"].lower()]})
        items.append(item)
    items.append({"name": "Powershell-команды", "use": "check.txt/твинки/VM (ключ HolyJournal)",
                  "page": f"{BASE}/powershell"})
    items.append({"name": "Проверка модов (.jar)", "use": "залить моды игрока", "page": f"{BASE}/mods-review"})
    return items


def _fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _download_one(tool: dict, dest_dir: str, retries: int = 2, timeout: int = 60) -> dict:
    name = tool["name"]
    urls = tool.get("urls") or []
    if not urls:
        return {"tool": name, "status": "skipped", "reason": "нет URL (обнови tools_manifest.json через tools resolve)"}
    tdir = os.path.join(dest_dir, name.replace(" ", "_"))
    os.makedirs(tdir, exist_ok=True)
    last_err = ""
    for url in urls:  # зеркала по очереди
        fname = tool.get("filename") or url.rsplit("/", 1)[-1].split("?", 1)[0] or (name + ".bin")
        target = os.path.join(tdir, fname)
        for attempt in range(retries + 1):
            try:
                # пропуск если файл уже на месте и непустой
                if os.path.isfile(target) and os.path.getsize(target) > 0:
                    return _postprocess(tool, target, note="already there")
                fd, tmp = tempfile.mkstemp(prefix="ltsdl_", dir=tdir)
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=timeout) as r, os.fdopen(fd, "wb") as f:
                        shutil.copyfileobj(r, f, length=1024 * 256)
                except BaseException:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                    raise
                os.replace(tmp, target)
                return _postprocess(tool, target)
            except Exception as e:  # noqa: BLE001 — собираем в отчёт
                last_err = str(e)[:200]
                time.sleep(1 + attempt)
    return {"tool": name, "status": "failed", "error": last_err}


def _postprocess(tool: dict, target: str, note: str = "") -> dict:
    """Распаковать .zip в подпапку, посчитать sha256."""
    res: dict = {"tool": tool["name"], "status": "ok", "file": target}
    if note:
        res["note"] = note
    try:
        h = hashlib.sha256()
        with open(target, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 256), b""):
                h.update(chunk)
        res["sha256"] = h.hexdigest()[:16]
        res["size"] = os.path.getsize(target)
    except OSError as e:
        res["status"] = "failed"
        res["error"] = str(e)[:200]
        return res
    if target.lower().endswith(".zip"):
        sub = os.path.join(os.path.dirname(target), os.path.basename(target)[:-4])
        try:
            if not os.path.isdir(sub) or not os.listdir(sub):
                os.makedirs(sub, exist_ok=True)
                with zipfile.ZipFile(target) as z:
                    z.extractall(sub)
                res["unpacked_to"] = sub
        except Exception as e:  # noqa: BLE001
            res["status"] = "failed"
            res["error"] = f"unzip: {e}"[:200]
    if tool.get("sha256") and res.get("sha256") and tool["sha256"] != res["sha256"]:
        res["status"] = "failed"
        res["error"] = "sha256 mismatch"
    return res


def _tool_dir(dest_dir: str, name: str) -> str:
    return os.path.join(dest_dir, name.replace(" ", "_"))


def find_main_exe(tool: dict, dest_dir: str) -> str | None:
    """Найти запускаемый .exe тулзы: unpacked-подпапка или папка тулзы.
    Приоритет: manifest-поле exe > <ИмяТулзы>.exe > самый большой .exe."""
    tdir = _tool_dir(dest_dir, tool["name"])
    if not os.path.isdir(tdir):
        return None
    hint = (tool.get("exe") or "").lower()
    cands: list[tuple[int, str]] = []
    for dirpath, _dn, files in os.walk(tdir):
        for fn in files:
            if fn.lower().endswith(".exe"):
                p = os.path.join(dirpath, fn)
                try:
                    cands.append((os.path.getsize(p), p))
                except OSError:
                    pass
    if not cands:
        return None
    if hint:
        for _size, p in cands:
            if os.path.basename(p).lower() == hint:
                return p
    norm = tool["name"].lower().replace(" ", "")
    for _size, p in cands:
        if os.path.basename(p).lower().replace(" ", "") == norm + ".exe":
            return p
    cands.sort(key=lambda t: t[0], reverse=True)
    return cands[0][1]


def launch_tool(dest_dir: str, name: str) -> dict:
    """Запустить основной .exe тулзы (Windows: os.startfile, иначе detached Popen)."""
    import subprocess
    manifest = {t["name"].lower(): t for t in load_manifest()}
    tool = manifest.get(name.lower())
    if tool is None:
        return {"tool": name, "status": "failed", "error": "нет в манифесте"}
    exe = find_main_exe(tool, dest_dir)
    if exe is None:
        return {"tool": name, "status": "failed", "error": "не скачано (exe не найден)"}
    try:
        if os.name == "nt" and hasattr(os, "startfile"):
            os.startfile(exe)  # noqa: E1101
            return {"tool": name, "status": "launched", "exe": exe}
        p = subprocess.Popen([exe], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        return {"tool": name, "status": "launched", "exe": exe, "pid": p.pid}
    except Exception as e:  # noqa: BLE001
        return {"tool": name, "status": "failed", "error": str(e)[:200]}


def download_and_launch(dest_dir: str, name: str, workers: int = 1, retries: int = 2) -> dict:
    """Скачать тулзу если нет и сразу запустить."""
    manifest = {t["name"].lower(): t for t in load_manifest()}
    tool = manifest.get(name.lower())
    if tool is None:
        return {"tool": name, "status": "failed", "error": "нет в манифесте"}
    if find_main_exe(tool, dest_dir) is None:
        rep = download_tools(dest_dir, only=[tool["name"]], workers=workers, retries=retries)
        if rep["failed"]:
            return {"tool": name, "status": "failed",
                    "error": rep["failed"][0].get("error", "")}
    return launch_tool(dest_dir, name)


def download_tools(dest_dir: str, only: list[str] | None = None,
                   workers: int = 4, retries: int = 2) -> dict:
    """Скачать тулзы из манифеста. Возвращает {'ok': [...], 'failed': [...], 'skipped': [...]}."""
    os.makedirs(dest_dir, exist_ok=True)
    manifest = load_manifest()
    if only:
        want = {o.lower() for o in only}
        manifest = [t for t in manifest if t["name"].lower() in want]
    rep: dict = {"ok": [], "failed": [], "skipped": []}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_download_one, t, dest_dir, retries): t for t in manifest}
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            rep[r["status"]].append(r)
    for k in rep:
        rep[k].sort(key=lambda r: r.get("tool", ""))
    return rep
