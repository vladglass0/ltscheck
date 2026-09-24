"""Разбор check.txt из Powershell-блока: VM, службы, ID 104/3079, твинки."""
from __future__ import annotations

import re
from datetime import datetime

from . import rules
from .report import Finding

MOD = "checktxt"

DT = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def _parse_dt(s: str):
    m = DT.search(s)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def parse_checktxt(path: str) -> list[Finding]:
    out: list[Finding] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError as e:
        return [Finding("WARN", MOD, "no-checktxt", path, str(e))]
    low = text.lower()

    # --- VM ---
    vm_hits = sorted({m for m in rules.VM_MARKERS if m in low})
    # отфильтровываем ложные: audioRelay virtual mic/speakers сами по себе не виртуалка,
    # но VMware/VBox/Hyper-V/QEMU диски и видео — да
    strong = [m for m in vm_hits if m in ("vmware", "vbox", "virtualbox", "qemu", "xen", "kvm", "svga")]
    model = re.search(r"модель системы:\s*(.+)", low)
    disk = re.search(r"модел[ьи] диска:\s*(.+)", low)
    video = re.search(r"видеоадаптеры:\s*(.+)", low)
    if strong or (model and any(m in model.group(1) for m in ("vmware", "virtual", "vbox", "qemu", "kvm"))) \
            or (disk and any(m in disk.group(1) for m in ("vmware", "virtual", "vbox", "qemu"))) \
            or (video and any(m in video.group(1) for m in ("vmware", "svga", "virtualbox", "vmbus"))):
        out.append(Finding("BAN", MOD, "vm-detected", path,
                           "виртуальная машина: " + ", ".join(vm_hits)))
    elif vm_hits:
        out.append(Finding("INFO", MOD, "vm-weak", path,
                           "слабые VM-маркеры (часто аудиодрайверы): " + ", ".join(vm_hits)))

    # --- boot time ---
    boot = None
    m = re.search(r"последнее включение пк:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", low)
    if m:
        try:
            boot = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            boot = None

    # --- службы ---
    stopped = []
    for svc in rules.MONITORED_SERVICES:
        # ищем строки вида "PcaSvc ... Stopped" / "Не запущена" / "Отключена"
        for line in text.splitlines():
            if svc.lower() in line.lower() and any(
                    w in line for w in ("Stopped", "Не запущена", "Остановлена", "Отключена")):
                stopped.append(svc)
                break
    for svc in sorted(set(stopped)):
        out.append(Finding("WARN", MOD, "service-stopped", path,
                           f"служба {svc} остановлена/отключена — проверить /history, иначе warn игроку"))

    # --- ID 104 (очистка журналов) после включения ---
    for line in text.splitlines():
        if re.search(r"\bID\s*104\b", line):
            dt = _parse_dt(line)
            if boot and dt and dt > boot:
                out.append(Finding("BAN", MOD, "event104", path,
                                   f"очистка журнала после включения ПК: {line.strip()[:160]}"))
                break
    # --- ID 3079 (журнал тома удалён / чистка jt) ---
    for line in text.splitlines():
        if re.search(r"\bID\s*3079\b", line) and ("том" in line.lower() or "journal" in line.lower() or "удалён" in line.lower()):
            dt = _parse_dt(line)
            if boot is None or (dt and dt > boot):
                out.append(Finding("BAN", MOD, "event3079", path,
                                   f"чистка jt после включения: {line.strip()[:160]}"))
                break
    # --- твинки ---
    tw = re.search(r"твинк[иов]*.{0,80}\n=+\n(.+)", text, re.S | re.I)
    if tw:
        names = [x.strip() for x in re.split(r"[\s,;]+", tw.group(1).strip()) if x.strip()]
        names = [n for n in names if n.lower() not in ("нет", "данных", "о", "твинках", "ошибки:")]
        if names:
            out.append(Finding("INFO", MOD, "twinks", path,
                               "твинки для /checkban: " + ", ".join(names[:60])))
    if not out:
        out.append(Finding("INFO", MOD, "checktxt-clean", path, "VM/службы/104/3079 чистые"))
    return out
