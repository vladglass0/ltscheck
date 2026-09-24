"""Recaf-lite: статический разбор .jar без запуска (мануал запрещает запуск у себя)."""
from __future__ import annotations

import json
import os
import zipfile

from . import rules
from .report import Finding
from .utils import fmt_mtime

MOD = "jar"


def _read_text_from_zip(z: zipfile.ZipFile, name: str) -> str:
    try:
        return z.read(name).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def mod_meta(path: str) -> dict:
    meta: dict = {"file": os.path.basename(path)}
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for n in names:
                if n.endswith("fabric.mod.json"):
                    try:
                        d = json.loads(_read_text_from_zip(z, n))
                        meta["loader"] = "fabric"
                        meta["id"] = d.get("id")
                        meta["version"] = d.get("version")
                    except Exception:
                        pass
                if n.endswith("mods.toml"):
                    meta["loader"] = "forge"
                    txt = _read_text_from_zip(z, n)
                    for line in txt.splitlines():
                        s = line.strip()
                        if s.startswith("modId"):
                            meta["id"] = s.split("=", 1)[-1].strip().strip('"')
                        if s.startswith("version") and "version" not in meta:
                            meta["version"] = s.split("=", 1)[-1].strip().strip('"')
    except Exception as e:
        meta["error"] = str(e)
    return meta


def analyze_jar(path: str) -> list[Finding]:
    out: list[Finding] = []
    try:
        with zipfile.ZipFile(path) as z:
            names = [n.lower() for n in z.namelist()]
    except Exception as e:
        return [Finding("WARN", MOD, "jar-unreadable", path, f"не открылся как zip: {e}", fmt_mtime(path))]
    blob = "\n".join(names)
    # думик
    if all(m.lower() in blob for m in rules.JAR_DUMIK_MARKERS):
        try:
            if rules.JAR_DUMIK_SIZE_RANGE[0] <= os.path.getsize(path) <= rules.JAR_DUMIK_SIZE_RANGE[1]:
                out.append(Finding("BAN", MOD, "jar-dumik", path, "думик s.class+f.class", fmt_mtime(path)))
        except OSError:
            pass
    for marker in rules.JAR_CHEAT_CLASS_MARKERS:
        if marker in blob:
            out.append(Finding("BAN", MOD, "jar-cheat-class", path,
                               f"класс ЗПО '{marker}' (KillAura/AutoAttack/Freecam...)", fmt_mtime(path)))
            break
    hit_found = [m for m in rules.JAR_HITBOX_MARKERS if m in blob]
    if hit_found:
        out.append(Finding("WARN", MOD, "jar-hitbox", path,
                           "хитбоксы/оптимайзер/сваппер маркеры: " + ", ".join(sorted(set(hit_found))),
                           fmt_mtime(path)))
    # обфускация: много однобуквенных классов вида a/b/c.class или aaa112
    short = sum(1 for n in names if n.endswith(".class") and len(n.rsplit("/", 1)[-1]) <= 7)
    total = sum(1 for n in names if n.endswith(".class"))
    if total >= 20 and short / total > 0.6:
        out.append(Finding("WARN", MOD, "jar-obfuscated", path,
                           f"похоже на обфускацию {short}/{total} коротких классов — "
                           "норма только для коммерческих визуалов, иначе бан", fmt_mtime(path)))
    if not out:
        out.append(Finding("INFO", MOD, "jar-clean", path, f"статика чиста {total} классов", fmt_mtime(path)))
    return out
