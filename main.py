"""Точка входа для PyInstaller: `pyinstaller ... main.py`.

cli.py внутри пакета использует относительные импорты, поэтому его нельзя
передавать pyinstaller напрямую (там __package__ пуст). Этот шим импортирует
пакет абсолютно — работает и как скрипт, и во frozen-сборке.
"""
from ltscheck.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
