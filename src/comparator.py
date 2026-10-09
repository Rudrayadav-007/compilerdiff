"""Feature E: compare observable behavior of the same test across configurations.

Only observable behavior (stdout, stderr, exit code) is compared -- never assembly.
A mismatch means "needs investigation", NOT "compiler bug": causes include
unspecified behavior in the test, library differences, or a real defect.
"""
from __future__ import annotations

from typing import Optional

# Per-configuration statuses
PASS = "pass"                      # matches expected output and return code
FAIL_EXPECTED = "fail_expected"    # ran, but differs from the manifest expectation
NO_EXPECTATION = "no_expectation"  # ran; manifest defines no expected output
COMPILE_FAILED = "compile_failed"
TIMEOUT = "timeout"
RUN_ERROR = "run_error"

# Per-test outcomes
MATCH = "match"
MISMATCH = "potential_discrepancy"
ALL_FAILED = "no_comparable_results"
SINGLE = "single_configuration"


def normalize_output(text: str) -> str:
    """Conservative normalization: unify line endings, strip trailing whitespace per line
    and trailing blank lines. Leading/inner whitespace and case are preserved."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(l.rstrip() for l in lines).rstrip("\n")


def classify_config(compile_status: str, exec_result: Optional[dict],
                    expected_stdout: Optional[str], expected_rc: int) -> str:
    """Status of ONE configuration. `exec_result` is ExecResult.to_dict() or None."""
    if compile_status != "ok":
        return COMPILE_FAILED
    if exec_result is None or exec_result["status"] == "launch_error":
        return RUN_ERROR
    if exec_result["status"] == "timeout":
        return TIMEOUT
    if expected_stdout is None:
        return NO_EXPECTATION
    same_out = normalize_output(exec_result["stdout"]) == normalize_output(expected_stdout)
    return PASS if same_out and exec_result["returncode"] == expected_rc else FAIL_EXPECTED


def _signature(exec_result: dict) -> tuple:
    return (exec_result["returncode"], normalize_output(exec_result["stdout"]),
            normalize_output(exec_result["stderr"]))


def compare_configs(configs: list[dict]) -> dict:
    """Compare configs of ONE test. Each dict needs 'config' (label), 'config_status', 'execution'.

    Only configs that compiled and exited normally are compared with each other;
    compile failures and timeouts are listed separately, never silently dropped.
    """
    comparable = [c for c in configs if c["execution"] and c["execution"]["status"] == "ok"]
    problems = [c["config"] for c in configs if c not in comparable]
    outcome, differences = ALL_FAILED, []
    if len(comparable) == 1:
        outcome = SINGLE
    elif len(comparable) > 1:
        groups: dict[tuple, list[str]] = {}
        for c in comparable:
            groups.setdefault(_signature(c["execution"]), []).append(c["config"])
        if len(groups) == 1:
            outcome = MATCH
        else:
            outcome = MISMATCH
            for sig, labels in groups.items():
                differences.append({"configs": labels, "returncode": sig[0],
                                    "stdout": sig[1], "stderr": sig[2]})
    # Failures (compile/timeout/run) are surfaced even if the rest agree.
    return {"outcome": outcome, "differences": differences, "not_compared": problems}
