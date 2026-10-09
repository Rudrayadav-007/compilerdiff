"""Unit tests (mocked subprocess; no compiler needed) plus end-to-end tests (skipped if none)."""
import json
import os
import subprocess

import pytest

import main as cli
from src import comparator, compiler_discovery, compiler_runner, execution_runner, pipeline
from src import report_generator as rg
from src.compiler_discovery import Compiler, available_only, discover_compilers
from src.test_corpus import TestCase, load_corpus, select_tests

GCC = Compiler("gcc", True, "/fake/gcc", "gcc 13")
CLANG = Compiler("clang", True, "/fake/clang", "clang 17")


def ex(stdout="", rc=0, stderr="", status="ok"):
    return {"status": status, "returncode": rc, "stdout": stdout, "stderr": stderr, "error": None}


def cfg(label, execution, status="pass"):
    return {"config": label, "config_status": status, "execution": execution}


# ---- output / return-code comparison ----
def test_normalize_trailing_whitespace_only():
    assert comparator.normalize_output("a  \r\nb\t\n\n") == "a\nb"
    assert comparator.normalize_output(" a") != comparator.normalize_output("a")  # leading kept


def test_match_ignores_trailing_whitespace():
    r = comparator.compare_configs([cfg("a", ex("hi\n")), cfg("b", ex("hi  \r\n"))])
    assert r["outcome"] == comparator.MATCH


def test_stdout_difference_is_flagged():
    r = comparator.compare_configs([cfg("a", ex("1\n")), cfg("b", ex("2\n"))])
    assert r["outcome"] == comparator.MISMATCH and len(r["differences"]) == 2


def test_return_code_difference_is_flagged():
    r = comparator.compare_configs([cfg("a", ex("x", rc=0)), cfg("b", ex("x", rc=1))])
    assert r["outcome"] == comparator.MISMATCH


def test_classify_against_expected():
    assert comparator.classify_config("ok", ex("5\n"), "5\n", 0) == comparator.PASS
    assert comparator.classify_config("ok", ex("6\n"), "5\n", 0) == comparator.FAIL_EXPECTED
    assert comparator.classify_config("ok", ex("5\n", rc=2), "5\n", 0) == comparator.FAIL_EXPECTED
    assert comparator.classify_config("ok", ex("5\n"), None, 0) == comparator.NO_EXPECTATION


def test_failures_are_not_silently_dropped():
    r = comparator.compare_configs([cfg("a", ex("1")), cfg("b", ex("1")),
                                    cfg("c", None, "compile_failed"),
                                    cfg("d", ex(status="timeout", rc=None), "timeout")])
    assert r["outcome"] == comparator.MATCH and r["not_compared"] == ["c", "d"]


def test_all_failed():
    r = comparator.compare_configs([cfg("a", None, "compile_failed")])
    assert r["outcome"] == comparator.ALL_FAILED


# ---- missing compiler handling ----
def test_missing_compilers(monkeypatch):
    monkeypatch.setattr(compiler_discovery.shutil, "which", lambda n: None)
    found = discover_compilers()
    assert [c.available for c in found] == [False, False]
    assert "not found" in found[0].error


def test_run_suite_skips_unavailable():
    missing = Compiler("clang", False, error="not found")
    assert available_only([missing]) == []
    assert pipeline.run_suite([missing], [TestCase("t", "t.c", "", None)])[0]["configs"] == []


def test_cli_run_without_compilers(monkeypatch, capsys):
    monkeypatch.setattr(cli, "discover_compilers",
                        lambda: [Compiler("gcc", False, error="x"), Compiler("clang", False, error="y")])
    assert cli.main(["run"]) == 2
    assert "nothing was tested" in capsys.readouterr().err


def test_version_failure_marks_unavailable(monkeypatch):
    monkeypatch.setattr(compiler_discovery.shutil, "which", lambda n: "/x/" + n)

    def boom(*a, **k):
        raise OSError("bad")
    monkeypatch.setattr(compiler_discovery.subprocess, "run", boom)
    assert not any(c.available for c in discover_compilers())


# ---- compile failure / timeout (mocked) ----
def _fake_run(returncode=0, stdout="", stderr=""):
    return lambda *a, **k: subprocess.CompletedProcess(a[0], returncode, stdout, stderr)


def test_compilation_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(compiler_runner.subprocess, "run", _fake_run(1, "", "error: boom"))
    res = compiler_runner.compile_source(GCC, "t.c", str(tmp_path), "t", "-O0")
    assert res.status == "error" and "boom" in res.diagnostics and res.binary is None
    assert comparator.classify_config(res.status, None, "x", 0) == comparator.COMPILE_FAILED


def test_compile_command_is_argument_list(monkeypatch, tmp_path):
    seen = {}

    def fake(cmd, **k):
        seen["cmd"], seen["shell"] = cmd, k.get("shell", False)
        return subprocess.CompletedProcess(cmd, 0, "", "warning: w")
    monkeypatch.setattr(compiler_runner.subprocess, "run", fake)
    res = compiler_runner.compile_source(CLANG, "t.c", str(tmp_path), "t", "-O2")
    assert isinstance(seen["cmd"], list) and not seen["shell"] and "-O2" in seen["cmd"]
    assert res.status == "ok" and "warning" in res.diagnostics


def test_compiler_launch_error(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise FileNotFoundError("gone")
    monkeypatch.setattr(compiler_runner.subprocess, "run", boom)
    assert compiler_runner.compile_source(GCC, "t.c", str(tmp_path), "t", "-O0").status == "tool_error"


def test_execution_timeout(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("x", 1, output=b"partial")
    monkeypatch.setattr(execution_runner.subprocess, "run", boom)
    res = execution_runner.run_binary("x", timeout=1)
    assert res.status == "timeout" and res.returncode is None and res.stdout == "partial"
    assert comparator.classify_config("ok", res.to_dict(), "", 0) == comparator.TIMEOUT


def test_execution_captures_output(monkeypatch):
    monkeypatch.setattr(execution_runner.subprocess, "run",
                        _fake_run(3, b"out\xff", b"err"))
    res = execution_runner.run_binary("x")
    assert (res.status, res.returncode, res.stderr) == ("ok", 3, "err") and "out" in res.stdout


# ---- test selection ----
def test_corpus_loads_and_selects():
    cases = load_corpus()
    assert len(cases) >= 6
    assert [c.name for c in select_tests(cases, ["arithmetic"])] == ["arithmetic"]
    assert select_tests(cases, None) == cases
    with pytest.raises(ValueError):
        select_tests(cases, ["nope"])


def test_corpus_sources_exist():
    assert all(c.expected_stdout is not None for c in load_corpus())


# ---- JSON report ----
def test_json_report_valid_with_odd_characters(tmp_path):
    weird = "caf\u00e9 \u2603 \x00 \ufffd \"quoted\" \\ \r\n"
    results = [{"test": "t", "source": "t.c", "description": "", "expected_stdout": weird,
                "expected_returncode": 0,
                "configs": [{"config": "gcc -O0", "compiler": "gcc", "opt_level": "-O0",
                             "compile": {"status": "ok", "command": ["gcc"], "returncode": 0,
                                         "diagnostics": weird},
                             "execution": ex(weird), "config_status": "pass"}],
                "comparison": comparator.compare_configs([cfg("gcc -O0", ex(weird))])}]
    report = rg.build_report([GCC], results, 10.0, ("-O0",))
    path = rg.write_json(report, str(tmp_path))
    with open(path, encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded["results"][0]["configs"][0]["execution"]["stdout"] == weird
    for key in ("run_id", "os", "python", "compilers", "summary"):
        assert key in loaded
    assert rg.format_summary(report)  # printing must not crash


# ---- end-to-end (real compiler) ----
def _can_build_and_run(comp) -> bool:
    """A compiler found on PATH may still be unusable (e.g. blocked by an OS policy)."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "hello.c")
        with open(src, "w") as fh:
            fh.write("int main(void) { return 0; }\n")
        res = compiler_runner.compile_source(comp, src, d, "hello", "-O0")
        return res.status == "ok" and execution_runner.run_binary(res.binary, 10).status == "ok"


REAL = [c for c in available_only(discover_compilers()) if _can_build_and_run(c)]
needs_compiler = pytest.mark.skipif(not REAL, reason="no WORKING gcc/clang (missing or unable to build/run)")


@needs_compiler
def test_end_to_end_all_corpus(tmp_path):
    results = pipeline.run_suite(REAL, load_corpus(), timeout=10)
    for r in results:
        assert len(r["configs"]) == 2 * len(REAL)
        for c in r["configs"]:
            assert c["config_status"] == comparator.PASS, (r["test"], c["config"], c)
        assert r["comparison"]["outcome"] in (comparator.MATCH, comparator.SINGLE)


@needs_compiler
def test_end_to_end_compile_error_and_timeout(tmp_path):
    comp = REAL[0]
    bad = tmp_path / "bad.c"
    bad.write_text("int main(void) { return 0 }\n")
    assert compiler_runner.compile_source(comp, str(bad), str(tmp_path), "bad", "-O0").status == "error"
    loop = tmp_path / "loop.c"
    loop.write_text("int main(void) { volatile int x = 1; while (x) {} return 0; }\n")
    cres = compiler_runner.compile_source(comp, str(loop), str(tmp_path), "loop", "-O0")
    assert cres.status == "ok"
    assert execution_runner.run_binary(cres.binary, timeout=1).status == "timeout"


@needs_compiler
def test_end_to_end_cli_writes_report(tmp_path):
    out = tmp_path / "r.json"
    assert cli.main(["run", "--test", "arithmetic", "--output", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["pass"] == 2 * len(REAL)
