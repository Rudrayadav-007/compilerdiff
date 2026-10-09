"""Validation of the discrepancy-detection rules, using simulated (mocked) execution results.

Rules under test (see src/comparator.py):
  * stdout, stderr and exit code are all compared;
  * only trailing whitespace / line-ending differences are ignored;
  * a disagreement is reported as `potential_discrepancy`, never as a "bug";
  * compile failures and timeouts are listed in `not_compared`, not silently dropped.
"""
import os

from src import comparator, compiler_runner, execution_runner, pipeline
from src import report_generator as rg
from src.compiler_discovery import Compiler
from src.compiler_runner import CompileResult
from src.execution_runner import ExecResult
from src.test_corpus import TestCase, load_corpus


def ex(stdout="", rc=0, stderr=""):
    return {"status": "ok", "returncode": rc, "stdout": stdout, "stderr": stderr, "error": None}


def cfg(label, execution):
    return {"config": label, "config_status": "pass", "execution": execution}


def test_different_stdout_flags_discrepancy_with_details():
    r = comparator.compare_configs([cfg("clang -O0", ex("total=10\n")),
                                    cfg("clang -O2", ex("total=11\n"))])
    assert r["outcome"] == comparator.MISMATCH == "potential_discrepancy"
    by_config = {tuple(d["configs"]): d for d in r["differences"]}
    assert by_config[("clang -O0",)]["stdout"] == "total=10"
    assert by_config[("clang -O2",)]["stdout"] == "total=11"
    assert r["not_compared"] == []


def test_different_exit_codes_flag_discrepancy_even_with_same_stdout():
    r = comparator.compare_configs([cfg("a", ex("same\n", rc=0)), cfg("b", ex("same\n", rc=7))])
    assert r["outcome"] == comparator.MISMATCH
    assert sorted(d["returncode"] for d in r["differences"]) == [0, 7]


def test_different_stderr_flags_discrepancy():
    r = comparator.compare_configs([cfg("a", ex("x\n", stderr="warn A\n")),
                                    cfg("b", ex("x\n", stderr="warn B\n"))])
    assert r["outcome"] == comparator.MISMATCH


def test_stderr_trailing_whitespace_is_not_a_discrepancy():
    r = comparator.compare_configs([cfg("a", ex("x\n", stderr="note\n")),
                                    cfg("b", ex("x\r\n", stderr="note  \r\n\r\n"))])
    assert r["outcome"] == comparator.MATCH


def test_meaningful_whitespace_difference_is_not_hidden():
    for a, b in [("a b", "a  b"), (" a", "a"), ("A", "a"), ("a\nb", "a\n\nb")]:
        r = comparator.compare_configs([cfg("x", ex(a)), cfg("y", ex(b))])
        assert r["outcome"] == comparator.MISMATCH, (a, b)


def test_three_way_split_groups_the_agreeing_configs():
    r = comparator.compare_configs([cfg("a", ex("1")), cfg("b", ex("1")), cfg("c", ex("2"))])
    assert r["outcome"] == comparator.MISMATCH
    groups = sorted(d["configs"] for d in r["differences"])
    assert groups == [["a", "b"], ["c"]]


def test_comparison_is_deterministic():
    configs = [cfg("a", ex("1")), cfg("b", ex("2")), cfg("c", ex("1"))]
    assert comparator.compare_configs(configs) == comparator.compare_configs(list(configs))


def test_identical_results_match():
    r = comparator.compare_configs([cfg("a", ex("ok\n", 3, "e")), cfg("b", ex("ok\n", 3, "e"))])
    assert r["outcome"] == comparator.MATCH and r["differences"] == []


def test_discrepancy_found_through_pipeline_and_reported(monkeypatch, tmp_path):
    """Whole path with fake compile/run: -O2 'prints' a different number than -O0."""
    comp = Compiler("clang", True, "/fake/clang", "clang 17")
    case = TestCase("demo", "demo.c", "simulated", "42\n")

    monkeypatch.setattr(compiler_runner, "compile_source",
                        lambda c, src, wd, test, opt, timeout=60: CompileResult(
                            "ok", [c.name, opt], 0, "", binary=f"bin{opt}"))
    outputs = {"bin-O0": "42\n", "bin-O2": "43\n"}
    monkeypatch.setattr(execution_runner, "run_binary",
                        lambda binary, timeout=10: ExecResult("ok", 0, outputs[binary], ""))

    results = pipeline.run_suite([comp], [case], ("-O0", "-O2"))
    assert results[0]["comparison"]["outcome"] == comparator.MISMATCH
    statuses = {c["config"]: c["config_status"] for c in results[0]["configs"]}
    assert statuses == {"clang -O0": "pass", "clang -O2": "fail_expected"}

    report = rg.build_report([comp], results, 10.0, ("-O0", "-O2"))
    assert report["summary"]["potential_discrepancies"] == 1
    text = rg.format_summary(report)
    assert "potential_discrepancy" in text and "not proof of a compiler bug" in text


# ---- corpus consistency ----
def test_every_c_file_in_corpus_is_in_manifest_and_vice_versa():
    cases = load_corpus()
    corpus_dir = os.path.dirname(cases[0].source)
    on_disk = {f for f in os.listdir(corpus_dir) if f.endswith(".c")}
    assert on_disk == {os.path.basename(c.source) for c in cases}
    assert len({c.name for c in cases}) == len(cases)  # unique names


def test_corpus_programs_avoid_obvious_nondeterminism():
    banned = ("rand(", "time(", "scanf", "gets(", "malloc", "%p", "clock(")
    for case in load_corpus():
        code = open(case.source, encoding="utf-8").read()
        assert not [b for b in banned if b in code], case.name
