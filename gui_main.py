"""Точка входа для GUI-only сборки: `flet pack gui_main.py`.

В отличие от main.py (CLI-диспетчер), сразу открывает окно проверки.
Для windowed-сборок, где консоль скрыта и аргументы неудобны.
"""
from ltscheck.gui import run

if __name__ == "__main__":
    run()
