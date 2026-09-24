"""Аудит папки игры (.minecraft) — уровень мл. сотрудник.

Покрывает manual.md: корень, versions (веса), mods (+Via), config (остатки 14д),
libraries-остатки, resourcepacks (xray), logs (читы/connecting/setting user),
screenshots за 14 дней, addons, lunar/profiles.
"""
from __future__ import annotations

import gzip
import os
import re
import zipfile

from . import rules
from .report import Finding
from .utils import fmt_mtime, is_fresh

MOD = "mc"


def _norm(s: str) -> str:
    return s.lower().replace(" ", "").replace("-", "").replace("_", "")


def _mod_name_hit(filename: str) -> str | None:
    n = _norm(filename)
    for banned in rules.BANNED_MODS:
        b = _norm(banned)
        if b and b in n:
            return banned
    return None


def _via_verdict(filename: str) -> tuple[str, str] | None:
    n = filename.lower()
    for b in rules.VIA_BANNED:
        if b in n:
            return ("BAN", f"запрещённый Via-мод {b} (мануал: ViaBackwards/ViaForge/ViaProxy = бан)")
    for s in rules.VIA_SUSPICIOUS:
        if s in n and not any(a in n for a in rules.VIA_ALLOWED):
            return ("WARN", f"подозрительный Via-мод {s}, уточнить у ответственного")
    return None


def audit_root(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    try:
        entries = os.listdir(mc_dir)
    except OSError as e:
        return [Finding("WARN", MOD, "root-unreadable", mc_dir, str(e))]
    # shellbag-чистка маркеры
    for e in entries:
        el = e.lower()
        if el == "shellbag_analyzer_cleaner.ini":
            out.append(Finding("BAN", MOD, "shellbag-cleaner", os.path.join(mc_dir, e),
                               "остаток чистки shellbag", fmt_mtime(os.path.join(mc_dir, e))))
        if el == "shellbag backups" and os.path.isdir(os.path.join(mc_dir, e)):
            out.append(Finding("BAN", MOD, "shellbag-cleaner", os.path.join(mc_dir, e),
                               "папка Shellbag Backups = чистка", fmt_mtime(os.path.join(mc_dir, e))))
    # папки с названием читов — остатки (<14 дней = бан)
    lowered = {e.lower(): e for e in entries}
    for kw in rules.EVERYTHING_KEYWORDS:
        k = kw.lower()
        if k in lowered:
            p = os.path.join(mc_dir, lowered[k])
            if os.path.isdir(p):
                if is_fresh(p, rules.RESIDUE_DAYS):
                    out.append(Finding("BAN", MOD, "cheat-folder", p,
                                       f"остаток '{kw}' <14 дней", fmt_mtime(p)))
                else:
                    out.append(Finding("INFO", MOD, "cheat-folder-old", p,
                                       f"остаток '{kw}' старше 14 дней", fmt_mtime(p)))
    return out


def _match_version_weight(dirname: str) -> int | None:
    d = dirname.lower()
    # сначала точные длинные ключи
    for ver in sorted(rules.VERSION_WEIGHTS_EXACT_KB, key=len, reverse=True):
        if ver in d:
            return rules.VERSION_WEIGHTS_EXACT_KB[ver]
    return None


def audit_versions(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    vdir = os.path.join(mc_dir, "versions")
    if not os.path.isdir(vdir):
        return [Finding("INFO", MOD, "no-versions", vdir, "папки versions нет")]
    for entry in os.listdir(vdir):
        ep = os.path.join(vdir, entry)
        if not os.path.isdir(ep):
            continue
        el = entry.lower()
        # папка с названием софта — остаток
        hit = _mod_name_hit(entry)
        if hit and is_fresh(ep, rules.RESIDUE_DAYS):
            out.append(Finding("BAN", MOD, "version-folder-cheat", ep,
                               f"папка версии с названием ЗПО '{hit}' <14д", fmt_mtime(ep)))
        # содержимое: .jar версии
        try:
            files = os.listdir(ep)
        except OSError:
            continue
        jars = [f for f in files if f.lower().endswith(".jar")]
        for j in jars:
            jp = os.path.join(ep, j)
            jl = j.lower()
            jhit = _mod_name_hit(j)
            if jhit:
                out.append(Finding("BAN", MOD, "version-jar-cheat", jp,
                                   f"хранение: .jar версии с названием ЗПО '{jhit}'", fmt_mtime(jp)))
                continue
            if any(x in jl for x in rules.VERSION_WEIGHT_EXEMPT_SUBSTR):
                out.append(Finding("INFO", MOD, "version-exempt", jp,
                                   "labymod/prosto/blclient/lunar — вес не судим", fmt_mtime(jp)))
                continue
            expected = _match_version_weight(entry) or _match_version_weight(j)
            if expected is None:
                # визуалы/кастом: WARN чтобы запустили и проверили функционал
                if any(x in jl for x in ("visual", "topka", "fever", "celestial", "astra")):
                    out.append(Finding("WARN", MOD, "version-custom", jp,
                                       "кастомная версия/визуал — запустить и проверить функционал", fmt_mtime(jp)))
                else:
                    out.append(Finding("INFO", MOD, "version-unknown", jp,
                                       "версия вне таблицы 1.16-1.20.2, вес не с чем сравнить", fmt_mtime(jp)))
                continue
            try:
                kb = os.path.getsize(jp) / 1024.0
            except OSError:
                continue
            if kb > expected * rules.VERSION_OVERWEIGHT_TOLERANCE:
                out.append(Finding("BAN", MOD, "version-overweight", jp,
                                   f"чит в версии: {kb:.0f}КБ > эталон {expected}КБ", fmt_mtime(jp)))
    return out


def _audit_mod_dir(d: str, label: str) -> list[Finding]:
    out: list[Finding] = []
    if not os.path.isdir(d):
        return []
    for fn in os.listdir(d):
        p = os.path.join(d, fn)
        if not os.path.isfile(p):
            continue
        fl = fn.lower()
        via = _via_verdict(fn)
        if via:
            out.append(Finding(via[0], MOD, "via-mod", p, via[1], fmt_mtime(p)))
            continue
        hit = _mod_name_hit(fn)
        if hit:
            out.append(Finding("BAN", MOD, "banned-mod", p,
                               f"запрещённый мод '{hit}' (хранение)", fmt_mtime(p)))
            continue
        # миникарты из news
        if "xaero" in fl and "minimap" in fl:
            m = re.search(r"(\d+)\.(\d+)\.(\d+)", fn)
            if m and (int(m.group(1)), int(m.group(2)), int(m.group(3))) >= (25, 3, 0):
                out.append(Finding("BAN", MOD, "minimap-banned", p,
                                   "Xaero Minimap >=25.3.0 запрещён (инвиз)", fmt_mtime(p)))
            else:
                out.append(Finding("WARN", MOD, "minimap-check", p,
                                   "миникарта: сверьте версию с /news (Xaero/LabyMod4/VoxelMap)", fmt_mtime(p)))
        elif "voxelmap" in fl or ("labymod" in fl and "minimap" in fl):
            out.append(Finding("WARN", MOD, "minimap-check", p,
                               "миникарта: сверьте с запретами /news", fmt_mtime(p)))
        # визуалы из whitelist
        for bv in rules.BANNED_VISUALS:
            if bv.replace(" ", "") in fl.replace(" ", "").replace("_", "").replace("-", ""):
                out.append(Finding("BAN", MOD, "banned-visual", p,
                                   f"запрещённый визуал '{bv}'", fmt_mtime(p)))
                break
    return out


def audit_mods(mc_dir: str) -> list[Finding]:
    out = _audit_mod_dir(os.path.join(mc_dir, "mods"), "mods")
    out += _audit_mod_dir(os.path.join(mc_dir, "LabyMod", "addons-1.16"), "addons")
    out += _audit_mod_dir(os.path.join(mc_dir, "labymod-neo", "addons"), "addons-neo")
    # lunar profiles
    lunar = os.path.join(mc_dir, "..", ".lunarclient", "profiles")
    lunar = os.path.normpath(lunar)
    if os.path.isdir(lunar):
        for profile in os.listdir(lunar):
            out += _audit_mod_dir(os.path.join(lunar, profile), f"lunar/{profile}")
    # абсолютный .lunarclient рядом с домом тоже пробуем
    alt = os.path.expanduser(os.path.join("~", ".lunarclient", "profiles"))
    if alt != lunar and os.path.isdir(alt):
        for profile in os.listdir(alt):
            out += _audit_mod_dir(os.path.join(alt, profile), f"lunar/{profile}")
    if not out:
        out.append(Finding("INFO", MOD, "mods-clean", os.path.join(mc_dir, "mods"), "подозрительных модов не найдено"))
    return out


def audit_configs(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    cdir = os.path.join(mc_dir, "config")
    if not os.path.isdir(cdir):
        return []
    for dirpath, _dn, files in os.walk(cdir):
        for fn in files:
            hit = _mod_name_hit(fn)
            if hit:
                p = os.path.join(dirpath, fn)
                if is_fresh(p, rules.RESIDUE_DAYS):
                    out.append(Finding("BAN", MOD, "config-leftover", p,
                                       f"конфиг ЗПО '{hit}' <14д", fmt_mtime(p)))
                else:
                    out.append(Finding("INFO", MOD, "config-leftover-old", p,
                                       f"конфиг ЗПО '{hit}' старше 14д", fmt_mtime(p)))
    return out


def audit_libraries(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    for parts, label in rules.LIBRARY_LEFTOVERS:
        p = os.path.join(mc_dir, *parts)
        if os.path.exists(p):
            if is_fresh(p, rules.RESIDUE_DAYS):
                out.append(Finding("BAN", MOD, "library-leftover", p, f"{label} <14д", fmt_mtime(p)))
            else:
                out.append(Finding("INFO", MOD, "library-leftover-old", p, f"{label} старше 14д", fmt_mtime(p)))
    return out


def audit_resourcepacks(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    rdir = os.path.join(mc_dir, "resourcepacks")
    if not os.path.isdir(rdir):
        return []
    for fn in os.listdir(rdir):
        fl = fn.lower()
        if "xray" in fl or "x-ray" in fl:
            out.append(Finding("BAN", MOD, "xray-pack", os.path.join(rdir, fn),
                               "ресурспак xray (бан даже по иконке/названию/описанию)", fmt_mtime(os.path.join(rdir, fn))))
            continue
        if fn.lower().endswith(".zip"):
            p = os.path.join(rdir, fn)
            try:
                with zipfile.ZipFile(p) as z:
                    names = " ".join(z.namelist()).lower()
                    if "xray" in names:
                        out.append(Finding("BAN", MOD, "xray-pack-content", p, "xray внутри архива", fmt_mtime(p)))
            except Exception:
                pass
    return out


def _read_log_lines(path: str) -> list[str]:
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
                return f.read().splitlines()
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines()
    except OSError:
        return []


def audit_logs(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    ldir = os.path.join(mc_dir, "logs")
    if not os.path.isdir(ldir):
        return []
    twinks: set[str] = set()
    for fn in os.listdir(ldir):
        if not (fn.endswith(".log") or fn.endswith(".log.gz")):
            continue
        p = os.path.join(ldir, fn)
        # логи старше 14 дней пропускаем (кроме твинков? твинки собираем все равно)
        lines = _read_log_lines(p)
        for line in lines:
            ll = line.lower()
            for kw in rules.LOG_CHEAT_KEYWORDS:
                if kw in ll and ("xray" in kw or "impact" in kw or kw in ("baritone", "celestial", "nursultan", "akrien")):
                    # xray может быть просто словом — требуем контекст чата/лога мода
                    out.append(Finding("WARN", MOD, "log-cheat-keyword", p, f"строка с '{kw}': {line.strip()[:160]}", fmt_mtime(p)))
                    break
            if rules.LOG_CONNECT_MARKER in ll:
                m = re.search(r"connecting to\s+([0-9]{1,3}(?:\.[0-9]{1,3}){3})", ll)
                if m:
                    out.append(Finding("BAN", MOD, "log-bypass-ip", p,
                                       f"connecting to {m.group(1)} + дальше сообщения HolyWorld = обход", fmt_mtime(p)))
            if rules.LOG_USER_MARKER in line:
                m = re.search(r"setting user:\s*(.+)$", line)
                if m:
                    twinks.add(m.group(1).strip())
    if twinks:
        out.append(Finding("INFO", MOD, "log-twinks", ldir, "твинки из логов: " + ", ".join(sorted(twinks))))
    if not out:
        out.append(Finding("INFO", MOD, "logs-clean", ldir, "подозрительных строк нет"))
    return out


def audit_screenshots(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    sdir = os.path.join(mc_dir, "screenshots")
    if not os.path.isdir(sdir):
        return []
    recent = [os.path.join(sdir, f) for f in os.listdir(sdir)
              if os.path.isfile(os.path.join(sdir, f)) and is_fresh(os.path.join(sdir, f), rules.RESIDUE_DAYS)]
    out.append(Finding("INFO", MOD, "screenshots", sdir,
                       f"скриншотов за 14 дней: {len(recent)} — проверить вручную: F3-версия, чат читов, трассеры/хитбоксы, freecam"))
    return out


def audit_mc(mc_dir: str) -> list[Finding]:
    out: list[Finding] = []
    out += audit_root(mc_dir)
    out += audit_versions(mc_dir)
    out += audit_mods(mc_dir)
    out += audit_configs(mc_dir)
    out += audit_libraries(mc_dir)
    out += audit_resourcepacks(mc_dir)
    out += audit_logs(mc_dir)
    out += audit_screenshots(mc_dir)
    return out
