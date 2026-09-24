# LTS Checker

[![build](https://github.com/vladglass0/ltscheck/actions/workflows/build.yml/badge.svg)](https://github.com/vladglass0/ltscheck/actions/workflows/build.yml)
## Сборка exe (PyInstaller)

Точка входа — `main.py` (шим: `cli.py` внутри пакета с относительными импортами
нельзя отдавать pyinstaller напрямую):

```bash
# Linux (тестовая сборка):
pyinstaller --onefile --name ltscheck --console \
  --add-data="data/whitelist_seed.json:data" --exclude-module=scrapling main.py
# Windows (релиз для ПК игрока):
pyinstaller --onefile --name ltscheck --console \
  --add-data="data/whitelist_seed.json;data" --exclude-module=scrapling main.py
```

По `manual.md` (Rev by MeYuugao) и сайту
`mods.holyworld.me` (Scrapling `stealthy-fetch --solve-cloudflare --ai-targeted`).

> Помощник модератора, не автобан. Чужие `.jar/.exe/.dll` не запускаем — только статика.
> Качать/выполнять на ПК игрока — только с `mods.holyworld.me`.

## Быстрый старт

```bash
pip install -r requirements.txt
python -m ltscheck.cli full --mc-dir /dump/.minecraft --scan-root /dump --checktxt /dump/check.txt --out report.html --json report.json
echo $?  # 0 CLEAN, 1 WARN, 2 BAN
```

Команды: `scan-mc | scan-fs | analyze-jar | parse-checktxt | gen-ps1 | full | tools | whitelist-refresh | gui`.
`gen-ps1 --out check.ps1` — скрипт для запуска на ПК игрока (собирает check.txt);
в GUI та же кнопка «Создать check.ps1» на вкладке «Проверка».
`tools --list` — manifest 31 тулзы; `tools --only RegScanner --dest tools` — скачать.

## GUI (Flet)

```bash
pip install "flet>=1.0"
python -m ltscheck.cli gui
```

Три вкладки: **Проверка** (пути → вердикт BAN/WARN/CLEAN + таблица находок + HTML/JSON),
**Моды (.jar)** (статика без запуска), **Тулзы** (кнопка «Скачать» у каждой
тулзы качает и сразу запускает + «Скачать все» + лог загрузки внизу;
строки без URL отмечены и качаются вручную).
Сканы идут в фоне через `page.run_thread`, файлы — через FilePicker.
API сверено с доками Flet 1.0 через Context7 (`/flet-dev/flet`).

## Правила вердиктов

Остатки — бан при <14 дней; хранение `.jar/.exe/.zip/.rar/.dll` — всегда бан;
вес версий по таблице 1.16–1.20.2 (+3%, Labymod/Prosto/BL/Lunar exempt);
Via: `viabackwards/viaforge/viaproxy`=бан; DLL-веса 8.95/8.9/1.54/1.43/1.42МБ.
