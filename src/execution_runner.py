"""Feature D: run a compiled binary with a timeout.

WARNING: a timeout only stops runaway programs. It is NOT a security sandbox.
Only run the project's own trusted corpus with this module.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, asdict
from typing import Optional

DEFAULT_TIMEOUT_S = 10.0


@dataclass
class ExecResult:
    """status: ok (exited, any code) | timeout | launch_error."""
    status: str
    returncode: Optional[int]
    stdout: str
    stderr: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _text(data) -> str:
    """Decode bytes (or None) to str; invalid bytes become U+FFFD instead of crashing."""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data


def run_binary(binary: str, timeout: float = DEFAULT_TIMEOUT_S) -> ExecResult:
    """Run `binary` (argument list, no shell). Never raises; failures are returned as data."""
    try:
        proc = subprocess.run([binary], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return ExecResult("timeout", None, _text(exc.stdout), _text(exc.stderr),
                          f"timed out after {timeout}s")
    except OSError as exc:
        return ExecResult("launch_error", None, "", "", f"could not run binary: {exc}")
    return ExecResult("ok", proc.returncode, _text(proc.stdout), _text(proc.stderr))
