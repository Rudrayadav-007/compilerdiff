# Learning Guide

## Flow
`main.py run` -> `discover_compilers()` -> `load_corpus()`/`select_tests()` -> `pipeline.run_suite()`:
for each test x compiler x opt level: `compile_source()` -> `run_binary()` -> `classify_config()`;
then `compare_configs()` per test -> `build_report()` -> `write_json()` + `format_summary()`.

## Modules
| File | Responsibility | Key functions (input -> output) |
|---|---|---|
| `src/compiler_discovery.py` | find gcc/clang | `discover_compilers(names) -> list[Compiler]` (uses `shutil.which`, `--version`) |
| `src/test_corpus.py` | load `corpus/manifest.json` | `load_corpus() -> list[TestCase]`, `select_tests(cases, names)` |
| `src/compiler_runner.py` | compile one config | `compile_source(compiler, src, workdir, test, opt) -> CompileResult` (never raises) |
| `src/execution_runner.py` | run binary w/ timeout | `run_binary(path, timeout) -> ExecResult` (ok/timeout/launch_error) |
| `src/comparator.py` | compare behavior | `normalize_output`, `classify_config`, `compare_configs` |
| `src/pipeline.py` | orchestration | `run_suite(...) -> list[dict]` |
| `src/report_generator.py` | JSON + terminal | `build_report`, `write_json`, `format_summary` |

## Terms
- **-O0/-O2**: no optimization / standard optimization. Valid programs must behave the same.
- **Undefined behavior (UB)**: the C standard imposes no rules (signed overflow, uninitialized reads); compilers may legitimately differ, so tests avoid it. `corpus/boundary.c` widens to `long long` before adding for this reason.
- **Differential testing**: compare several implementations on the same input; disagreement = investigate.
- **Subprocess argument list**: `["gcc","-O2",...]`, no shell, so no quoting/injection issues.
- **Timeout != sandbox**: it only stops hangs.
- **PTX**: NVIDIA's virtual GPU assembly emitted by `nvcc`; `ptxas` turns it into machine code.

## Commands
`python main.py check | list-tests | run [--test NAME]`, `python -m pytest -q`.

## Common errors
- `'gcc' not found on PATH`: install and reopen the terminal.
- `compile_failed` with "cannot execute as.exe ... blocked": OS application-control policy blocks the toolchain (seen on the author's machine); check diagnostics in the JSON report.
- All configs `fail_expected`: inspect `expected_stdout` in manifest vs actual stdout (unvalidated hand-computed expectations are possible).

## Interview questions
1. Why not compare assembly? (Different code, same behavior.)
2. Why must test programs avoid UB? (Divergence would not indicate a bug.)
3. What does a mismatch mean? How would you triage? (Reduce, check UB with `-fsanitize=undefined`, check versions, report minimal repro.)
4. Why normalize trailing whitespace only? (Conservative; don't hide real differences.)
5. How do you handle hangs/timeouts and what are the limits? (Timeout; not a sandbox.)
6. Why return data instead of raising from runners? (Failures are test results.)
7. How would you extend to CUDA? (`nvcc -ptx`, `ptxas`, compare across `-O` levels / sm targets; GPU runs need hardware.)

## How the comparison works (beginner version)
For each test the SAME C file is built several ways (e.g. clang -O0, clang -O2, cl -O0, cl -O2) and every build is run.
1. **Per configuration** (`classify_config`): did it compile? time out? Does its stdout and exit code equal the manifest's expected values? -> `pass`, `fail_expected`, `compile_failed`, `timeout`, ...
2. **Across configurations** (`compare_configs`): builds that ran normally are grouped by their *signature* = (exit code, stdout, stderr). One group -> `match`. More than one group -> `potential_discrepancy`, and the groups are listed.
3. **Normalization** is deliberately tiny: line endings (`\r\n` -> `\n`) and trailing spaces/blank lines are ignored. Case, inner spacing and leading spaces still count.
4. Compile failures and timeouts are never compared as if they were outputs; they appear in `not_compared`.
A discrepancy is a *lead to investigate* (check the test for undefined behavior, compiler versions, library differences), not proof of a compiler bug.

## Discrepancy validation (added later)
- `tests/test_discrepancy.py` feeds the comparator simulated results to prove it flags different stdout, exit codes and stderr, ignores only trailing whitespace, groups 3-way splits, is deterministic, and that a discrepancy flows through `run_suite` into the report and summary. It also checks the corpus manifest matches the files and that programs avoid `rand`, `time`, `malloc`, `%p`, etc.
- Corpus grew from 7 to 13 programs (`bitops`, `sieve`, `matrix`, `safe_limits`, `recursion`, `strings`), all free of undefined behavior (overflow is checked *before* it can happen).
