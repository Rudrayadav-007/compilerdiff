"""Feature A: find which C compilers are installed and record their versions."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional

SUPPORTED_COMPILERS = ("gcc", "clang", "cl")

INSTALL_HINTS = {
    "gcc": "Install MinGW-w64/MSYS2 (e.g. `winget install MSYS2.MSYS2`, then "
           "`pacman -S mingw-w64-ucrt-x86_64-gcc`) and add its bin folder to PATH.",
    "clang": "Install LLVM (`winget install LLVM.LLVM`), add its bin folder to PATH, and "
             "install Visual Studio C++ Build Tools (provides the C headers/libraries).",
    "cl": "Install Visual Studio Build Tools with the 'Desktop development with C++' workload; "
          "CompilerDiff loads its environment automatically via vswhere/vcvars64.bat.",
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


def _get_version(path: str, name: str = "") -> tuple[Optional[str], Optional[str]]:
    """Return (first_line, error). gcc/clang use `--version`; MSVC `cl` prints a banner to stderr."""
    cmd = [path] if name == "cl" else [path, "--version"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"could not run {' '.join(cmd[1:]) or 'compiler'}: {exc}"
    if name != "cl" and proc.returncode != 0:
        return None, f"--version exited with code {proc.returncode}"
    # cl writes its banner to stderr and usage text to stdout, so look at stderr first.
    lines = (proc.stderr + proc.stdout).strip().splitlines()
    if not lines:
        return None, "no version output"
    return lines[0].strip(), None


def find_vcvars() -> Optional[str]:
    """Locate Visual Studio's vcvars64.bat via the official `vswhere` tool (Windows only)."""
    if os.name != "nt":
        return None
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = os.path.join(pf86, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not os.path.isfile(vswhere):
        return None
    try:
        proc = subprocess.run([vswhere, "-latest", "-products", "*", "-requires",
                               "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                               "-property", "installationPath"],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    root = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
    bat = os.path.join(root, "VC", "Auxiliary", "Build", "vcvars64.bat") if root else ""
    return bat if bat and os.path.isfile(bat) else None


def load_vs_environment() -> Optional[str]:
    """Import the Visual Studio developer environment (what the Developer Command Prompt
    does) into THIS process only, so cl and clang can find the Windows SDK/CRT headers.
    Returns None on success/no-op, or a message describing why it was skipped."""
    if os.name != "nt" or os.environ.get("VSCMD_VER"):
        return None
    bat = find_vcvars()
    if bat is None:
        return "Visual Studio C++ Build Tools not found (vswhere/vcvars64.bat missing)"
    try:
        proc = subprocess.run(["cmd", "/c", "call", bat, ">nul", "&&", "set"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"could not run vcvars64.bat: {exc}"
    if proc.returncode != 0:
        return f"vcvars64.bat exited with code {proc.returncode}"
    for line in proc.stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep and key:
            os.environ[key] = value
    return None


def discover_compilers(names: tuple[str, ...] = SUPPORTED_COMPILERS,
                       use_vs_env: bool = True) -> list[Compiler]:
    """Look up each compiler on PATH. Never raises for a missing compiler.
    On Windows the Visual Studio environment is loaded first (see load_vs_environment)."""
    if use_vs_env:
        load_vs_environment()
    found = []
    for name in names:
        path = shutil.which(name)
        if path is None:
            found.append(Compiler(name, False, error=f"'{name}' not found on PATH"))
            continue
        version, err = _get_version(path, name)
        # A compiler whose version query fails is treated as unusable.
        found.append(Compiler(name, err is None, path, version, err))
    return found



def available_only(compilers: list[Compiler]) -> list[Compiler]:
    return [c for c in compilers if c.available]
