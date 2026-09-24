"""Загрузчик: локальный HTTP-сервер вместо реальной сети."""
import functools
import http.server
import os
import threading
import zipfile

import pytest

from ltscheck import tools


class Handler(http.server.SimpleHTTPRequestHandler):
    attempts: dict = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/flaky.zip":
            n = Handler.attempts.get(self.path, 0)
            Handler.attempts[self.path] = n + 1
            if n == 0:
                self.send_error(500)
                return
        return super().do_GET()


@pytest.fixture()
def srv(tmp_path):
    root = tmp_path / "srv"
    root.mkdir()
    (root / "tool.zip").write_bytes(b"")  # перезапишем ниже как zip
    with zipfile.ZipFile(root / "tool.zip", "w") as z:
        z.writestr("inner/program.exe", b"MZ fake")
    (root / "flaky.zip").write_bytes((root / "tool.zip").read_bytes())
    (root / "plain.exe").write_bytes(b"MZ fake")
    Handler.attempts = {}
    httpd = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(Handler, directory=str(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def _tool(name, urls, filename=""):
    return {"name": name, "urls": urls, "filename": filename}


def test_download_zip_unpacks(srv, tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "load_manifest",
                        lambda path=tools.MANIFEST_PATH: [_tool("T", [srv + "/tool.zip"], "tool.zip")])
    rep = tools.download_tools(str(tmp_path / "out"), workers=1)
    assert len(rep["ok"]) == 1 and not rep["failed"]
    r = rep["ok"][0]
    assert os.path.isfile(os.path.join(r["unpacked_to"], "inner", "program.exe"))
    assert r["size"] > 0 and len(r["sha256"]) == 16


def test_retry_then_ok(srv, tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "load_manifest",
                        lambda path=tools.MANIFEST_PATH: [_tool("F", [srv + "/flaky.zip"], "flaky.zip")])
    rep = tools.download_tools(str(tmp_path / "out"), workers=1)
    assert len(rep["ok"]) == 1 and not rep["failed"]


def test_failed_and_skipped(srv, tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "load_manifest", lambda path=tools.MANIFEST_PATH: [
        _tool("Missing", [srv + "/nope.zip"], "nope.zip"),
        {"name": "NoUrl", "urls": []},
    ])
    rep = tools.download_tools(str(tmp_path / "out"), workers=2)
    assert [r["tool"] for r in rep["failed"]] == ["Missing"]
    assert [r["tool"] for r in rep["skipped"]] == ["NoUrl"]


def test_skip_if_exists(srv, tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "load_manifest",
                        lambda path=tools.MANIFEST_PATH: [_tool("P", [srv + "/plain.exe"], "plain.exe")])
    d = str(tmp_path / "out")
    assert len(tools.download_tools(d, workers=1)["ok"]) == 1
    rep2 = tools.download_tools(d, workers=1)
    assert rep2["ok"][0].get("note") == "already there" and not rep2["failed"]


def test_manifest_has_urls_for_all_but_two():
    tools_list = tools.load_manifest()
    assert len(tools_list) == 31
    empty = sorted(t["name"] for t in tools_list if not t.get("urls"))
    assert empty == ["HolyCheck", "Ocean"]


def _mk_tool_dir(base, name, files: dict[str, int]):
    d = os.path.join(base, name.replace(" ", "_"))
    for rel, size in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"\x00" * size)
    return d


def test_find_main_exe_exact_name(tmp_path):
    base = str(tmp_path)
    _mk_tool_dir(base, "RegScanner", {"RegScanner/regscanner.exe": 100, "RegScanner/other.exe": 5000})
    tool = {"name": "RegScanner", "urls": ["http://x/y.zip"]}
    assert tools.find_main_exe(tool, base).endswith("regscanner.exe")


def test_find_main_exe_largest(tmp_path):
    base = str(tmp_path)
    _mk_tool_dir(base, "Foo", {"a.exe": 10, "b.exe": 50})
    assert tools.find_main_exe({"name": "Foo", "urls": ["http://x"]}, base).endswith("b.exe")


def test_find_main_exe_missing(tmp_path):
    assert tools.find_main_exe({"name": "Nope", "urls": ["http://x"]}, str(tmp_path)) is None


def test_launch_tool(monkeypatch, tmp_path):
    base = str(tmp_path)
    _mk_tool_dir(base, "Foo", {"Foo.exe": 10})
    monkeypatch.setattr(tools, "load_manifest", lambda path=tools.MANIFEST_PATH: [{"name": "Foo", "urls": ["http://x"]}])
    started = {}

    class P:
        def __init__(self, argv, **kw):
            started["argv"] = argv
            self.pid = 4242

    monkeypatch.setattr("subprocess.Popen", P)
    r = tools.launch_tool(base, "Foo")
    assert r["status"] == "launched" and r["pid"] == 4242
    assert started["argv"][0].endswith("Foo.exe")


def test_download_and_launch_skips_download(monkeypatch, tmp_path):
    base = str(tmp_path)
    _mk_tool_dir(base, "Foo", {"Foo.exe": 10})
    monkeypatch.setattr(tools, "load_manifest", lambda path=tools.MANIFEST_PATH: [{"name": "Foo", "urls": ["http://x"]}])
    monkeypatch.setattr("subprocess.Popen", lambda argv, **kw: type("P", (), {"pid": 7})())
    called = []
    monkeypatch.setattr(tools, "download_tools", lambda *a, **k: called.append(1) or {"ok": [], "failed": [], "skipped": []})
    r = tools.download_and_launch(base, "Foo")
    assert r["status"] == "launched" and not called
