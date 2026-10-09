"""Feature A: find which C compilers are installed and record their versions."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional

SUPPORTED_COMPILERS = ("gcc", "clang")

INSTALL_HINTS = {
    "gcc": "Install MinGW-w64/MSYS2 (e.g. `winget install MSYS2.MSYS2`, then "
           "`pacman -S mingw-w64-ucrt-x86_64-gcc`) and add its bin folder to PATH.",
    "clang": "Install LLVM (`winget install LLVM.LLVM`) and add its bin folder to PATH.",
}


@dataclass
class Compiler:
    """One compiler we looked for. `available` is False when not found."""
    name: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _get_version(path: str) -> tuple[Optional[str], Optional[str]]:
    """Run `<compiler> --version`; return (first_line, error)."""
    try:
        proc = subprocess.run([path, "--version"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"could not run --version: {exc}"
    if proc.returncode != 0:
        return None, f"--version exited with code {proc.returncode}"
    lines = proc.stdout.strip().splitlines()
    return (lines[0] if lines else "unknown"), None


def discover_compilers(names: tuple[str, ...] = SUPPORTED_COMPILERS) -> list[Compiler]:
    """Look up each compiler on PATH. Never raises for a missing compiler."""
    found = []
    for name in names:
        path = shutil.which(name)
        if path is None:
            found.append(Compiler(name, False, error=f"'{name}' not found on PATH"))
            continue
        version, err = _get_version(path)
        # A compiler whose --version fails is treated as unusable.
        found.append(Compiler(name, err is None, path, version, err))
    return found


def available_only(compilers: list[Compiler]) -> list[Compiler]:
    return [c for c in compilers if c.available]
