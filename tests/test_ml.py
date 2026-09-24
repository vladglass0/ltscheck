import os

from ltscheck.checktxt import parse_checktxt
from ltscheck.fs_scan import audit_fs
from ltscheck.jar_analyze import analyze_jar
from ltscheck.mc_audit import audit_mc
from tests.conftest import make_checktxt, make_dump, make_jar, make_mc


def test_clean_mc_no_ban(tmp_path):
    mc = make_mc(str(tmp_path / "clean"), dirty=False)
    lv = [f.level for f in audit_mc(mc)]
    assert "BAN" not in lv


def test_dirty_mc_bans(tmp_path):
    mc = make_mc(str(tmp_path / "dirty"), dirty=True)
    got = {(f.rule, f.level) for f in audit_mc(mc)}
    assert ("cheat-folder", "BAN") in got
    assert ("version-jar-cheat", "BAN") in got
    assert ("banned-mod", "BAN") in got
    assert ("via-mod", "BAN") in got
    assert ("config-leftover", "BAN") in got
    assert ("xray-pack", "BAN") in got
    assert ("log-bypass-ip", "BAN") in got


def test_fs_vec_and_storage(tmp_path):
    d = make_dump(str(tmp_path), dirty=True)
    got = {(f.rule, f.level) for f in audit_fs(d)}
    assert ("vec-dll", "BAN") in got
    assert ("dll-weight", "BAN") in got
    assert ("keyword-storage", "BAN") in got


def test_jar_cheat_class(tmp_path):
    p = make_jar(str(tmp_path / "m.jar"), {"com/x/KillAura.class": b"1", "net/java/s.class": b"2"})
    assert any(f.level == "BAN" and f.rule == "jar-cheat-class" for f in analyze_jar(p))


def test_jar_dumik(tmp_path):
    p = make_jar(str(tmp_path / "d.jar"), {"net/java/s.class": b"1", "net/java/f.class": b"2",
                                           "pad.bin": b"\x00" * (100 * 1024)})
    assert any(f.rule == "jar-dumik" for f in analyze_jar(p))


def test_checktxt_vm_and_104(tmp_path):
    p = make_checktxt(str(tmp_path / "check.txt"), vm=True, stopped=True, ev104=True)
    got = {(f.rule, f.level) for f in parse_checktxt(p)}
    assert ("vm-detected", "BAN") in got
    assert ("service-stopped", "WARN") in got
    assert ("event104", "BAN") in got


def test_checktxt_clean(tmp_path):
    p = make_checktxt(str(tmp_path / "check.txt"))
    assert "BAN" not in [f.level for f in parse_checktxt(p)]


def test_gen_ps1_markers(tmp_path):
    from ltscheck.checktxt_gen import render_ps1, write_ps1
    ps1 = render_ps1()
    for marker in ("Модель системы", "Виртуальные устройства", "Последнее включение ПК",
                   "PcaSvc", "DPS", "SysMain", "EventLog", "bam",
                   "EventID=104", "EventID=3079", "СПИСОК ТВИНКОВ",
                   "setting user:", "usercache.json", "usernamecache.json"):
        assert marker in ps1, marker
    p = write_ps1(str(tmp_path / "check.ps1"))
    assert open(p, encoding="utf-8-sig").read() == ps1
