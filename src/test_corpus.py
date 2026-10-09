"""Feature B: load the trusted C test corpus described by corpus/manifest.json."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

CORPUS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")


@dataclass
class TestCase:
    __test__ = False  # tell pytest this is not a test class
    name: str
    source: str                      # absolute path to the .c file
    description: str
    expected_stdout: Optional[str]   # None = no expectation defined
    expected_returncode: int = 0


def load_corpus(corpus_dir: str = CORPUS_DIR) -> list[TestCase]:
    """Read manifest.json; raise ValueError on malformed entries or missing files."""
    with open(os.path.join(corpus_dir, "manifest.json"), encoding="utf-8") as fh:
        entries = json.load(fh)
    cases = []
    for e in entries:
        try:
            path = os.path.join(corpus_dir, e["file"])
            case = TestCase(e["name"], path, e.get("description", ""),
                            e.get("expected_stdout"), e.get("expected_returncode", 0))
        except KeyError as exc:
            raise ValueError(f"manifest entry missing key {exc}: {e}") from exc
        if not os.path.isfile(path):
            raise ValueError(f"source file for test '{case.name}' not found: {path}")
        cases.append(case)
    return cases


def select_tests(cases: list[TestCase], names: Optional[list[str]] = None) -> list[TestCase]:
    """Return all cases, or only those whose name is in `names` (ValueError if unknown)."""
    if not names:
        return cases
    known = {c.name for c in cases}
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(f"unknown test(s): {', '.join(unknown)}. Known: {', '.join(sorted(known))}")
    return [c for c in cases if c.name in names]
