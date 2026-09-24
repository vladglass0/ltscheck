"""Flet GUI (мл. сотрудник): проверка дампа, разбор .jar, тулзы.

Запуск: `python -m ltscheck.cli gui`. Требует `pip install "flet>=1.0"`.
Тяжёлые сканы уходят в `page.run_thread` (в 1.0 блокировать UI нельзя).
FilePicker 1.0.1 — сервис в `page.services`, методы синхронные,
сразу возвращают результат (`str | None` / `list[FilePickerFile]`).
"""
from __future__ import annotations

from .mc_audit import audit_mc
from .fs_scan import audit_fs
from .jar_analyze import analyze_jar, mod_meta
from .checktxt import parse_checktxt
from .report import Report
from . import rules


def _findings_table(findings, limit: int = 500):
    import flet as ft
    rows = []
    for f in findings[:limit]:
        color = {"BAN": ft.Colors.RED_400, "WARN": ft.Colors.ORANGE_400}.get(f.level)
        rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(f.level, color=color, weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(f.module)),
            ft.DataCell(ft.Text(f.rule)),
            ft.DataCell(ft.Text(f.path)),
            ft.DataCell(ft.Text(f"{f.detail} {f.mtime}".strip())),
        ]))
    return ft.DataTable(
        columns=[ft.DataColumn(ft.Text(c)) for c in ("Уровень", "Модуль", "Правило", "Путь", "Детали")],
        rows=rows,
    )


def main(page) -> None:
    import flet as ft
    page.title = "ltscheck — проверка HolyWorld (мл. сотрудник)"

    picker = ft.FilePicker()
    page.services.append(picker)

    # --- вкладка "Проверка" ---
    mc_field = ft.TextField(label=".minecraft (папка игры)", expand=True)
    root_field = ft.TextField(label="Дамп для Everything-скана", expand=True)
    check_field = ft.TextField(label="check.txt (Powershell-блок)", expand=True)
    verdict = ft.Container(
        content=ft.Text("Укажите пути и нажмите «Запустить»", size=16),
        padding=12, border_radius=8, bgcolor=ft.Colors.GREY_800,
    )
    progress = ft.ProgressRing(visible=False)
    status = ft.Text("")
    results = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def make_pick(target: ft.TextField):
        async def _do(_):
            path = await picker.get_directory_path()
            if path:
                target.value = path
                page.update()
        return _do

    async def pick_check(_):
        files = await picker.pick_files(allowed_extensions=["txt"])
        if files:
            check_field.value = files[0].path
            page.update()

    async def save_ps1(_):
        from .checktxt_gen import render_ps1
        path = await picker.save_file(file_name="check.ps1")
        if path:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(render_ps1())
            status.value = (f"check.ps1 сохранён: {path}. Запустите его на ПК игрока "
                            "в PowerShell от администратора, заберите check.txt.")
            page.update()

    def set_busy(on: bool, msg: str = ""):
        progress.visible = on
        status.value = msg
        page.update()

    def do_scan():
        rep = Report(target=mc_field.value or root_field.value)
        if mc_field.value:
            rep.extend(audit_mc(mc_field.value))
        if root_field.value:
            rep.extend(audit_fs(root_field.value))
        if check_field.value:
            rep.extend(parse_checktxt(check_field.value))
        c = rep.counts
        verdict.bgcolor = {"BAN": ft.Colors.RED_900, "WARN": ft.Colors.ORANGE_900,
                           "CLEAN": ft.Colors.GREEN_900}[rep.verdict]
        verdict.content = ft.Text(
            f"Вердикт: {rep.verdict}  BAN={c['BAN']} WARN={c['WARN']} INFO={c['INFO']} "
            "(решение о бане — за модератором)", size=16, weight=ft.FontWeight.BOLD)
        results.controls = [
            ft.Text(f"Находок: {len(rep.findings)} (показаны первые 500)"),
            _findings_table(rep.sorted_findings()),
        ]
        page._lts_report = rep
        set_busy(False, "Готово.")

    def on_run(_):
        if not (mc_field.value or root_field.value or check_field.value):
            status.value = "Укажите хотя бы один путь."
            page.update()
            return
        set_busy(True, "Сканирую…")
        page.run_thread(do_scan)

    async def on_save_html(_):
        rep: Report | None = getattr(page, "_lts_report", None)
        if not rep:
            return
        path = await picker.save_file(file_name="report.html")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(rep.to_html())

    async def on_save_json(_):
        rep: Report | None = getattr(page, "_lts_report", None)
        if not rep:
            return
        path = await picker.save_file(file_name="report.json")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(rep.to_json())

    check_tab = ft.Column(controls=[
        ft.Row([mc_field, ft.FilledButton("Папка…", on_click=make_pick(mc_field))]),
        ft.Row([root_field, ft.FilledButton("Папка…", on_click=make_pick(root_field))]),
        ft.Row([check_field, ft.FilledButton("Файл…", on_click=pick_check),
                ft.FilledButton("Создать check.ps1", on_click=save_ps1)]),
        ft.Row([ft.FilledButton("Запустить проверку", on_click=on_run),
                ft.FilledButton("HTML", on_click=on_save_html),
                ft.FilledButton("JSON", on_click=on_save_json), progress, status]),
        verdict,
        results,
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    # --- вкладка "Моды (.jar)" ---
    jar_status = ft.Text("Выберите .jar — статика без запуска (по мануалу запуск у себя запрещён).")
    jar_results = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    async def on_pick_jar(_):
        files = await picker.pick_files(allowed_extensions=["jar"], allow_multiple=True)
        if not files:
            return
        out = []
        for fp in files:
            meta = mod_meta(fp.path)
            out.append(ft.Text(f"{fp.name} — {meta}", weight=ft.FontWeight.BOLD))
            out.append(_findings_table(analyze_jar(fp.path)))
        jar_results.controls = out
        jar_status.value = f"Проверено: {len(files)}"
        page.update()

    jar_tab = ft.Column(controls=[
        ft.Row([ft.FilledButton("Выбрать .jar…", on_click=on_pick_jar)]),
        jar_status, jar_results,
    ], expand=True)

    # --- вкладка "Тулзы" (кнопки «Скачать» + «Скачать все», лог, автозапуск) ---
    from .tools import download_and_launch, download_tools, load_manifest
    dl_manifest = load_manifest()
    dest_field = ft.TextField(label="Папка для тулзов", value="ltscheck", expand=True)
    dl_overall = ft.Text("")
    dl_buttons: dict[str, object] = {}
    dl_states: dict[str, object] = {}
    dl_log_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def dl_say(msg: str):
        dl_log_view.controls.append(ft.Text(msg, size=12))
        if len(dl_log_view.controls) > 200:
            dl_log_view.controls = dl_log_view.controls[-200:]
        page.update()

    def do_download_many(names: list[str], launch: bool = False):
        dest = dest_field.value or "tools"
        if launch:
            assert len(names) == 1
            name = names[0]
            dl_say(f"скачивается: {name}")
            rep = download_and_launch(dest, name)
            st = dl_states.get(name)
            if rep["status"] == "launched":
                dl_say(f"запущено: {rep['exe']}")
                if st is not None:
                    st.value, st.color = f"запущено: {rep['exe']}", ft.Colors.GREEN_400
            else:
                dl_say(f"ошибка {name}: {rep.get('error', '')}")
                if st is not None:
                    st.value, st.color = f"FAIL: {rep.get('error', '')}", ft.Colors.RED_400
        else:
            rep = download_tools(dest, only=names, workers=4)
            by_tool: dict[str, dict] = {}
            for key in ("ok", "failed", "skipped"):
                for r in rep[key]:
                    by_tool[r["tool"]] = r
            for name in names:
                st = dl_states.get(name)
                if st is None:
                    continue
                r = by_tool.get(name)
                if r is None:
                    continue
                if r in rep["ok"]:
                    st.value, st.color = f"OK: {r.get('file', '')}", ft.Colors.GREEN_400
                elif r in rep["failed"]:
                    st.value, st.color = f"FAIL: {r.get('error', '')}", ft.Colors.RED_400
                    dl_say(f"ошибка {r.get('tool')}: {r.get('error', '')}")
                else:
                    st.value, st.color = f"SKIP: {r.get('reason', '')}", ft.Colors.ORANGE_400
            n_ok, n_fail = len(rep["ok"]), len(rep["failed"])
            if len(names) > 1:
                dl_overall.value = (f"Готово: ok={n_ok} failed={n_fail} "
                                    f"skipped={len(rep['skipped'])}")
                dl_say(f"готово: ok={n_ok} failed={n_fail} skipped={len(rep['skipped'])}")
        for b in dl_buttons.values():
            b.disabled = False
        page.update()

    def make_dl(name: str):
        def _do(_):
            btn = dl_buttons.get(name)
            if btn is not None:
                btn.disabled = True
            st = dl_states.get(name)
            if st is not None:
                st.value, st.color = "Качаю…", None
            page.update()
            page.run_thread(do_download_many, [name], True)
        return _do

    def on_download_all(_):
        names = [t["name"] for t in dl_manifest if t.get("urls")]
        if not names:
            return
        for b in dl_buttons.values():
            b.disabled = True
        dl_overall.value = f"Качаю {len(names)}…"
        dl_say(f"скачиваю всё: {len(names)}")
        page.update()
        page.run_thread(do_download_many, names)

    tool_rows = [ft.Row([dest_field,
                         ft.FilledButton("Папка…", on_click=make_pick(dest_field)),
                         ft.FilledButton("Скачать все", on_click=on_download_all),
                         dl_overall])]
    if not dl_manifest:
        tool_rows.append(ft.Text("Нет манифеста тулзов (data/tools_manifest.json не найден в сборке).",
                                 color=ft.Colors.RED_400))
    for t in dl_manifest:
        name = t["name"]
        st = ft.Text("", size=12)
        dl_states[name] = st
        if t.get("urls"):
            btn: object = ft.FilledButton("Скачать", on_click=make_dl(name))
            dl_buttons[name] = btn
            tool_rows.append(ft.Row([ft.Text(f"{name} — {t.get('use', '')}", expand=True), st, btn]))
        else:
            tool_rows.append(ft.Row([
                ft.Text(f"{name} — {t.get('use', '')}", expand=True),
                ft.Text("без URL: " + t.get("note", "качать вручную"), italic=True, size=12)]))
    tools_tab = ft.Column(
        controls=tool_rows + [
            ft.Text("Лог загрузки:", weight=ft.FontWeight.BOLD),
            ft.Container(content=dl_log_view, border=ft.Border.all(1, ft.Colors.GREY_700),
                         border_radius=8, padding=8, height=140),
        ],
        scroll=ft.ScrollMode.AUTO, expand=True)

    page.add(ft.Tabs(length=3, content=ft.Column(expand=True, controls=[
        ft.TabBar(tabs=[ft.Tab(label="Проверка"), ft.Tab(label="Моды (.jar)"), ft.Tab(label="Тулзы")]),
        ft.TabBarView(controls=[check_tab, jar_tab, tools_tab], expand=True),
    ]), expand=True))


def run(view: str = "app") -> None:
    import flet as ft
    if view == "web":
        ft.run(main, view=ft.AppView.WEB_BROWSER)
    else:
        ft.run(main)
