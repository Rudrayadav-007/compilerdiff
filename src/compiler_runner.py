"""Feature C: compile one C file with one compiler + optimization level."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional

from .compiler_discovery import Compiler

COMPILE_TIMEOUT_S = 60


@dataclass
class CompileResult:
    """Outcome of one compilation. status: ok | error | timeout | tool_error."""
    status: str
    command: list[str]
    returncode: Optional[int]
    diagnostics: str            # compiler stdout+stderr (kept separate from program output)
    binary: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def build_command(compiler: Compiler, source: str, output: str, opt: str) -> list[str]:
    """Return the argv list (no shell). -Wall -Wextra surfaces warnings; -std=c11 pins the language."""
    return [compiler.path or compiler.name, opt, "-std=c11", "-Wall", "-Wextra",
            source, "-o", output]


def binary_name(test: str, compiler: str, opt: str) -> str:
    suffix = ".exe" if os.name == "nt" else ""
    return f"{test}_{compiler}_{opt.lstrip('-')}{suffix}"


def compile_source(compiler: Compiler, source: str, workdir: str, test: str,
                   opt: str, timeout: float = COMPILE_TIMEOUT_S) -> CompileResult:
    """Compile `source` into `workdir`. Never raises; failures are returned as data."""
    output = os.path.join(workdir, binary_name(test, compiler.name, opt))
    cmd = build_command(compiler, source, output, opt)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return CompileResult("timeout", cmd, None, f"compilation exceeded {timeout}s")
    except OSError as exc:  # compiler vanished / not executable
        return CompileResult("tool_error", cmd, None, f"could not launch compiler: {exc}")
    diagnostics = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return CompileResult("error", cmd, proc.returncode, diagnostics)
    return CompileResult("ok", cmd, 0, diagnostics, binary=output)
