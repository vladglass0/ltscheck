# AGENTS.md — ltscheck (HolyWorld cheat-check automation, мл. сотрудник)

## Environment (Arch Linux, fish shell)

- Python is externally managed — **never use bare `pip`/`python`**. Always `.venv/bin/python`, `.venv/bin/pip`.
- User shell is **fish**: no `^` line continuations, no `source bin/activate`; use `source .venv/bin/activate.fish`.
- No git repo, no CI. Verify with pytest, not linters (none configured).

## Entrypoints

- `main.py` — PyInstaller shim for CLI. **Never pass `ltscheck/cli.py` to pyinstaller directly**: relative imports fail frozen (`ImportError: attempted relative import`).
- `gui_main.py` — GUI-only entry (opens window directly, for windowed builds).
- `python -m ltscheck.cli <scan-mc|scan-fs|analyze-jar|parse-checktxt|full|tools|whitelist-refresh|gui>`; exit codes 0/1/2 = CLEAN/WARN/BAN.
- `ltscheck/gui.py` imports `flet` lazily inside functions — CLI frozen builds work without flet installed.

## Flet 1.0 gotchas (verified against runtime 1.0.1, docs were partly stale)

- `inspect.signature` **hides coroutine-ness**: `FilePicker.pick_files/get_directory_path/save_file` ARE coroutines — check with `inspect.iscoroutinefunction`, handlers must be `async def` + `await`.
- No `ElevatedButton` (use `FilledButton`); button text lives in `.content`, not `.text`; no `page.window`, no `pick_files_async` methods.
- FilePicker goes to `page.services` (not `page.overlay`); tabs are `Tabs(length=N)` + `TabBar`/`TabBarView`; border via `ft.Border.all`, not `ft.border.all`.
- Long scans must go via `page.run_thread` (single-threaded async UI freezes otherwise).
- GUI can't run headless (needs display/`flet-desktop`); regression-test via `tests/test_gui.py` FakePage pattern. `gui --view web` is the fallback without display.

## PyInstaller

- `--add-data` separator is `:` on Linux, `;` on Windows. Seed path resolves via `__file__` (`ltscheck/../data`), so keep the `data` dest dir name.
- CLI build excludes heavy optionals: `--exclude-module=scrapling --exclude-module=flet`. Drop the flet exclusion for GUI builds (use `flet pack gui_main.py` instead).
- **No cross-compilation**: Windows `.exe` for players must be built on Windows.

## Автозагрузчик тулзов (`tools.py`, `data/tools_manifest.json`)

- 31/31 кнопок «Скачать» замаплено кликами в stealth-браузере: 18 прямых URL + stable-зеркала
  вендоров и официальных релизов. Без URL остались только 2 позиции (Ocean без публичной
  ссылки, наборный загрузчик — качать со страницы релизов).
- Кнопки 13 тулзов (WinRar, Recuva, Ocean и др.) требуют входа — клик без
  авторизации не даёт сети; для них в манифесте вендорские URL.
- Подписанные `release-assets.githubusercontent.com` ссылки живут ~1 час — в манифест
  класть только stable `github.com/.../releases/download/...`; `tools --resolve` об этом
  предупреждает.

## Domain rules (from manual.md, do not soften)

- Never execute foreign `.jar/.exe/.dll` — static analysis only (`jar_analyze.py`).
- Downloads/execution on a player's PC only from `mods.holyworld.me`; `whitelist.py` network refresh uses Scrapling `StealthyFetcher(solve_cloudflare=True)` + robots/delays (plain GET returns 403). Offline default is `data/whitelist_seed.json`.
- Verdicts: residues BAN only if <14 days; storage (`.jar/.exe/.zip/.rar/.dll`) always BAN; Labymod/Prosto/BL/Lunar exempt from version-weight checks.
