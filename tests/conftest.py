"""Фикстуры мл. сотрудника: чистая и грязная копии .minecraft + check.txt + jar."""
from __future__ import annotations

import gzip
import os
import zipfile

import pytest


def _write(path: str, size: int, head: bytes = b"") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(head)
        rest = size - len(head)
        if rest > 0:
            f.write(b"\x00" * rest)


def make_mc(root: str, dirty: bool) -> str:
    mc = os.path.join(root, ".minecraft")
    os.makedirs(os.path.join(mc, "versions", "1.16.5"), exist_ok=True)
    os.makedirs(os.path.join(mc, "mods"), exist_ok=True)
    os.makedirs(os.path.join(mc, "config"), exist_ok=True)
    os.makedirs(os.path.join(mc, "libraries", "net"), exist_ok=True)
    os.makedirs(os.path.join(mc, "resourcepacks"), exist_ok=True)
    os.makedirs(os.path.join(mc, "logs"), exist_ok=True)
    # версия: чистый вес 17136КБ
    _write(os.path.join(mc, "versions", "1.16.5", "1.16.5.jar"), 17136 * 1024)
    import zipfile as _zf
    for _name in ("sodium.jar",):
        with _zf.ZipFile(os.path.join(mc, "mods", _name), "w") as _z:
            _z.writestr("fabric.mod.json", '{"id":"sodium","version":"1.0"}')
    with open(os.path.join(mc, "logs", "latest.log"), "w", encoding="utf-8") as f:
        f.write("[Client] setting user: Steve\n")
    if dirty:
        os.makedirs(os.path.join(mc, "Impact"), exist_ok=True)
        _write(os.path.join(mc, "versions", "1.16.5", "Impact_4.9.1.jar"), 100 * 1024)
        with _zf.ZipFile(os.path.join(mc, "mods", "freecam-forge.jar"), "w") as _z:
            _z.writestr("com/freecam/FreeCam.class", b"0")
        with _zf.ZipFile(os.path.join(mc, "mods", "ViaForge.jar"), "w") as _z:
            _z.writestr("com/viaforge/ViaForge.class", b"0")
        _write(os.path.join(mc, "config", "baritone.json"), 100)
        _write(os.path.join(mc, "resourcepacks", "Xray_Ultimate.zip"), 100)
        with open(os.path.join(mc, "logs", "2025-04-18-1.log"), "w", encoding="utf-8") as f:
            f.write("[Chat] Nursultan enabled\nconnecting to 192.168.1.71 then HolyWorld\n")
            f.write("[Client] setting user: Cheater123\n")
    return mc


def make_dump(root: str, dirty: bool) -> str:
    dump = os.path.join(root, "dump")
    os.makedirs(dump, exist_ok=True)
    if dirty:
        # vec.dll 30kb + маркер
        _write(os.path.join(dump, "vec.dll"), 30 * 1024, b"net/minecraft/util/math/axisalignedbb")
        _write(os.path.join(dump, "Nursultan.rar"), 50 * 1024)
        _write(os.path.join(dump, "dauntiblyat.dll"), int(1.43 * 1024 * 1024))
    else:
        _write(os.path.join(dump, "notes.txt"), 100, b"hello")
    return dump


def make_jar(path: str, entries: dict[str, bytes]) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return path


def make_checktxt(path: str, vm: bool = False, stopped: bool = False, ev104: bool = False) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "1. Модель системы: MS-7D25",
        "2. Серийный BIOS: Default string",
        "4. Модель диска: Samsung SSD 970",
        "5. Видеоадаптеры: NVIDIA GeForce RTX 3070 - NVIDIA",
        "6. Виртуальные устройства: Virtual Mic for AudioRelay" if not vm else
        "6. Виртуальные устройства: VMware SVGA 3D, VMware VMCI Bus Device",
        "Последнее включение ПК: 2025-05-26 10:38:09",
        "PcaSvc Running Авто 2025-05-26 10:39:00" if not stopped else "PcaSvc Stopped Отключена Не запущена",
    ]
    if ev104:
        lines.append("ID 104 | 2025-05-26 11:00:00 | журнал Application очищен")
    lines += ["СПИСОК ТВИНКОВ ИГРОКА", "Steve Cheater123"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
