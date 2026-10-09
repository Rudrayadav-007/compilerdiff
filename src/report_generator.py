"""Feature F: build, save and print reports."""
from __future__ import annotations

import datetime
import json
import os
import platform
import sys
from typing import Optional

from . import comparator
from .compiler_discovery import Compiler


def build_report(compilers: list[Compiler], results: list[dict], timeout: float,
                 opt_levels: tuple[str, ...]) -> dict:
    now = datetime.datetime.now()
    return {
        "run_id": now.strftime("%Y%m%d-%H%M%S"),
        "timestamp": now.isoformat(timespec="seconds"),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "timeout_seconds": timeout,
        "opt_levels": list(opt_levels),
        "compilers": [c.to_dict() for c in compilers],
        "results": results,
        "summary": summarize(results),
        "note": "A potential_discrepancy needs investigation; it is not proof of a compiler bug.",
    }


def summarize(results: list[dict]) -> dict:
    s = {"tests": len(results), "configurations": 0, "pass": 0, "fail_expected": 0,
         "compile_failed": 0, "timeout": 0, "run_error": 0, "no_expectation": 0,
         "potential_discrepancies": 0}
    for r in results:
        for c in r["configs"]:
            s["configurations"] += 1
            s[c["config_status"]] += 1
        if r["comparison"]["outcome"] == comparator.MISMATCH:
            s["potential_discrepancies"] += 1
    return s


def write_json(report: dict, reports_dir: str, path: Optional[str] = None) -> str:
    """Write report as UTF-8 JSON (ensure_ascii escapes odd characters). Returns the path."""
    if path is None:
        os.makedirs(reports_dir, exist_ok=True)
        path = os.path.join(reports_dir, f"report_{report['run_id']}.json")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)
    return path


def format_compilers(compilers: list[Compiler]) -> str:
    lines = []
    for c in compilers:
        lines.append(f"  [OK]      {c.name}: {c.version}  ({c.path})" if c.available
                     else f"  [MISSING] {c.name}: {c.error}")
    return "\n".join(lines)


def _safe(text: str) -> str:
    """Make text printable on consoles with limited encodings (e.g. cp1252)."""
    enc = sys.stdout.encoding or "utf-8"
    return text.encode(enc, errors="backslashreplace").decode(enc)


def format_summary(report: dict) -> str:
    out = [f"CompilerDiff run {report['run_id']}  ({report['os']}, Python {report['python']})",
           "Compilers:", format_compilers([Compiler(**c) for c in report["compilers"]]), ""]
    for r in report["results"]:
        out.append(f"{r['test']}: {r['comparison']['outcome']}")
        for c in r["configs"]:
            line = f"  {c['config']:<12} {c['config_status']}"
            ex = c["execution"]
            if c["compile"]["status"] != "ok":
                line += f"  (compile {c['compile']['status']})"
            elif ex and ex["status"] == "timeout":
                line += f"  ({ex['error']})"
            elif ex:
                line += f"  (rc={ex['returncode']})"
            out.append(line)
        for d in r["comparison"]["differences"]:
            out.append(f"    differs: {', '.join(d['configs'])} -> rc={d['returncode']} "
                       f"stdout={d['stdout']!r}")
        if r["comparison"]["not_compared"]:
            out.append(f"    not compared: {', '.join(r['comparison']['not_compared'])}")
    s = report["summary"]
    out += ["", "Summary: " + ", ".join(f"{k}={v}" for k, v in s.items()), report["note"]]
    return _safe("\n".join(out))
