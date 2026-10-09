# CompilerDiff — Project Walkthrough

Line numbers refer to the code as of the last verification (2026-10-09). If you edit a file, re-check them.

## 1. What this project is (and is not)
CompilerDiff builds small C programs with several compilers/optimization levels, runs each build, and
compares the observable behavior (stdout, stderr, exit code). It is **CPU C compiler testing**.
It is **not** NVIDIA GPU compiler verification: no CUDA, `nvcc`, `ptxas` or GPU has been used.
It is an educational tool, not a production verification system.

## 2. Execution flow: `python main.py run` -> JSON report
1. [`main.py`](main.py) `main()` (L71) parses args; `build_parser()` (L57) routes to `cmd_run()` (L32).
2. `cmd_run` loads tests: `test_corpus.load_corpus()` (src/test_corpus.py L22) reads `corpus/manifest.json`;
   `select_tests()` (L40) applies `--test`.
3. `compiler_discovery.discover_compilers()` (src/compiler_discovery.py L96) finds `gcc`, `clang`, `cl`.
   On Windows it first calls `load_vs_environment()` (L72), which runs Visual Studio's `vcvars64.bat`
   and copies the resulting environment variables into *this Python process only*, so clang/cl find `stdio.h`.
4. If no compiler is available, `cmd_run` prints install hints and exits with code 2 (nothing is faked).
5. `pipeline.run_suite()` (src/pipeline.py L14) loops: test x compiler x optimization level and calls `_run_one()` (L44).
6. `_run_one`: `compile_source()` -> if it compiled, `run_binary()` -> `classify_config()`.
7. After all configs of a test finish, `comparator.compare_configs()` (src/comparator.py L53) compares them.
8. `report_generator.build_report()` (L15) assembles the dict; `write_json()` (L45) saves
   `reports/report_<timestamp>.json`; `format_summary()` (L71) prints the terminal summary.
9. Exit code: 0 all good; 1 if any `fail_expected`/`compile_failed`/`timeout`/`run_error`/discrepancy; 2 usage/no compiler.

## 3. Modules and responsibilities
| Module | Responsibility |
|---|---|
| `main.py` | CLI (`check`, `list-tests`, `run`), exit codes |
| `src/compiler_discovery.py` | find compilers, read versions, load VS environment |
| `src/test_corpus.py` | load/validate manifest, select tests |
| `src/compiler_runner.py` | build argv for one compile, run it, return `CompileResult` |
| `src/execution_runner.py` | run a binary with timeout, return `ExecResult` |
| `src/comparator.py` | normalize output, classify one config, compare configs |
| `src/pipeline.py` | glue: loops over tests/configs |
| `src/report_generator.py` | JSON + terminal output |

## 4. How a C file is compiled and executed
- `build_command()` (src/compiler_runner.py L30) returns an **argument list** (no shell):
  - gcc/clang: `[compiler, -O0|-O2, -std=c11, -Wall, -Wextra, source, -o, output]`
  - MSVC `cl`: `[cl, /nologo, /Od|/O2, /std:c11, /W3, source, /Fe:output, /Fo:tempdir\]`;
    `MSVC_OPT_FLAGS` (L27) translates `-O0 -> /Od`, `-O2 -> /O2`.
- `compile_source()` (L47) runs it in a temp directory with `subprocess.run(..., timeout=60)` and **never raises**:
  it returns status `ok | error | timeout | tool_error`, plus the command, return code and diagnostics
  (compiler messages are kept separate from program output).
- `run_binary()` (src/execution_runner.py L37) runs `[binary]` with a timeout (default 10 s, `--timeout`),
  captures bytes, decodes as UTF-8 with replacement (`_text`, L28), and returns `ok | timeout | launch_error`.
- A timeout is **not a security sandbox**; only the trusted bundled corpus is ever executed.

## 5. Two different checks (important to explain)
| | Expected-output check | Cross-configuration comparison |
|---|---|---|
| Function | `classify_config()` (comparator.py L33) | `compare_configs()` (L53) |
| Question | "Does THIS build print what the manifest says?" | "Do ALL builds of this test agree with each other?" |
| Inputs | stdout + exit code vs `expected_stdout`/`expected_returncode` | exit code + stdout + stderr signature of each build |
| Results | `pass`, `fail_expected`, `compile_failed`, `timeout`, `run_error`, `no_expectation` | `match`, `potential_discrepancy`, `single_configuration`, `no_comparable_results` |
Both can disagree: all builds could agree with each other and still all be wrong vs. the manifest (e.g. a typo in the expected output).
`normalize_output()` (L26) only unifies line endings and strips trailing whitespace/blank lines; case, inner spacing and leading spaces count.
`compare_configs` groups builds by their signature `(returncode, stdout, stderr)` (`_signature`, L48); more than one group = `potential_discrepancy`. Compile failures and timeouts go to `not_compared`, never silently dropped.

## 6. How simulated discrepancy tests work
[`tests/test_discrepancy.py`](tests/test_discrepancy.py) builds fake execution dicts with the helper `ex(stdout, rc, stderr)` and calls the comparator directly - no compiler needed:
- L27 different stdout -> flagged; L37 different exit code; L43 different stderr
- L49 trailing whitespace/CRLF ignored; L55 meaningful whitespace/case differences still flagged
- L61 3-way split groups agreeing configs; L68 deterministic; L73 identical -> `match`
- L78 full pipeline with `monkeypatch`-ed `compile_source`/`run_binary` where `-O2` "prints" `43` instead of `42`: result must be `potential_discrepancy`, the summary counts it, and the text says "not proof of a compiler bug".
- L102/L110 corpus consistency and no `rand/time/malloc/%p`.
These prove the *detector* works. They do **not** prove the compilers are correct; no real discrepancy has been observed.

## 7. Audit results (2026-10-09)
**Actual results:** `pytest -q -rs`: 36 passed, 0 skipped. `main.py run`: 13 tests x 4 configs = 52 builds, 52 pass, 13/13 match, 0 discrepancies; report `reports/report_20261009-231817.json`. README numbers match.

**Conformance check of the 13 C programs** (hand review + tools): every program compiled with `clang -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Werror -O2` and `cl /W4 /WX /std:c11` with zero warnings, and ran under clang `-fsanitize=undefined` with no runtime errors. Tools can't *prove* absence of UB, so remaining uncertainty:
- `exitcode.c` returns `3`: the C standard only defines `0`, `EXIT_SUCCESS`, `EXIT_FAILURE`; other values are implementation-defined. Intentional, used to test exit-code comparison; kept deliberately.
- `%lld`, `%u` etc. are used with matching argument types. Output relies on `printf` formatting only (no floats, pointers, or uninitialized data).
- Strictly speaking "strictly conforming" also means no implementation-defined behavior; the exit code above is the only known exception.

**Limitations / non-bugs found (not changed):**
1. `-O3` is mapped to `/O2` for `cl` (L27) - a label can be more specific than the real flag.
2. `classify_config` does not check stderr against an expectation (the manifest has no `expected_stderr`); stderr is only compared across builds.
3. `discover_compilers` ignores the message returned by `load_vs_environment`, so *why* VS loading failed is not shown (compilers are simply reported missing/unusable).
4. The VS environment is loaded once into the process environment; this affects only this process.
5. `cl` writes `<test>.obj` into the temp dir with a fixed name; fine because builds run sequentially but would collide if parallelized.
6. Clang and `cl` share the Windows C runtime, so agreement is weaker evidence than e.g. GCC vs Clang on Linux.
7. Only 13 fixed programs; no random program generation (like Csmith). Compile timeout (60 s) is fixed.
8. `main.py check` returns exit 0 if at least one compiler works.

## 8. Ten interview questions (short answers)
1. **What does CompilerDiff do?** It compiles the same valid C program with several compilers/optimization levels, runs each, and flags behavior differences as potential discrepancies. (`pipeline.run_suite`)
2. **Why not compare assembly?** Different compilers legitimately generate different code with the same behavior; only observable behavior (stdout, stderr, exit code) matters. (`_signature`, comparator.py L48)
3. **Why must test programs avoid undefined behavior?** With UB the compiler may do anything, so a difference wouldn't indicate a bug. That's why `safe_limits.c` checks overflow *before* adding.
4. **Expected-output check vs differential comparison?** First compares one build to the manifest (`classify_config`); second compares builds to each other (`compare_configs`). They can disagree.
5. **What is a "potential discrepancy" and how would you triage it?** Builds disagreed. Check the program for UB (UBSan, `-Wall`), check flags/versions, reduce to a minimal repro, then decide; never claim a bug without that.
6. **How do you handle hangs?** `subprocess.run(timeout=...)` in `run_binary` returns status `timeout` with partial output. It prevents hangs but is not a sandbox.
7. **Why do runners return result objects instead of raising?** A compile error or timeout is test data; the run must continue and report it. (`compile_source` / `run_binary` never raise.)
8. **How is the output normalized and why so little?** Only CRLF->LF and trailing whitespace/blank lines (`normalize_output`). Windows `printf("\n")` writes `\r\n` in some cases; anything more aggressive could hide real bugs.
9. **How does it work on Windows with MSVC and Clang?** `load_vs_environment` runs `vcvars64.bat` (found with `vswhere`) and imports its variables so the compilers find headers/libs; `build_command` translates flags for `cl` (`/Od`, `/O2`).
10. **How would you extend this toward NVIDIA GPU compiler testing?** Add `nvcc -ptx`/`ptxas` as compile steps, compare PTX assembly success across `-O` levels and `sm_` targets, and (with a GPU) run kernels and compare results to a CPU reference. None of this exists yet; today it is CPU-only.

## 9. Commands to verify everything yourself
From the project root folder (PowerShell):
```powershell
.venv\Scripts\python.exe main.py check
.venv\Scripts\python.exe main.py list-tests
.venv\Scripts\python.exe main.py run
.venv\Scripts\python.exe main.py run --test arithmetic
.venv\Scripts\python.exe -m pytest -q -rs
.venv\Scripts\python.exe -m pytest tests\test_discrepancy.py -v
```
Expected (this machine): `check` lists clang and cl (gcc missing); `run` -> 52 pass / 13 match / 0 discrepancies; pytest -> 36 passed.
