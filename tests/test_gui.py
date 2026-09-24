"""Сборка GUI на фейковой странице: ловит опечатки в ft-API без дисплея."""
import inspect
from types import SimpleNamespace

import flet as ft

from ltscheck import gui
from ltscheck.report import Finding


class FakePage(SimpleNamespace):
    def __init__(self):
        super().__init__(title="", window=SimpleNamespace(width=0, height=0),
                         services=[], added=[])
    def add(self, *controls):
        self.added.extend(controls)
    def update(self):
        pass
    def run_thread(self, fn, *args):
        pass


def test_findings_table_builds():
    t = gui._findings_table([
        Finding("BAN", "mc", "banned-mod", "mods/freecam.jar", "чит"),
        Finding("INFO", "mc", "mods-clean", "mods", "ок"),
    ])
    assert len(t.rows) == 2
    assert len(t.columns) == 5


def test_main_builds_tabs():
    page = FakePage()
    gui.main(page)
    assert page.title.startswith("ltscheck")
    assert len(page.added) == 1
    assert len(page.services) == 1


def test_tools_tab_buttons():
    import flet as ft2
    from ltscheck.tools import load_manifest
    page = FakePage()
    gui.main(page)
    texts = []

    def walk(c):
        if isinstance(c, ft2.FilledButton) and isinstance(getattr(c, "content", None), str):
            texts.append(c.content)
        for child in getattr(c, "controls", []) or []:
            walk(child)
        content = getattr(c, "content", None)
        if isinstance(content, list):
            for child in content:
                walk(child)
        elif content is not None and not isinstance(content, str):
            walk(content)

    for top in page.added:
        walk(top)
    manifest = load_manifest()
    with_url = sum(1 for t in manifest if t.get("urls"))
    assert texts.count("Скачать") == with_url == 29
    assert texts.count("Скачать все") == 1
    # Ocean/HolyCheck — без кнопок, с пометкой
    notes = []

    def walk_text(c):
        if isinstance(c, ft2.Text) and "без URL" in (c.value or ""):
            notes.append(c.value)
        for child in getattr(c, "controls", []) or []:
            walk_text(child)
        content = getattr(c, "content", None)
        if isinstance(content, list):
            for child in content:
                walk_text(child)
        elif content is not None and not isinstance(content, str):
            walk_text(content)

    for top in page.added:
        walk_text(top)
    assert len(notes) == 2


def test_picker_methods_are_coroutines():
    # рантайм 1.0.1: методы FilePicker надо await'ить, хендлеры — async
    for m in ("pick_files", "get_directory_path", "save_file"):
        assert inspect.iscoroutinefunction(getattr(ft.FilePicker, m)), m
