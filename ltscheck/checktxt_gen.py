"""Генератор check.ps1 — скрипт создаёт check.txt на ПК игрока.

Формат выхлопа повторяет Powershell-блок manual.md и то, что умеет
разбирать checktxt.parse_checktxt: железо/VM-маркеры, boot time, службы
PcaSvc/DPS/SysMain/EventLog/bam, события ID 104/3079, список твинков.
Запуск — на ПК игрока в PowerShell от администратора, check.txt потом
разбирается командой parse-checktxt / вкладкой «Проверка».
"""
from __future__ import annotations

PS1 = r'''# ltscheck check.ps1 — собрать check.txt на ПК игрока (запуск от администратора)
$ErrorActionPreference = "SilentlyContinue"
$out = "$PWD\check.txt"
"1. Модель системы: $((Get-WmiObject Win32_ComputerSystem).Model)`n2. Серийный BIOS: $((Get-WmiObject Win32_BIOS).SerialNumber)`n3. Реестр: $((Get-ItemProperty 'HKLM:\HARDWARE\DESCRIPTION\System\BIOS').SystemProductName)`n4. Модель диска: $((Get-WmiObject Win32_DiskDrive).Model -join ', ')`n5. Видеоадаптеры: $(($(Get-WmiObject Win32_VideoController | ForEach-Object { "$($_.Name) - $($_.AdapterCompatibility)" }) -join ', '))`n6. Виртуальные устройства: $((Get-WmiObject Win32_PnPEntity | Where-Object {$_.Name -match 'VMware|Virtual|VBox|Hyper-V|QEMU|Xen|KVM|VirtIO|VirtualBox|VMCI|SVGA|VMBus'}).Name -join ', ')" > $out
$bootTime = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
"`nПоследнее включение ПК: $($bootTime.ToString('yyyy-MM-dd HH:mm:ss'))" >> $out
"`nСОСТОЯНИЕ СЛУЖБ" >> $out
@("PcaSvc","DPS","SysMain","EventLog","bam") | ForEach-Object {
  $s = Get-Service $_ -ea 0
  if ($s) { "$_ $($s.Status)" >> $out } else { "$_ Не запущена" >> $out }
}
"`nСОБЫТИЯ ОЧИСТКИ ЖУРНАЛОВ (ID 104)" >> $out
Get-WinEvent -LogName System -FilterXPath "*[System[(EventID=104)]]" -ea 0 | ForEach-Object {
  "ID $($_.Id) | $($_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')) | $($_.Message -split \"`n\" | Select-Object -First 1)" >> $out
}
"`nСОБЫТИЯ ПРИЛОЖЕНИЯ (ID 3079)" >> $out
Get-WinEvent -LogName Application -FilterXPath "*[System[(EventID=3079)]]" -MaxEvents 5 -ea 0 | ForEach-Object {
  "ID $($_.Id) | $($_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')) | $($_.Message -split \"`n\" | Select-Object -First 1)" >> $out
}
"`nСПИСОК ТВИНКОВ ИГРОКА`n=============================================" >> $out
$r = @{}
Get-ChildItem -Path . -Recurse -Include *.log,*.log.gz -ea 0 | ForEach-Object {
  try {
    if ($_.Extension -eq '.gz') {
      $c = [System.IO.Compression.GzipStream]::new([System.IO.File]::OpenRead($_.FullName), [System.IO.Compression.CompressionMode]::Decompress)
      $s = [System.IO.StreamReader]::new($c)
      while (-not $s.EndOfStream) { $l = $s.ReadLine(); if ($l -match 'setting user:\s*(.+)$') { $r[$matches[1].Trim()] = 1 } }
      $s.Close()
    } else {
      Get-Content $_.FullName | Where-Object { $_ -match 'setting user:\s*(.+)$' } | ForEach-Object { $r[$matches[1].Trim()] = 1 }
    }
  } catch {}
}
if (Test-Path "$PWD\usercache.json") {
  try { Get-Content "$PWD\usercache.json" -Raw | ConvertFrom-Json | Select-Object -ExpandProperty name | ForEach-Object { $r[$_] = 1 } } catch {}
}
if (Test-Path "$PWD\usernamecache.json") {
  try { Get-Content "$PWD\usernamecache.json" -Raw | ConvertFrom-Json | ForEach-Object { $_.PSObject.Properties.Value } | ForEach-Object { $r[$_] = 1 } } catch {}
}
if ($r.Count -gt 0) { $r.Keys >> $out } else { "Нет данных о твинках" >> $out }
"Готово: $out"
'''


def render_ps1() -> str:
    return PS1


def write_ps1(path: str) -> str:
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(PS1)
    return path
