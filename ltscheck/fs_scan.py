"""Everything-замена: скан дерева по ключевым словам + сигнатуры размеров/контента."""
from __future__ import annotations

import os
import zipfile

from . import rules
from .report import Finding
from .utils import fmt_mtime, is_fresh, read_head

MOD = "fs"

_ARCHIVE_NAMES = (".jar", ".zip", ".rar")


def _is_storage(name: str) -> bool:
    n = name.lower()
    return any(n.endswith(e) for e in rules.STORAGE_EXTS)


def scan_keywords(scan_root: str) -> list[Finding]:
    out: list[Finding] = []
    kws = [k.lower() for k in rules.EVERYTHING_KEYWORDS]
    for dirpath, dirnames, filenames in os.walk(scan_root):
        # папки
        for d in list(dirnames):
            dl = d.lower()
            for kw in kws:
                if kw and kw in dl:
                    p = os.path.join(dirpath, d)
                    if _is_storage(d):
                        out.append(Finding("BAN", MOD, "keyword-storage", p,
                                           f"хранение: имя содержит '{kw}'", fmt_mtime(p)))
                    elif is_fresh(p, rules.RESIDUE_DAYS):
                        out.append(Finding("BAN", MOD, "keyword-residue", p,
                                           f"остаток '{kw}' <14д", fmt_mtime(p)))
                    else:
                        out.append(Finding("INFO", MOD, "keyword-old", p,
                                           f"'{kw}' старше 14д", fmt_mtime(p)))
                    break
        for fn in filenames:
            fl = fn.lower()
            for kw in kws:
                if kw and kw in fl:
                    p = os.path.join(dirpath, fn)
                    if _is_storage(fn):
                        # .lnk с названием ЗПО — по дате; остальное хранение — всегда бан
                        if fl.endswith(".lnk"):
                            if is_fresh(p, rules.RESIDUE_DAYS):
                                out.append(Finding("BAN", MOD, "lnk-cheat", p,
                                                   f"ярлык ЗПО '{kw}' <14д", fmt_mtime(p)))
                            else:
                                out.append(Finding("INFO", MOD, "lnk-cheat-old", p,
                                                   f"ярлык ЗПО '{kw}' старше 14д", fmt_mtime(p)))
                        else:
                            out.append(Finding("BAN", MOD, "keyword-storage", p,
                                               f"хранение: имя содержит '{kw}'", fmt_mtime(p)))
                    elif is_fresh(p, rules.RESIDUE_DAYS):
                        out.append(Finding("BAN", MOD, "keyword-residue", p,
                                           f"остаток '{kw}' <14д", fmt_mtime(p)))
                    else:
                        out.append(Finding("INFO", MOD, "keyword-old", p,
                                           f"'{kw}' старше 14д", fmt_mtime(p)))
                    break
            # shellbag-чистка
            if fl == "shellbag_analyzer_cleaner.ini":
                out.append(Finding("BAN", MOD, "shellbag-cleaner", os.path.join(dirpath, fn),
                                   "чистка shellbag", fmt_mtime(os.path.join(dirpath, fn))))
    return out


def _has_all_markers_zip(path: str, markers: tuple[str, ...]) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            names = [n.lower() for n in z.namelist()]
            blob = "\n".join(names)
            # думик: ищем s.class и f.class в net/java/
            return all(m.lower() in blob for m in markers)
    except Exception:
        return False


def scan_signatures(scan_root: str) -> list[Finding]:
    out: list[Finding] = []
    for dirpath, _dn, files in os.walk(scan_root):
        for fn in files:
            p = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            fl = fn.lower()
            # vec.dll: ~30kb
            if abs(size - rules.VEC_DLL_SIZE) <= rules.VEC_DLL_SIZE_TOL:
                head = read_head(p, 200000).lower()
                if rules.VEC_CONTENT_MARKER in head:
                    out.append(Finding("BAN", MOD, "vec-dll", p,
                                       "vec.dll 30kb + axisalignedbb", fmt_mtime(p)))
            # mp3-хиты
            if abs(size - rules.MP3_HITS_SIZE) <= rules.MP3_HITS_TOL:
                out.append(Finding("WARN", MOD, "mp3-hits", p,
                                   "вес 9400174 — проверить PID-краш тестом из мануала", fmt_mtime(p)))
            # exe точные веса
            if fl.endswith(".exe") and size in rules.EXE_SUSPICIOUS_SIZES:
                out.append(Finding("WARN", MOD, "exe-size", p,
                                   f"подозрительный вес exe {size} — запустить и проверить", fmt_mtime(p)))
            # exe fml/glowEsp 700kb..5mb
            if fl.endswith(".exe") and rules.EXE_FML_SIZE_RANGE[0] <= size <= rules.EXE_FML_SIZE_RANGE[1]:
                head = read_head(p)
                if any(m in head for m in rules.EXE_FML_MARKERS):
                    out.append(Finding("BAN", MOD, "exe-fml", p, "FMLLoader/glowEsp в exe 700kb-5mb", fmt_mtime(p)))
            # exe d3d 14..17mb
            if fl.endswith(".exe") and rules.EXE_D3D_SIZE_RANGE[0] <= size <= rules.EXE_D3D_SIZE_RANGE[1]:
                head = read_head(p)
                if any(m in head for m in rules.EXE_D3D_MARKERS):
                    out.append(Finding("WARN", MOD, "exe-d3d", p,
                                       "D3D11/LoadLibraryA в exe 14-17mb — запустить", fmt_mtime(p)))
            # jar-думик 21kb..10mb + s.class/f.class
            if fl.endswith((".jar",)) and rules.JAR_DUMIK_SIZE_RANGE[0] <= size <= rules.JAR_DUMIK_SIZE_RANGE[1]:
                if _has_all_markers_zip(p, rules.JAR_DUMIK_MARKERS):
                    out.append(Finding("BAN", MOD, "jar-dumik", p, "думик: s.class+f.class", fmt_mtime(p)))
            # dll запрет. веса (SystemInformer Modules/Unloaded)
            if fl.endswith(".dll"):
                mb = size / (1024 * 1024)
                for ref, label in rules.DLL_FORBIDDEN_MB.items():
                    if abs(mb - ref) <= rules.DLL_WEIGHT_TOLERANCE_MB:
                        out.append(Finding("BAN", MOD, "dll-weight", p,
                                           f"{mb:.2f}MB ≈ {ref}MB ({label})", fmt_mtime(p)))
                        break
    return out


def audit_fs(scan_root: str) -> list[Finding]:
    if not os.path.isdir(scan_root):
        return [Finding("WARN", MOD, "no-root", scan_root, "папки для скана нет")]
    out = scan_keywords(scan_root)
    out += scan_signatures(scan_root)
    if not out:
        out.append(Finding("INFO", MOD, "fs-clean", scan_root, "подозрительных файлов нет"))
    return out
