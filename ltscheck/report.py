"""Модель находок и отчётов."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import html
import json

LEVEL_ORDER = {"INFO": 0, "WARN": 1, "BAN": 2}


@dataclass
class Finding:
    level: str
    module: str
    rule: str
    path: str
    detail: str = ""
    mtime: str = ""

    def as_dict(self) -> dict:
        return {"level": self.level, "module": self.module, "rule": self.rule,
                "path": self.path, "detail": self.detail, "mtime": self.mtime}


@dataclass
class Report:
    target: str = ""
    started: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, module: str, rule: str, path: str, detail: str = "", mtime: str = "") -> None:
        self.findings.append(Finding(level, module, rule, path, detail, mtime))

    def extend(self, findings: list[Finding]) -> None:
        self.findings.extend(findings)

    @property
    def counts(self) -> dict[str, int]:
        c = {"BAN": 0, "WARN": 0, "INFO": 0}
        for f in self.findings:
            if f.level in c:
                c[f.level] += 1
        return c

    @property
    def verdict(self) -> str:
        c = self.counts
        if c["BAN"]:
            return "BAN"
        if c["WARN"]:
            return "WARN"
        return "CLEAN"

    def sorted_findings(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: (-LEVEL_ORDER.get(f.level, 0), f.module, f.path))

    def to_dict(self) -> dict:
        return {"target": self.target, "started": self.started, "verdict": self.verdict,
                "counts": self.counts, "findings": [f.as_dict() for f in self.sorted_findings()]}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_text(self) -> str:
        lines = [f"ltscheck verdict={self.verdict} counts={self.counts} target={self.target}"]
        for f in self.sorted_findings():
            lines.append(f"[{f.level}] {f.module}:{f.rule} :: {f.path} {f.detail} {f.mtime}".rstrip())
        return "\n".join(lines)

    def to_html(self) -> str:
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(f.level), html.escape(f.module), html.escape(f.rule),
                html.escape(f.path), html.escape(f"{f.detail} {f.mtime}".strip()))
            for f in self.sorted_findings())
        return ("<!doctype html><html lang=ru><head><meta charset=utf-8><title>ltscheck</title></head><body>"
                f"<h1>Вердикт: {html.escape(self.verdict)}</h1>"
                f"<p>target={html.escape(self.target)} started={html.escape(self.started)} "
                f"counts={html.escape(str(self.counts))}</p>"
                "<table border=1><tr><th>level</th><th>module</th><th>rule</th><th>path</th><th>detail</th></tr>"
                + rows + "</table></body></html>")
