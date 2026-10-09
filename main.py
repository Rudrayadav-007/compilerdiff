"""CompilerDiff command-line interface."""
from __future__ import annotations

import argparse
import os
import sys

from src import report_generator as rg
from src.compiler_discovery import INSTALL_HINTS, available_only, discover_compilers
from src.pipeline import DEFAULT_OPT_LEVELS, run_suite
from src.test_corpus import load_corpus, select_tests

ROOT = os.path.dirname(os.path.abspath(__file__))


def cmd_check(args) -> int:
    compilers = discover_compilers()
    print("Compilers:\n" + rg.format_compilers(compilers))
    missing = [c for c in compilers if not c.available]
    for c in missing:
        print(f"\nHow to install {c.name}: {INSTALL_HINTS[c.name]}")
    return 0 if available_only(compilers) else 2


def cmd_list(args) -> int:
    for c in load_corpus():
        exp = "expected output defined" if c.expected_stdout is not None else "no expected output"
        print(f"{c.name:<14} rc={c.expected_returncode}  {exp}  - {c.description}")
    return 0


def cmd_run(args) -> int:
    try:
        cases = select_tests(load_corpus(), args.test)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    compilers = discover_compilers()
    if not available_only(compilers):
        print("error: no C compiler (gcc/clang) found; nothing was tested.\n"
              + rg.format_compilers(compilers), file=sys.stderr)
        for c in compilers:
            print(f"  {c.name}: {INSTALL_HINTS[c.name]}", file=sys.stderr)
        return 2
    opts = tuple(args.opt)
    results = run_suite(compilers, cases, opts, args.timeout)
    report = rg.build_report(compilers, results, args.timeout, opts)
    path = rg.write_json(report, os.path.join(ROOT, "reports"), args.output)
    print(rg.format_summary(report))
    print(f"\nJSON report: {path}")
    s = report["summary"]
    bad = s["fail_expected"] + s["compile_failed"] + s["timeout"] + s["run_error"] \
        + s["potential_discrepancies"]
    return 1 if bad else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="main.py", description="CompilerDiff: differential C compiler testing")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="detect gcc/clang").set_defaults(func=cmd_check)
    sub.add_parser("list-tests", help="list corpus tests").set_defaults(func=cmd_list)
    r = sub.add_parser("run", help="compile, run and compare tests")
    r.add_argument("--test", action="append", help="test name (repeatable); default: all")
    r.add_argument("--timeout", type=float, default=10.0, help="per-program timeout in seconds")
    r.add_argument("--opt", nargs="+", default=list(DEFAULT_OPT_LEVELS), help="e.g. -O0 -O2 -O3")
    r.add_argument("--output", help="JSON report path (default: reports/report_<id>.json)")
    r.set_defaults(func=cmd_run)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
