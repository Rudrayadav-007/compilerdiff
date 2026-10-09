"""Glue: compile + run every selected test on every configuration, then compare."""
from __future__ import annotations

import tempfile
from typing import Optional

from . import comparator, compiler_runner, execution_runner
from .compiler_discovery import Compiler, available_only
from .test_corpus import TestCase

DEFAULT_OPT_LEVELS = ("-O0", "-O2")


def run_suite(compilers: list[Compiler], cases: list[TestCase],
              opt_levels: tuple[str, ...] = DEFAULT_OPT_LEVELS,
              timeout: float = execution_runner.DEFAULT_TIMEOUT_S,
              workdir: Optional[str] = None) -> list[dict]:
    """Return one result dict per test. Only available compilers are used.

    Every configuration of a test compiles the SAME source file, so comparisons
    are always between identical inputs. Binaries live in a temp dir that is deleted.
    """
    usable = available_only(compilers)
    results = []
    with tempfile.TemporaryDirectory(prefix="compilerdiff_") as tmp:
        wd = workdir or tmp
        for case in cases:
            configs = []
            for comp in usable:
                for opt in opt_levels:
                    configs.append(_run_one(comp, case, opt, wd, timeout))
            results.append({
                "test": case.name,
                "source": case.source,
                "description": case.description,
                "expected_stdout": case.expected_stdout,
                "expected_returncode": case.expected_returncode,
                "configs": configs,
                "comparison": comparator.compare_configs(configs),
            })
    return results


def _run_one(comp: Compiler, case: TestCase, opt: str, wd: str, timeout: float) -> dict:
    cres = compiler_runner.compile_source(comp, case.source, wd, case.name, opt)
    execution = None
    if cres.status == "ok":
        execution = execution_runner.run_binary(cres.binary, timeout).to_dict()
    status = comparator.classify_config(cres.status, execution, case.expected_stdout,
                                        case.expected_returncode)
    return {"config": f"{comp.name} {opt}", "compiler": comp.name, "opt_level": opt,
            "compile": {k: v for k, v in cres.to_dict().items() if k != "binary"},
            "execution": execution, "config_status": status}
