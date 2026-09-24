"""CLI: python -m ltscheck.cli <scan-mc|scan-fs|analyze-jar|parse-checktxt|full|tools|whitelist-refresh|gui>."""
from __future__ import annotations

import argparse
import os
import sys

from .checktxt import parse_checktxt
from .fs_scan import audit_fs
from .jar_analyze import analyze_jar
from .mc_audit import audit_mc
from .report import Report


def _write_outputs(rep: Report, out: str | None, json_path: str | None) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(rep.to_html())
    if json_path:
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(rep.to_json())


def _exit_for(rep: Report) -> int:
    return {"CLEAN": 0, "WARN": 1, "BAN": 2}[rep.verdict]


def cmd_scan_mc(a: argparse.Namespace) -> int:
    rep = Report(target=a.mc_dir)
    rep.extend(audit_mc(a.mc_dir))
    print(rep.to_text())
    _write_outputs(rep, a.out, a.json)
    return _exit_for(rep)


def cmd_scan_fs(a: argparse.Namespace) -> int:
    rep = Report(target=a.scan_root)
    rep.extend(audit_fs(a.scan_root))
    print(rep.to_text())
    _write_outputs(rep, a.out, a.json)
    return _exit_for(rep)


def cmd_jar(a: argparse.Namespace) -> int:
    rep = Report(target=a.jar)
    rep.extend(analyze_jar(a.jar))
    print(rep.to_text())
    _write_outputs(rep, a.out, a.json)
    return _exit_for(rep)


def cmd_checktxt(a: argparse.Namespace) -> int:
    rep = Report(target=a.checktxt)
    rep.extend(parse_checktxt(a.checktxt))
    print(rep.to_text())
    _write_outputs(rep, a.out, a.json)
    return _exit_for(rep)


def cmd_full(a: argparse.Namespace) -> int:
    rep = Report(target=a.mc_dir or a.scan_root)
    if a.mc_dir:
        rep.extend(audit_mc(a.mc_dir))
        # все .jar из mods — статикой
        mods = os.path.join(a.mc_dir, "mods")
        if os.path.isdir(mods):
            for fn in os.listdir(mods):
                if fn.lower().endswith(".jar"):
                    rep.extend(analyze_jar(os.path.join(mods, fn)))
    if a.scan_root:
        rep.extend(audit_fs(a.scan_root))
    if a.checktxt:
        rep.extend(parse_checktxt(a.checktxt))
    print(rep.to_text())
    _write_outputs(rep, a.out, a.json)
    return _exit_for(rep)


def cmd_tools(a: argparse.Namespace) -> int:
    from .tools import download_tools, tool_manifest
    if a.list:
        for t in tool_manifest():
            urls = t.get("urls") or []
            print(f"- {t['name']}: {t['use']} ({urls[0] if urls else t.get('page', 'no url')})")
        return 0
    if a.resolve:
        from .tools_resolve import main as resolve_main
        tools = resolve_main(a.resolve)
        print(f"resolved {len(tools)} -> {a.resolve}")
        print("ВНИМАНИЕ: подписанные release-assets ссылки GitHub живут ~1 час — "
              "вручную замени их на stable releases/download перед коммитом.")
        return 0
    res = download_tools(a.dest, only=a.only, workers=a.workers)
    print(f"ok={len(res['ok'])} failed={len(res['failed'])} skipped={len(res['skipped'])}")
    for f in res["failed"]:
        print("FAIL", f.get("tool"), f.get("error"))
    for s in res["skipped"]:
        print("SKIP", s.get("tool"), s.get("reason"))
    return 0 if not res["failed"] else 1


def cmd_whitelist(a: argparse.Namespace) -> int:
    if a.offline:
        from .whitelist import load_seed
        import json
        data = load_seed()
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"seed -> {a.out}")
        return 0
    from .whitelist import refresh_whitelist
    data = refresh_whitelist(a.out)
    print(f"refreshed -> {a.out}, pages={list(data.get('pages', {}))}")
    return 0


def cmd_gen_ps1(a: argparse.Namespace) -> int:
    from .checktxt_gen import write_ps1
    print(write_ps1(a.out))
    return 0


def cmd_gui(a: argparse.Namespace) -> int:
    try:
        from .gui import run
    except ImportError as e:
        print(f"для GUI нужен flet>=1.0: pip install flet ({e})")
        return 3
    run(view=a.view)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ltscheck", description="HolyWorld check automation (мл. сотрудник)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_out(sp):
        sp.add_argument("--out", default=None, help="HTML-отчёт")
        sp.add_argument("--json", default=None, help="JSON-отчёт")

    s = sub.add_parser("scan-mc", help="аудит .minecraft"); s.add_argument("--mc-dir", required=True); add_out(s); s.set_defaults(f=cmd_scan_mc)
    s = sub.add_parser("scan-fs", help="Everything-скан дерева"); s.add_argument("--scan-root", required=True); add_out(s); s.set_defaults(f=cmd_scan_fs)
    s = sub.add_parser("analyze-jar", help="статика .jar"); s.add_argument("--jar", required=True); add_out(s); s.set_defaults(f=cmd_jar)
    s = sub.add_parser("parse-checktxt", help="разбор check.txt"); s.add_argument("--checktxt", required=True); add_out(s); s.set_defaults(f=cmd_checktxt)
    s = sub.add_parser("gen-ps1", help="создать check.ps1 для запуска на ПК игрока"); s.add_argument("--out", default="check.ps1"); s.set_defaults(f=cmd_gen_ps1)
    s = sub.add_parser("full", help="всё сразу")
    s.add_argument("--mc-dir", default=None); s.add_argument("--scan-root", default=None)
    s.add_argument("--checktxt", default=None); add_out(s); s.set_defaults(f=cmd_full)
    s = sub.add_parser("tools", help="загрузчик тулзов")
    s.add_argument("--list", action="store_true")
    s.add_argument("--dest", default="tools")
    s.add_argument("--only", nargs="*", default=None, help="только эти тулзы")
    s.add_argument("--resolve", default=None, metavar="OUT_JSON",
                   help="maintainer: перемапить URL кликами в браузере")
    s.add_argument("--workers", type=int, default=4); s.set_defaults(f=cmd_tools)
    s = sub.add_parser("whitelist-refresh", help="обновить whitelist с mods.holyworld.me")
    s.add_argument("--out", default="data/whitelist.json"); s.add_argument("--offline", action="store_true")
    s.set_defaults(f=cmd_whitelist)
    s = sub.add_parser("gui", help="Flet GUI (мл. сотрудник)")
    s.add_argument("--view", choices=("app", "web"), default="app",
                   help="app — отдельное окно, web — вкладка браузера (если нет дисплея)")
    s.set_defaults(f=cmd_gui)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
