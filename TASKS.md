<!-- generated: eos-ai-scaffold -->
# Tasks

Working ledger for `eCAD-Hardware-Products`. The planner writes entries; each owning role
updates its own row. Roles are in [AGENTS.md](./AGENTS.md), the workflow in
[ORCHESTRATION.md](./ORCHESTRATION.md), the gate in [VERIFY.md](./VERIFY.md).

Status is one of: `todo`, `in-progress`, `blocked`, `review`, `done`.

## Active

| ID | Task | Owner | Mode | Status | Depends on |
|----|------|-------|------|--------|------------|
| T-002 | Author catalogs for the 260 remaining product directories | — | build | todo | T-001 |
| T-003 | Resolve the 6 unresolved BOM total mismatches | — | fix | blocked | owner decision on which figure is authoritative |
| T-004 | Verify component MPNs and unit costs against a distributor source | — | verify | todo | T-001 |
| T-005 | Seed the HEALTH-RING biosensor simulation and resolve its HbA1c spec margin | — | fix | blocked | owner decision: widen spec or improve design |
| T-006 | Route the generated boards and add pin-level signal nets | — | build | todo | T-002 |
| T-008 | Assign real IPC-7351 land patterns to every placed footprint | — | build | todo | T-007 |
| T-009 | Run DRC and export fabrication outputs (needs KiCad installed) | — | verify | blocked | KiCad unavailable: `apt` needs root |
| T-010 | CAD dataset, engineering semantic model, and robotic-joint mechanical validation (issue #27) | — | build | review | independent review |
| T-011 | Multi-domain foundation: domain adapters, null statuses, per-requirement results, spec §4 metadata (plan §21 item 3) | — | build | review | T-010 |
| T-012 | Electrical domain: the servo supply input on ngspice (plan §21 item 4) | — | build | review | T-011 |
| T-013 | Digital domain: the UART loopback on Icarus Verilog (plan §21 item 5) | — | build | review | T-012 |

### T-008 — Real land patterns

Owner: unassigned
Mode: build
Status: todo

Goal
: Every placed footprint carries pads from a verified IPC-7351 land pattern or a
  manufacturer drawing, replacing the body-and-courtyard placement models.

Why it is not done
: Package bodies are currently *estimated* from family and pin count, except for
  the chip passives in `cad_geometry.EXACT_PACKAGES`, which use standard land
  patterns. Pads are omitted entirely rather than invented — an invented land
  pattern looks fabricable and is not.

Acceptance criteria
: - Every footprint has pads matching a cited source.
  - `cad_geometry.package_model()` reports `exact: True` for every package used.

### T-009 — DRC and fabrication outputs

Owner: unassigned
Mode: verify
Status: blocked — KiCad is not installed and `apt` requires a password

Goal
: `kicad-cli pcb drc` passes on every board, and Gerber, drill and pick-and-place
  outputs are produced.

Note
: `kiutils` parses the board files in pure Python, which is what the current CAD
  validation uses. It cannot run DRC or export fabrication data. Nothing in this
  repository has been DRC-checked.

### T-005 — HEALTH-RING simulation is unseeded and sits on its spec limit

Owner: unassigned
Mode: fix
Status: blocked — needs an owner decision

Goal
: The PPG biosensor simulation is reproducible, and its HbA1c result either
  meets the stated specification with margin or the specification is corrected.

Evidence
: Measured 2026-08-08 over 8 consecutive runs of
  `eosHealth_CAD_Design/HEALTH-RING/simulation/ppg_biosensor_sim.py`:
  HbA1c mean error 0.409%, 0.509%, 0.632%, 0.409%, 0.451%, 0.578%, 0.424%,
  0.643% against a 0.5% specification. Exited non-zero on 4 of 8 runs.

Risks
: Seeding the RNG to a value that happens to pass would hide the marginal
  design rather than fix it. The seed and the design margin are separate
  decisions and both need making.

### T-006 — Route the generated boards

Owner: unassigned
Mode: build
Status: todo

Goal
: The generated `.kicad_pcb` files carry placed footprints, routed traces and
  copper pours, and the `.net` files carry pin-level signal connectivity.

Note
: What exists today is a starting board — outline, layer stack, design rules —
  and a netlist of components and power nets. This is stated in each generated
  `fabrication_notes.md` and in the `.net` header. It is deliberately not
  presented as a finished design.

### T-002 — Author catalogs for the remaining product directories

Owner: unassigned
Mode: build
Status: todo
Depends on: T-001 (complete)

Goal
: Every name in `tools/catalog/taxonomy.json` resolves to a product directory
  containing a datasheet, a costed BOM, a runnable simulation, and hardware trees.

Acceptance criteria
: - `python3 tools/generate_products.py --coverage` reports 337/337.
  - `python3 tools/validate_products.py --run` exits 0 with no new baseline entries.
  - No new entry is added to `tools/product_baseline.json`.

Files in scope
: `tools/catalog/divisions/*.json`, `tools/catalog/components.json`

Out of scope
: The sixteen hand-authored product directories that predate the catalog.

Verification
: | Check | Command | Result |
  |-------|---------|--------|
  | Coverage | `python3 tools/generate_products.py --coverage` | `74/337` at 2026-08-08 |
  | Contract | `python3 tools/validate_products.py --run` | `PASS` for what exists |

### T-003 — Resolve the six unresolved BOM total mismatches

Owner: unassigned
Mode: fix
Status: blocked — needs the product owner to say which figure is authoritative

Goal
: Each BOM's stated total equals the sum of its line items, with the correction
  applied to whichever side is actually wrong.

Affected
: `eConsumer/smart_devices` (+$1.00), `eDefense/tactical_communications` (+$1.00),
  `eosHealth/HEALTH-BAND-Neuro` (+$2.65), `eosHealth/HEALTH-KEY-ULTRA` (-$6.30),
  `eosHealth/HEALTH-LAB` (+$1.30), `eosHealth/HEALTH-RING` (-$5.00)

Risks
: Editing the total to match the sum hides a genuinely missing line item; editing
  a line item to match the total invents a cost. Neither is safe to guess.

### T-010 — CAD dataset, engineering model, robotic-joint mechanical validation

Owner: unassigned
Mode: build
Status: review (PR #36, from the fork's `feat/cad-mechanical-domain`, which is the local `wip/stack`)
Depends on: `fix/adapter-timeout-decode` and `fix/producer-cross-reference-checks` (cherry-picked as `3639778`, patch-identical); both are in the stack below this work

Goal
: A STEP design becomes an engineering model whose every value states its
  source and status, and one domain -- mechanical -- is validated end to end
  through the existing V0-V4 contract, on an architecture the other domains
  attach to without changing it.

Acceptance criteria (verbatim from the issue #27 implementation plan)
: - "Build the CAD dataset + engineering semantic model + first robotic-joint
    mechanical validation example, with enough structure that the exact same
    data architecture can support the next eight domains."

Files in scope
: `schemas/engineering-model/v1/`, `schemas/cad-dataset/v1/`, `tools/ecad_model/`,
  `tools/cad_dataset.py`, `tools/requirements-cad.txt`, `tools/constraints-cad.txt`,
  `datasets/cad/`, `tests/unit/test_engineering_model.py`,
  `tests/unit/test_cad_dataset.py`, `tests/mutation/run_mutations.py`, the
  `cad-dataset` job in `.github/workflows/ci.yml`, documentation,
  `ECAD_MULTI_DOMAIN_DATASET_PLAN.md`.

Out of scope
: Every domain other than mechanical; importers other than STEP; the v1
  receipt contract, which is reused unchanged; the product inventory. The
  multi-domain foundation is planned in `ECAD_MULTI_DOMAIN_DATASET_PLAN.md`
  §21 item 3 and in progress on the local branch
  `feat/multi-domain-foundation`, which builds on this one.

Risks
: MuJoCo stages have not run on native Linux x86_64: under emulation on Apple
  silicon the CPU has no AVX and `import mujoco` aborts, so only OpenCASCADE
  reproduction was verified there. Whether the `ubuntu-22.04` runner image
  ships `libGL.so.1` is unknown; the job installs `libgl1`. `cadquery-ocp`
  cannot be installed on the Python 3.10 legs, where the dataset tests skip by
  design. Push access is read-only for this account.

Verification (code at `bd999d5`, 2026-09-26)
: | Check | Command | Result |
  |-------|---------|--------|
  | Complete suite, CAD tests mandatory | `ECAD_REQUIRE_CAD_TOOLS=1 python3 run_all_tests.py` | `PASS` -- 245 passed, 0 skipped (macOS arm64, Python 3.14.4) |
  | Lint, new code | `ruff check tools/ecad_model tools/cad_dataset.py tests/unit/test_cad_dataset.py tests/unit/test_engineering_model.py tests/unit/test_ci_and_runner.py tests/mutation datasets/cad --select=E,F,W --ignore=E501` | `PASS` -- no findings |
  | Type check | `mypy tools run_all_tests.py tests/mutation/run_mutations.py --ignore-missing-imports --no-strict-optional` | `PASS` for new code -- the 11 errors reported are the same set as on `fea3fc4`, all in existing modules |
  | Derivation reproduces from the CAD | `python3 tools/cad_dataset.py check datasets/cad/robotic_joint_001` | `PASS` -- exit 0 |
  | V0-V4 receipt on a clean clone | `python3 tools/cad_dataset.py validate datasets/cad/robotic_joint_001 --output <dir>` | `PASS` as designed -- V0-V3 PASS; V4 BLOCKED: five illustrative limits met (WARNING) and REQ-XD-001 BLOCKED on the unselected actuator; not eligible for ebuild; 76 evidence digests re-hash |
  | Test discrimination | `python3 tests/mutation/run_mutations.py --workers 3` | `PASS` -- 68 of 68 mutants killed, after the unmutated baseline passed; each kill names the failing test |
  | Skip cannot go silent | the two dataset test files with `OCP`/`mujoco` absent, with and without `ECAD_REQUIRE_CAD_TOOLS=1` | `PASS` -- 45 skipped, each with a reason / all 45 red (25 failed, 20 errors) |
  | Linux aarch64 | the CI job's steps in `python:3.12-slim` with only `git` and `libgl1` added, offline from the pinned wheels | `PASS` -- `check` exit 0; 245 passed; `validate` gives the same gate verdicts as macOS |
  | Linux x86_64 | `check` in `python:3.12-slim` under emulation | `PASS` for OpenCASCADE reproduction (`check` exit 0, at `c9be0b6`). MuJoCo stages `NOT RUN`: the emulated CPU has no AVX and `import mujoco` aborts |
  | Pinned set resolves on Linux | `pip download -r tools/requirements.txt -r tools/requirements-cad.txt -c tools/constraints-cad.txt` for x86_64 and aarch64, Python 3.12 | `PASS` -- all 23 pins resolve unchanged |
  | Independent review | two reviews and a check of the plan's claims against the code, each finding checked by a separate verifier | `PASS` -- every confirmed finding within this task is fixed on the stack (`f4398f4`, `c9be0b6`, `bd999d5`); five in existing merged code or later domains are open, each listed with its owner in the plan §7.2 |

### T-011 — Multi-domain foundation: domain adapters, null statuses, per-requirement results

Owner: unassigned
Mode: build
Status: review (PR #37, from the fork's `feat/multi-domain-foundation`, stacked on #36)
Depends on: T-010 (`wip/stack`, which this branch builds on)

Goal
: The dataset pipeline knows no engineering domain: each domain attaches
  through one adapter, a value can be missing in the three ways the
  specification distinguishes, every requirement gets a result that says what
  was measured against what on which inputs, and the dataset metadata and
  licence provenance are what the specification asks for.

Acceptance criteria (verbatim from `ECAD_MULTI_DOMAIN_DATASET_PLAN.md` §21 item 3)
: 1. "No derived number changes." (with the named exceptions listed there)
  2. "No mechanical names (`mjcf`, `mujoco`, `derived/mechanical`, `.step`) in `dataset.py` or `requirements.py` outside the mechanical adapter"
  3. "No existing assertion is deleted or weakened; the mutation suite is re-anchored with a green baseline and zero survivors"
  4. "For each of `UNKNOWN`, `UNSPECIFIED`, `NOT_AVAILABLE`, as a density and as a limit: `BLOCKED MISSING_REQUIRED_INPUT` with the status and the path, and a schema-valid receipt."
  5. "With a requirement that is *not* illustrative, an `AI_ASSUMPTION` density, and separately an `AI_ASSUMPTION` limit quantity, give `INCONCLUSIVE INPUT_IS_AI_ASSUMPTION` both when the limit is met and when it is violated"
  6. "A test-only sample with no STEP ... its domain is `AVAILABLE`, mechanical `NOT_APPLICABLE` and every other domain `NOT_IMPLEMENTED`; without that adapter registered, `build` refuses and `validate` is `BLOCKED DOMAIN_NOT_IMPLEMENTED`."
  7. "One result per requirement and reference, naming the receipt check that decided it ..."
  8. "The manifest's domain status is derived from the registry, and a test forging it fails `check`."
  9. "The versioning rule of §9.3 replaces the pre-release declaration in the schema documentation, taking effect at the merge."
  10. "The protocol is exercised end to end by a test-only artefact-first adapter"

Files in scope
: `tools/ecad_model/` (domains/, results.py, dataset.py, requirements.py,
  quantity.py, builder.py, mjcf.py), `schemas/engineering-model/v1/`,
  `schemas/cad-dataset/v1/`, `datasets/cad/robotic_joint_001/`,
  `tests/unit/test_engineering_model.py`, `tests/unit/test_domain_adapter.py`,
  `tests/unit/test_cad_dataset.py`, `tests/mutation/run_mutations.py`,
  documentation, the plan.

Out of scope
: Any domain but mechanical; renaming `dataset-item.json` or moving
  `datasets/cad/`; training records; cross-domain rules (`from_result`).

Risks
: The adapter protocol is provisional: one production domain uses it, and the
  test-only Verilog adapter runs no simulator, so no metric has yet been
  parsed from a non-Python tool. The engineering-model and cad-dataset v1
  schemas change in place relative to the stack; they are declared stable
  from this branch's merge.

Verification (2026-09-26/27; code at `000309b` unless a row names another commit. `000309b` differs from `dbf73e1` only in one test fixture; `dbf73e1` from `bb43124` by the fourth review's fixes)
: | Check | Command | Result |
  |-------|---------|--------|
  | Complete suite, CAD tests mandatory | `ECAD_REQUIRE_CAD_TOOLS=1 python3 run_all_tests.py` | `PASS` -- 332 passed, 0 skipped, on a clean clone, the tree clean afterwards (macOS arm64, Python 3.14.4) |
  | Lint, new code | `ruff check tools/ecad_model tools/cad_dataset.py tests/unit/test_cad_dataset.py tests/unit/test_engineering_model.py tests/unit/test_domain_adapter.py tests/unit/test_ci_and_runner.py tests/mutation datasets/cad --select=E,F,W --ignore=E501` | `PASS` -- no findings |
  | Type check | `mypy tools run_all_tests.py tests/mutation/run_mutations.py --ignore-missing-imports --no-strict-optional` | `PASS` for new code -- the same 11 errors in the same seven existing modules as at `bd999d5`; none in `tools/ecad_model` |
  | Derivation reproduces | `python3 tools/cad_dataset.py check datasets/cad/robotic_joint_001` on a clean clone of `dbf73e1` | `PASS` -- exit 0 |
  | Criterion 1 on a clean clone of `dbf73e1` | `validate`, then every check's verdict and metrics against the clean-clone receipt of `bd999d5`, and the results against those of `bb43124` | `PASS` -- the 19 checks both runs have give identical verdicts and metrics; `v2.cad-model-invariants` is split into `v2.dataset-reproduction` and `v2.mechanical.model-invariants`, both `PASS`; the other differences are the named renames. V0-V3 `PASS`, V4 `BLOCKED` as designed; 94 evidence digests re-hash (the rise from 82 is the recorded inputs of each check); 15 results, bound to the receipt, identical to `bb43124`'s apart from run-bound fields |
  | Criterion 2 | `grep -nE "mjcf\|mujoco\|derived/mechanical\|\.step" tools/ecad_model/dataset.py tools/ecad_model/requirements.py` | `PASS` -- no match |
  | Test discrimination | `python3 tests/mutation/run_mutations.py --workers 7` (and `--only` for the second part) | `PASS` -- at `dbf73e1`, 222 of 222 mutants killed in two runs, each after the unmutated baseline passed (54, then the other 168), each kill naming its test (96 by `test_engineering_model.py`, 84 by `test_domain_adapter.py`, 42 by `test_cad_dataset.py`). The two earlier full runs each left one survivor that was a missing test, closed by `b4fca10` and `7b58a76` |
  | Skip cannot go silent (at `bb43124`) | the dataset test files with `OCP`/`mujoco` absent, with and without `ECAD_REQUIRE_CAD_TOOLS=1` | `PASS` -- the 50 CAD tests skip, each with a reason, and the 122 fast tests (the adapter fixture included) still pass / with `ECAD_REQUIRE_CAD_TOOLS=1` all 50 are red (26 failed, 24 errors) |
  | Linux aarch64 | the CI job's steps in `python:3.12-slim` with only `git` and `libgl1` added, offline from the pinned wheels, on a clean clone of `000309b` | `PASS` -- `check` exit 0; 332 passed; `validate` gives the same gate verdicts as macOS. One subtest is skipped on Python 3.12, with its reason: the document nested too deeply to *check* cannot be built there, because 3.12's JSON parser and `repr` stop at the same depth (about 10 000); the too-deep-to-parse case runs. At `dbf73e1` this subtest failed in its fixture, the reason for `000309b` |
  | Linux x86_64 | -- | `NOT RUN` on this branch; MuJoCo cannot run under emulation here (T-010) |
  | Independent review | four reviews, each finding checked by a separate verifier: five lenses on the foundation; a check of every fix; a focused review of the second round and the documentation; the same of the third | `PASS` -- 59 findings confirmed (2 refuted); then 49 found fixed and 10 partly, with new defects in the fixes; then 19 more, none refuted; then 22 more, none refuted. All closed on `dbf73e1` (plan §7.5). The fourth round's fixes have had no review of their own. One defect in merged code is open: ENGINE-1 (plan §7.2) |

### T-012 — Electrical domain: the servo supply input on ngspice

Owner: unassigned
Mode: build
Status: review (PR #38, from the fork's `feat/domain-electrical`, stacked on #37; two independent reviews at `bf04f1b`, whose findings are fixed at `11b19b1`, `555bfd7`, `ec37115` and `49887ac` (plan §7.6); the fixes have had no review of their own)
Depends on: T-011 (`feat/multi-domain-foundation` at `042f934`, which this branch builds on)

Goal
: A SPICE netlist becomes an engineering model whose every value states its
  source and status, ngspice runs a deck written from that model, and the
  electrical domain is validated end to end through the same V0-V4 runner as
  mechanical, on a sample that invents no part, rating or requirement.

Acceptance criteria (verbatim from `ECAD_MULTI_DOMAIN_DATASET_PLAN.md` §21 item 4)
: 1. "ngspice supply sample"
  2. "output capture and metric parsing"
  3. "version parsing"
  4. "`spice` CI job"
  5. "First artefact-first domain; the protocol stops being provisional here, and the PR lists every protocol change the domain forced with the matching change to the mechanical adapter (SCOPE-15)."

Acceptance criteria (verbatim from the plan §10, for every domain)
: 6. "Each domain lands as one PR with: at least one sample; a met limit (`PASS` against a real requirement, `WARNING` against an illustrative one), a `FAIL` from a mutated input and a `BLOCKED` from a missing input; an invalid-input and a boundary sample (spec §21); negative tests and mutants; per-domain documentation (spec §28); and a CI job that makes a skip a failure."

State of each criterion (the plan §21 item 4 carries the same markers)
: 1. IMPLEMENTED: `datasets/cad/servo_supply_001` builds, checks and validates as designed (Verification).
  2. IMPLEMENTED for ngspice (ARCH-2, the ngspice half); the `run_process` output copy is not needed by ngspice and stays open for the HDL and KiCad domains.
  3. IMPLEMENTED (RESULT-8); RESULT-2 is PARTIAL, fixed on the ngspice path only.
  4. PARTIAL: the job is written and its shape is tested (since `ec37115`, strictly enough that an `if:`, `|| true`, `--ignore` or a step-level override fails the test); it has never run on a runner, and ngspice is not pinned (BLOCKED until the runner's version is known). Its steps passed in arm64 Linux containers on ngspice-36 and 44.2 at `f6dee36` (Verification of the review fixes, below), after the fix of a test that failed on ngspice-36; after the branch review (the tenth metric, the new goldens) they passed again on ngspice-36 at `e938cc8`; 44.2 has not been re-run since `f6dee36`.
  5. IMPLEMENTED: `domains/base.py` and the plan §11 state the protocol stable and list its one change, `Extraction.producer`.
  6. Sample IMPLEMENTED. Met limit: `WARNING` against the illustrative limits IMPLEMENTED; `PASS` against a real requirement only on a test-built copy with a fixture rating, since no real part is selected. `FAIL` from a mutated input IMPLEMENTED (test-built copies, real ngspice). `BLOCKED` from a missing input IMPLEMENTED (the committed sample). Invalid-input and boundary samples PARTIAL: test-built copies, not committed items (plan §20 Q17). Negative tests IMPLEMENTED; mutants IMPLEMENTED: 322 at `ec37115`, the 101 of the electrical branch killed there after green baselines and the other 221 last run at `57f4fee` (Verification of the branch review). Documentation IMPLEMENTED (`docs/electrical-domain-v1.md`). CI job PARTIAL, as in 4.

Files in scope
: `tools/ecad_model/spice.py`, `tools/ecad_model/domains/` (electrical.py,
  base.py, mechanical.py, `__init__.py`), `tools/ecad_model/__init__.py`,
  `tools/ecad_model/dataset.py`, `tools/ecad_validation/adapters/ngspice.py`,
  `tools/ecad_validation/adapters/capabilities.py`,
  `schemas/engineering-model/v1/` (engineering-model, design-annotations,
  electrical-vocabulary), `datasets/cad/servo_supply_001/`, the regenerated
  `datasets/cad/robotic_joint_001/dataset-item.json`, `.gitattributes`,
  `tests/unit/test_spice_netlist.py`, `tests/unit/test_ngspice_adapter.py`,
  `tests/unit/test_electrical_domain.py`, `tests/unit/test_electrical_spice.py`,
  the edited `test_domain_adapter.py`, `test_engineering_model.py` and
  `test_ci_and_runner.py`, `tests/mutation/run_mutations.py`, the `spice` job
  in `.github/workflows/ci.yml`, documentation, the plan.

Out of scope
: Other network classes, element types, analyses and subcircuits; LTspice and
  PSpice; a KiCad schematic importer; the SEC-2 runner guard (its own
  foundation change, plan §7.2); the general RESULT-2 fix; moving
  `datasets/cad/` (the brief kept the layout, plan §20 Q8); training records.

Risks
: The CI runner's ngspice is Unknown until the `spice` job runs: ngspice-36
  and 44.2 were run for real only in arm64 containers, not on the x86_64
  runner, and a version that prints differently makes cases `INCONCLUSIVE`
  or `BLOCKED`, loudly. The reference tolerances were set on ngspice-47 on
  macOS arm64; every reference also passed on 36 and 44.2 in those
  containers. ngspice's output can differ run to run in its progress
  report, which 47 and 44.2 write to stdout and 36 to stderr (plan §20
  Q11). A committed case document, and the committed deck it names, still
  run before the runner decides what counts (SEC-2): a hand-edited deck's
  `.control` `shell` block ran during `validate` (the branch review).
  REF-EL-010's tolerance and the moved precharge goldens were checked on
  ngspice-47 only.
  The mutation harness now needs ngspice, the CAD kernel and MuJoCo on one
  machine. Push access is read-only for this account.

Verification (2026-09-27, macOS arm64, Python 3.14.4, ngspice-47; code at `37b2de7` plus this change's docstring fix)
: | Check | Command | Result |
  |-------|---------|--------|
  | Complete suite, CAD and ngspice tests mandatory | `ECAD_REQUIRE_CAD_TOOLS=1 ECAD_REQUIRE_SPICE_TOOLS=1 python3 run_all_tests.py -q -p no:cacheprovider --tb=short` | `PASS` -- 397 passed, 0 failed, 0 skipped, exit 0 (249 s); the tree unchanged afterwards. The 63 electrical tests (16 parser, 14 ngspice adapter, 26 domain, 7 real ngspice) are among them |
  | Lint, changed Python | `ruff check <the 17 Python files changed since 042f934> --select=E,F,W --ignore=E501` | `PASS` -- "All checks passed!" |
  | Type check | `mypy tools run_all_tests.py tests/mutation/run_mutations.py --ignore-missing-imports --no-strict-optional` | `PASS` for new code -- "Found 11 errors in 7 files (checked 44 source files)", the baseline set, none in `tools/ecad_model` |
  | Derivation reproduces, clean copy | `python3 tools/cad_dataset.py check datasets/cad/servo_supply_001`, then `build`, then `git status --short` | `PASS` -- `check` exit 0; `build` exit 0, five files written, 0 lines of `git status` |
  | V0-V4 receipt, clean copy | `python3 tools/cad_dataset.py validate datasets/cad/servo_supply_001 --output <dir>` | `PASS` as designed -- exit 0; V0-V3 `PASS`; V4 `BLOCKED`: REQ-EL-001..004 `WARNING WITHIN_ILLUSTRATIVE_LIMIT`, REQ-EL-005..007 `BLOCKED MISSING_REQUIRED_INPUT` (48.0, 0.0533906, 372.465 measured by `v3.REF-EL-001`); not eligible; 16 results bound to the receipt; 82 evidence digests re-hash; ngspice version `47` |
  | FAIL from a mutated input, real ngspice | clean copies with `R_PRE ... 1` and with the bypass command at 5 ms, rebuilt, `check`, `validate` | `PASS` -- REQ-EL-001 `FAIL CORNER_LIMITS_FAILED` at 40.6812 A, every reference `PASS`; REQ-EL-002 `FAIL` at 31.2169 V, REF-EL-003 `BLOCKED REFERENCE_NOT_APPLICABLE`; both overall `FAIL` |
  | Without ngspice | `validate` with ngspice absent from `PATH` | `PASS` -- 13 cases `BLOCKED TOOL_NOT_INSTALLED`, 3 `BLOCKED MISSING_REQUIRED_INPUT`, no simulator version in any of the 16 results |
  | Without the CAD kernel | `check`, `build`, `validate` in a virtualenv with only `tools/requirements.txt` and pytest (no OCP, no MuJoCo) | `PASS` -- all exit 0, tree unchanged, same gate verdicts |
  | Skip cannot go silent | `pytest tests/unit/test_electrical_spice.py` with ngspice absent from `PATH`, without and with `ECAD_REQUIRE_SPICE_TOOLS=1` | `PASS` -- 7 skipped, each with its reason / 7 failed |
  | Mechanical sample unchanged | `git diff 042f934 HEAD -- datasets/cad/robotic_joint_001/`; `check datasets/cad/robotic_joint_001` on the clean copy | `PASS` -- one entry changed (electrical `NOT_IMPLEMENTED` -> `NOT_APPLICABLE`); `check` exit 0 |
  | ngspice behaviour the grammar and the docs rely on | probe decks run with `ngspice -b ... </dev/null`, each in its own directory | `PASS` -- reproduced on ngspice-47: `-r` makes no `.meas` and `-o` moves them to the log; `numdgt=12` still prints six digits; a failed `.meas` goes to stderr with exit 0; a duplicate name prints twice; `1M`, `1MEG`, `10uF`, `10F`, `2kohm`, `1ms`, `1mil` read as the traps say; `gnd` is ground; a `pa_00` node is taken over; the title line swallows a card; `+` joins lines; a card after `.end` is read and a missing `.end` accepted; a dangling node is accepted; `.control` `shell`, a working-directory `.spiceinit` (not with `-n`), a `*#` line (even with `-n`) and a `*ng_script` title all ran; `noacct` removes the operating-point table and statistics but not the progress report, and `norefvalue` removes that |
  | Test discrimination, the 63 new mutants | `python3 tests/mutation/run_mutations.py --workers 4 --only <21 names>`, then a scratch driver calling the harness's `run()` for the other 50 (two runs of 25, 5 workers) | `PASS` -- 63 of 63 killed, none survived, each kill naming its test. The harness reported "baseline green" and killed 13 before a 470 s wall-clock limit stopped it; `run()` (the same copy, edit, rebuild and suites, without a second baseline, on the same code and tests) killed 25 of 25 and 25 of 25. Several are killed first by a module's doctests, which run first, rather than by the test the design names |
  | Test discrimination, all 285 mutants | `python3 tests/mutation/run_mutations.py` | `NOT RUN` -- only the 63 new mutants were run in this change; the 222 of the foundation were last run at `dbf73e1` (T-011). Run for the review fixes, below |
  | CI `spice` job | the job itself | `NOT RUN` -- push access is read-only; its shape is tested by `test_spice_job_cannot_skip_silently` |
  | ngspice-36 and 44.2 | a real run of either | `NOT RUN` in this session; the adapter tests replay their output as recorded in arm64 containers earlier on 2026-09-27 (`MEMORY.md`). Run for the review fixes, below |
  | Linux | the `spice` job's steps in a container | `NOT RUN` here; run for the review fixes, below |
  | Independent review | CLAUDE.md rule 4: one verification pass by a separate agent at `816e625`, which re-ran the suite, lint, types, `check` and `validate` of both samples, compared the mechanical receipt with `042f934`'s, and re-derived the closed forms and every model value's source | `PARTIAL` -- no blocking problem found; its one finding, public adapter methods without a run example, is fixed in `57f4fee`. The fixes (`57f4fee`, `f6dee36`) have had no review of their own |

Verification of the review fixes (2026-09-27 UTC; code at `f6dee36` unless a row names `57f4fee`. `57f4fee` adds docstrings, their examples and two tests to `816e625`, and touches code files only in docstrings; `f6dee36` changes one assertion of the real-ngspice test S1. Neither changes what the pipeline does)
: | Check | Command | Result |
  |-------|---------|--------|
  | Complete suite, CAD and ngspice tests mandatory, macOS arm64, Python 3.14.4, ngspice-47, clean clone | `ECAD_REQUIRE_CAD_TOOLS=1 ECAD_REQUIRE_SPICE_TOOLS=1 python3 run_all_tests.py -q -p no:cacheprovider --tb=short` | `PASS` -- 399 passed, 0 failed, 0 skipped, exit 0 (779 s, on a machine the mutation run loaded); the tree unchanged afterwards. The 64 electrical tests (16 parser, 15 ngspice adapter, 26 domain, 7 real ngspice) are among them. At `57f4fee`: 399 passed, exit 0 (213 s) |
  | The example tests fail without an example | in a scratch copy of the working tree that became `57f4fee`: the examples of `ElectricalAdapter.metrics` and `NgspiceAdapter.run` removed; then that of `ElectricalAdapter.document_schemas`; then a public function with no example added to `spice.py` | `PASS` -- each run exit 1, naming each function; before the examples were written, the electrical test named all 14 `ElectricalAdapter` methods |
  | Lint, changed Python | `ruff check <the 17 Python files changed since 042f934> --select=E,F,W --ignore=E501 --no-cache` | `PASS` -- "All checks passed!" |
  | Type check | `mypy tools run_all_tests.py tests/mutation/run_mutations.py --ignore-missing-imports --no-strict-optional` | `PASS` for new code -- "Found 11 errors in 7 files (checked 44 source files)", the baseline set, none in a file this branch changed |
  | Derivation reproduces and V0-V4 receipt, macOS, clean clone | `python3 tools/cad_dataset.py check` of both samples; `validate datasets/cad/servo_supply_001` | `PASS` as designed -- both `check` exit 0; `validate` exit 0: V0-V3 `PASS`, V4 `BLOCKED` (4 `WARNING WITHIN_ILLUSTRATIVE_LIMIT`, 3 `BLOCKED MISSING_REQUIRED_INPUT`), overall `BLOCKED`, not eligible, 16 results, source `f6dee36` not dirty, ngspice `47` |
  | The `spice` job's steps on Linux, ngspice-36 | an ubuntu:22.04 arm64 container, a clean clone: apt `ngspice git python3.11` (ngspice 36+ds-1ubuntu0.1; Python 3.11.0rc1, where the job uses 3.12), `pip install -r tools/requirements.txt pytest`, then with `ECAD_REQUIRE_SPICE_TOOLS=1` the job's `run_all_tests.py --tb=short`, `check` and `validate` | `PASS` -- 348 passed, 52 skipped, 0 failed; all 64 electrical tests passed. The skips are the 51 tests of `test_cad_dataset.py` (the job installs no CAD kernel) and the subtest of `test_domain_adapter.py` that skips where Python's JSON parse and print depths are too close (its probe returned `None` on 3.11.0rc1 and 3.12.14). `check` exit 0; `validate` exit 0 with the designed receipt, ngspice `36`, source not dirty. At `57f4fee` the same run failed S1's two subtests, below |
  | The `spice` job's steps on Linux, ngspice-44.2 | a python:3.12-slim (Debian 13) arm64 container, the same steps (ngspice 44.2+ds-1, Python 3.12.14) | `PASS` -- 348 passed, 52 skipped (the same), 0 failed; `check` exit 0; `validate` exit 0 with the designed receipt, ngspice `44.2`. The same at `57f4fee` |
  | S1 on ngspice-36, before and after `f6dee36` | the ubuntu:22.04 container at `57f4fee` with two busy loops per CPU: two adapter runs; S1 as committed; S1 with the fix, three times; two adapter runs; the 7 real-ngspice tests | `PASS` for the fix -- every adapter run wrote two or three ` Reference value : <t>` lines to stderr and none to stdout, and read 9 of 9 measurements; S1 as committed failed both subtests on those lines; with the fix it passed 3 runs of 3; the 7 tests passed |
  | `.options norefvalue` on ngspice-36 and 44.2 (plan §20 Q11) | the committed deck and a copy with `.options noacct norefvalue`, three runs of each per version, under load | Observed -- without it 36 wrote two or three progress reports per run to stderr and 44.2 two to stdout; with it neither wrote any. Every run exit 0, with no stderr line but 36's four warnings; the nine measurement lines were identical across the six runs of each version. The deck is unchanged: that is Q11, the maintainer's call |
  | Test discrimination, all 285 mutants | `python3 tests/mutation/run_mutations.py --workers 8` on a clean clone of `57f4fee`, with ngspice-47, the CAD kernel and MuJoCo | `PASS` -- "baseline green", then "285 of 285 mutants killed", exit 0, in 61 minutes. None survived, and each kill names its test: 114 by `test_engineering_model.py`, 84 by `test_domain_adapter.py`, 37 by `test_cad_dataset.py`, 20 by `test_electrical_domain.py`, 17 by `test_ngspice_adapter.py`, 13 by `test_spice_netlist.py`. `f6dee36` only lets S1 accept more on stderr, so a mutant that passed S1 at `57f4fee` still passes it and every kill stands (Inferred; not re-run at `f6dee36`) |
  | CI `spice` job, and Linux x86_64 | the job itself | `NOT RUN` -- push access is read-only; the containers above are arm64 |
  | Coverage of new and changed code | a coverage tool | `NOT RUN` -- none is installed in this environment (no `coverage`, no `pytest-cov`) |

Verification of the branch review (2026-09-28/29, macOS arm64, Python 3.14.4, ngspice-47; code at `ec37115`, whose documentation commit changes only Markdown; each row on a clean clone unless it says otherwise)
: | Check | Command | Result |
  |-------|---------|--------|
  | Complete suite before the fixes | `ECAD_REQUIRE_CAD_TOOLS=1 ECAD_REQUIRE_SPICE_TOOLS=1 python3 run_all_tests.py -q -p no:cacheprovider --tb=short` at `bf04f1b` | `PASS` -- 402 passed, 0 failed, 0 skipped (201 s) |
  | Complete suite after the fixes | the same at `ec37115` | `PASS` -- 410 passed, 0 failed, 0 skipped, exit 0 (219 s as pytest counts it; the machine slept during the run); the clone unchanged afterwards. The 73 electrical tests (16 parser, 16 ngspice adapter, 31 domain, 10 real ngspice; 67 at `bf04f1b`) are among them |
  | Lint, changed Python | `ruff check <the 11 Python files changed since bf04f1b> --select=E,F,W --ignore=E501 --no-cache` | `PASS` -- "All checks passed!" |
  | Type check | `mypy tools run_all_tests.py tests/mutation/run_mutations.py --ignore-missing-imports --no-strict-optional` | `PASS` for changed code -- "Found 11 errors in 7 files (checked 44 source files)", the baseline set, none in a file the review fixes changed |
  | Derivation reproduces | `python3 tools/cad_dataset.py check` of both samples | `PASS` -- both exit 0 |
  | V0-V4 receipt | `python3 tools/cad_dataset.py validate datasets/cad/servo_supply_001 --output <dir>` | `PASS` as designed -- exit 0; V0-V3 `PASS` (REF-EL-001..010), V4 `BLOCKED`: REQ-EL-001..004 and 008 `WARNING WITHIN_ILLUSTRATIVE_LIMIT`, REQ-EL-005..007 `BLOCKED MISSING_REQUIRED_INPUT`; overall `BLOCKED`, not eligible; 18 results; 90 evidence entries (47 digests) re-hash; `v0.pinned-clean-source` `PASS`; ngspice `47` |
  | The reviewers' reproductions | their scripts, copied with the repository path pointed at a clone of `ec37115`: `time_falsepass.py time` and `n_bus`, `slow_fault.py slow` and `fast`, `variant.py` with a zero C_BULK, SW_FLT ROFF=1k and the bypass at 14.5 ms, and `node_probe.py` (also with its other node renamed `n_a`) | `PASS` -- `time` refused by the parser (`'time' is not a node name`), the `n_bus` control FAILs REQ-EL-900 at 48.0; the slow fault refused (`S_FLT closes at 0.15000000000000002 s ...`), the fast control FAILs at 372.465; the zero capacitance refused with a receipt written; ROFF=1k: every reference `PASS` but REF-EL-010 `BLOCKED REFERENCE_NOT_APPLICABLE`; 14.5 ms: REQ-EL-001 `WARNING`, REQ-EL-008 `FAIL` at 28.3205, REF-EL-010 `BLOCKED`; the 81 names of the node probe all refused, and their 12 `n_` forms read correctly by ngspice |
  | Names ngspice misreads | a divider on each of 174 names, five `.meas` reading it, and a switch model of each name, run with `ngspice -b` directly (no parser) | Verified -- 12 misread as nodes (`agauss all alli allv aunif gauss gnd limit pa_00 temper time unif`), 2 as models (`GND`, `TEMPER`); with `n_` and `SW_`, none |
  | Closed forms against ngspice | a scratch script, written apart from the adapter, on 13 variants (the sample; SW_FLT ROFF 1k and 100; SW_BYP ROFF 1k; the bypass at 5, 14.5 and 24.9 ms; no ESR, alone and with 14.5 ms; VH=1 V with a 1 ms command; R_PRE 1 ohm; an 8 A load) | Verified -- every precharge, settled and startup value within its tolerance of ngspice-47 where the form applies; the bypass surge, where it is the startup peak, 3e-4 to 8e-4 below the form (28.3205 against 28.3286 A at 14.5 ms), which is why that form then does not apply |
  | New tests fail before the fixes | the tests of `555bfd7` for CS-2..CS-5 copied into a clone of `11b19b1` (before the electrical fixes); the tests of `11b19b1` into one of `bf04f1b`; the runner test with `dataset.py` of `bf04f1b` | `PASS` -- on `11b19b1`, 25 tests and subtests of the fault window, the refused values, the closed forms, the startup peak and the two real-ngspice tests failed; on `bf04f1b`, 28 (22 of the parser test, some only for its new message, and 6 of the electrical tests, among them the rail named `time` and the model `TEMPER`); the runner test raised `ZeroDivisionError` out of `validate` |
  | CI tests catch a hidden skip | the four edits of the review (and two on the cad-dataset job) applied to the workflow text in memory, against the new and the old tests | `PASS` -- each fails the new test of its job and passed the old one |
  | Test discrimination, the electrical branch | `python3 tests/mutation/run_mutations.py --workers 4 --only <batch>`, nine batches of 9 to 13 covering all 101, on a clean clone of `ec37115` | `PASS` -- "baseline green" and "N of N mutants killed" in each; 101 killed, none survived: 42 by `test_electrical_domain.py`, 22 by `test_engineering_model.py`, 18 by `test_ngspice_adapter.py`, 16 by `test_spice_netlist.py`, 3 by `test_domain_adapter.py`. Three batches ran 8 m 1 s to 8 m 39 s (two of them concurrently); a tool retry started batch 8 twice, and the log kept is the complete second run. Earlier, the 4 name mutants at `11b19b1` (4 of 4) and 10 of the electrical ones at `555bfd7` (10 of 10) |
  | Test discrimination, the other 221 | `run_mutations.py` | `NOT RUN` here -- last run at `57f4fee` (above); their target lines and killing tests are unchanged |
  | Two statements of the `555bfd7` commit message | -- | Wrong, not amended: it says 16 new mutants (it adds 15) and that the goldens moved "in the ninth to twelfth figure" (the eighth to twelfth) |
  | The `spice` job's steps on Linux, ngspice-36, at `e938cc8` | an ubuntu:22.04 arm64 container, a clean clone: apt `ngspice git` (ngspice 36), Python 3.12.14 (uv's standalone build, where CI uses actions/setup-python), `pip install -r tools/requirements.txt pytest`, then with `ECAD_REQUIRE_SPICE_TOOLS=1` the job's `run_all_tests.py --tb=short`, `check` and `validate` | `PASS` -- 359 passed, 51 skipped (the tests of `test_cad_dataset.py`: the job installs no CAD kernel), 0 failed; `check` exit 0; `validate` exit 0: V0-V3 `PASS`, V4 `BLOCKED` with REQ-EL-001..004 and 008 `WARNING` and REQ-EL-005..007 `BLOCKED`, source not dirty |
  | ngspice-44.2, the CI job, Linux x86_64 | a real run | `NOT RUN` for the branch review -- 44.2 last ran at `f6dee36` (above); push access is read-only; the containers are arm64 |
  | Coverage of new and changed code | a coverage tool | `NOT RUN` -- none is installed |
  | The parser test's texts, `49887ac` | after `5917365`: `test_spice_netlist.py`'s NETLIST and DECK compared with the committed files | Found stale: `555bfd7` changed the netlist's comment and the deck's measurements and left the constants, though the file says they are the committed texts. `49887ac` updates them and asserts they equal the files. Then, on clean clones of `49887ac`: the 16 mutants that file kills, `--workers 4` in two batches of 8, each after a green baseline -- 16 of 16 killed, each by the same test as before; the complete suite -- 410 passed, 0 failed, 0 skipped (217 s) |

### T-013 — Digital domain: the UART loopback on Icarus Verilog

Owner: unassigned
Mode: build
Status: review (the fork's `feat/domain-digital`, stacked on PR #38; two independent reviews at `905294f` (`6fbae29` on this branch), whose 12 distinct findings are fixed at `2b2d1d0` to `0a5ff00` (plan §7.7); the fixes have had no review of their own)
Depends on: T-012 (`feat/domain-electrical` at `7368641`, which this branch builds on)

Goal
: Verilog sources become an engineering model whose every value states its
  source and status, Icarus Verilog runs a harness written from that model,
  and the digital domain is validated end to end through the same V0-V4
  runner as mechanical and electrical, on a sample that invents no part,
  device or requirement.

Acceptance criteria (verbatim from `ECAD_MULTI_DOMAIN_DATASET_PLAN.md` §21 item 5)
: "5. **Digital**: `rtl/` UART loopback on Icarus. First, `iverilog` onto `run_process`, with a test and a mutant that both the compile and the run step get the scrubbed environment and the output cap (ARCH-10); `hdl` CI job; `tests/test_rtl_models.py` unchanged."
  1. "`rtl/` UART loopback on Icarus."
  2. "First, `iverilog` onto `run_process`, with a test and a mutant that both the compile and the run step get the scrubbed environment and the output cap (ARCH-10)"
  3. "`hdl` CI job"
  4. "`tests/test_rtl_models.py` unchanged."

Acceptance criteria (verbatim from the plan §10, for every domain)
: 5. "Each domain lands as one PR with: at least one sample; a met limit (`PASS` against a real requirement, `WARNING` against an illustrative one), a `FAIL` from a mutated input and a `BLOCKED` from a missing input; an invalid-input and a boundary sample (spec §21); negative tests and mutants; per-domain documentation (spec §28); and a CI job that makes a skip a failure."

State of each criterion (the plan §21 item 5 carries the same markers)
: 1. IMPLEMENTED for the UART 8N1 loopback class only (rules C1-C7): `datasets/cad/uart_loopback_001` builds, checks and validates as designed (Verification). Every metric is `SIMPLIFIED`.
  2. IMPLEMENTED (ARCH-10): both steps and the version probe run through `run_process`; the tests `test_both_icarus_steps_run_through_run_process_with_the_scrubbed_environment`, `test_both_steps_are_capped_at_the_process_output_limit` and `test_the_compiler_sees_only_the_scrubbed_environment` (real Icarus), and the mutants `hdl-compile-bypasses-run-process`, `hdl-run-bypasses-run-process`, `hdl-compile-inherits-environment` and `hdl-run-inherits-environment`, killed (Verification). `capabilities.detect_capabilities` still probes with the caller's environment (plan §7.2 ARCH-10).
  3. PARTIAL: the `hdl` job is written, placed between `validation-evidence` and `spice`, and its shape is tested (`test_hdl_job_cannot_skip_silently`); it has never run on a runner, and Icarus is not pinned (BLOCKED until the runner's version is known, plan §20 Q16). Its steps passed in an ubuntu:22.04 arm64 container on Icarus 11.0 (Verification, run by the coordinator).
  4. IMPLEMENTED: `tests/test_rtl_models.py` was last changed in `f15a4aa`, and its sha256 at `0a5ff00` is `7a9ced8edde3a4100b67a3cfddfc8096d53f0222b8747087df5e70eb471a2866`, as the design recorded.
  5. Sample IMPLEMENTED. Met limit: `WARNING` against the illustrative limits IMPLEMENTED; `PASS` against a real requirement only on a test-built copy with a fixture device limit, since no device is selected. `FAIL` from a mutated input IMPLEMENTED (test-built copies, real Icarus: 230 400 Bd fails REQ-DIG-002; RTL defect copies fail their references). `BLOCKED` from a missing input IMPLEMENTED (REQ-DIG-007: no target device is selected, so its `min_clock_period` is `UNKNOWN`). Invalid-input and boundary samples PARTIAL: test-built copies, not committed items. Negative tests IMPLEMENTED; mutants IMPLEMENTED: 451 at `0a5ff00`, the 129 of the digital branch killed at `11e8c09` and the re-anchored `electrical-unregistered` at `0a5ff00`, each after a green baseline; the other 321 last run at `ec37115` or `57f4fee` (Verification). Documentation IMPLEMENTED (`docs/digital-domain-v1.md`). CI job PARTIAL, as in 3.

Files in scope
: `tools/ecad_model/verilog.py`, `tools/ecad_model/domains/digital.py`,
  `tools/ecad_model/domains/__init__.py`, `tools/ecad_model/__init__.py`,
  `tools/ecad_model/dataset.py` (REUSE-1, `VALIDATOR_VERSION`),
  `tools/ecad_validation/adapters/hdl.py`,
  `tools/ecad_validation/adapters/process.py`, `schemas/engineering-model/v1/`
  (engineering-model, design-annotations, digital-vocabulary),
  `schemas/cad-dataset/v1/source-provenance.schema.json`,
  `datasets/cad/uart_loopback_001/`, the regenerated `dataset-item.json` of
  `robotic_joint_001` and `servo_supply_001`, `.gitattributes`,
  `tests/unit/test_verilog_source.py`, `tests/unit/test_hdl_adapter.py`,
  `tests/unit/test_digital_domain.py`, `tests/unit/test_digital_icarus.py`,
  the edited `test_ci_and_runner.py`, `test_domain_adapter.py`,
  `test_electrical_domain.py`, `test_engineering_model.py` and
  `test_validation_adapters.py`, `tests/mutation/run_mutations.py`, the `hdl`
  job in `.github/workflows/ci.yml`, documentation, the plan.

Out of scope
: Other design classes and RTL forms (negedge, asynchronous reset, `assign`,
  `generate`, `$clog2`, SystemVerilog, VHDL); FSM extraction and timing
  analysis; a Verilator adapter and ModelSim/Questa (PLANNED); the SEC-2
  runner guard (its own foundation change, plan §7.2) and the SEC-3 program
  screen; the general RESULT-2 fix; `detect_capabilities`' probe; moving
  `datasets/cad/` (the brief kept the layout, plan §20 Q8); training
  records.

Risks
: The CI runner's Icarus is Unknown until the `hdl` job runs: apt gave 11.0
  in an arm64 container, every local run used 13.0, and nothing ran on
  x86_64. Only marker lines are read, and 11.0 and 13.0 printed the same ones
  for the sample and five copies, but their stdout differs in 13.0's
  `$finish called at` line. A hand-edited committed simulation file runs
  during `validate` before it is marked stale (SEC-2, Verification). The
  sampling condition W is conservative, so a borderline design gets
  `REFERENCE_NOT_APPLICABLE`; framing-error detection is never exercised by
  the committed sample. The regression test of REUSE-1's letter-case alias,
  and so its mutant's kill, exists only on a case-insensitive filesystem. The
  mutation harness now needs Icarus, ngspice, the CAD kernel and MuJoCo on
  one machine. Push access is read-only for this account.

Verification (2026-09-29, macOS 26.6.2 arm64, Python 3.14.4, Icarus Verilog 13.0, ngspice-47; code at `0a5ff00`, which the documentation commit changes only in Markdown and in comments of `tools/requirements.txt`; `git diff 11e8c09 0a5ff00` is exactly the electrical design-document commit `7368641`)
: | Check | Command | Result |
  |-------|---------|--------|
  | Complete suite, CAD, ngspice and Icarus tests mandatory | `ECAD_REQUIRE_CAD_TOOLS=1 ECAD_REQUIRE_SPICE_TOOLS=1 ECAD_REQUIRE_HDL_TOOLS=1 python3 run_all_tests.py -q -p no:cacheprovider --tb=short`, at the documentation commit | `PASS` -- 489 passed, 0 failed, 0 skipped, 8 warnings, exit 0 (259 s), on the tree this commit records; at `0a5ff00`, before the documentation, the same 489 (262 s). The 77 digital tests (14 grammar, 18 hdl adapter, 35 domain, 10 real Icarus) are among them |
  | Lint, changed Python | `ruff check <the 17 Python files changed since 7368641> --select=E,F,W --ignore=E501 --no-cache` | `PASS` -- "All checks passed!" |
  | Type check | `mypy tools run_all_tests.py tests/mutation/run_mutations.py --ignore-missing-imports --no-strict-optional` | `PASS` for changed code -- "Found 11 errors in 7 files (checked 46 source files)", the baseline set (discovery 2, contract 1, python_control 1, cases 4, engine 1, cli 1, validate_products 1), none in a file this branch changed |
  | Derivation reproduces, clean clone | `python3 tools/cad_dataset.py build datasets/cad/uart_loopback_001`, then `git status --short`, then `check` of all three samples | `PASS` -- `build` exit 0, five files written, 0 lines of `git status`; `check` exit 0 for `uart_loopback_001`, `robotic_joint_001` and `servo_supply_001` |
  | V0-V4 receipt, clean clone | `python3 tools/cad_dataset.py validate datasets/cad/uart_loopback_001 --output <dir>` | `PASS` as designed -- exit 0; V0-V3 `PASS` (REF-DIG-001..008); V4 `BLOCKED`: REQ-DIG-001..006 `WARNING WITHIN_ILLUSTRATIVE_LIMIT`, REQ-DIG-007 `BLOCKED MISSING_REQUIRED_INPUT` (2e-08 s measured by `v3.REF-DIG-001`); overall `BLOCKED`, not eligible; 15 results, each `SIMPLIFIED`, bound to the receipt's digest; 86 evidence entries (45 digests) re-hash; source `0a5ff00` not dirty; `ecad-validator` 1.1.0, `Icarus Verilog version 13.0 (stable) (v13_0)`. The same in the worktree at `0a5ff00` |
  | SEC-2 on the digital path | a scratch clone of `0a5ff00` with a `$fopen(<file outside the item>, "a")` added to the committed simulation file's harness, then `validate` | Verified, the defect stands -- the file was written 14 times, once per compiled case; then V0 `FAIL`, `v2.dataset-reproduction` `FAIL DERIVATION_DIVERGED`, `v2.digital.model-invariants` `PASS`, the 14 cases `BLOCKED COMMITTED_CASE_STALE`, overall `FAIL`; `check` exit 1 |
  | Test discrimination, the digital branch | `python3 tests/mutation/run_mutations.py --workers 4 --only <batch>`, 23 batches covering the 129 mutants `38680e0` did not have, on the code of `11e8c09` | `PASS` -- 129 of 129 killed, none surviving, no `ANCHOR` or `HARNESS` outcome, each batch after its own green baseline (23 green baselines). First killers by file: 57 `test_digital_domain.py`, 29 `test_hdl_adapter.py`, 27 `test_verilog_source.py`, 14 `test_engineering_model.py` (the modules' doctests), 1 `test_domain_adapter.py`, 1 `test_ngspice_adapter.py`. Five batches took longer than 8 minutes (up to 647 s). This is the review's fixer's run of 2026-09-29, not this session's; the code at `0a5ff00` equals `11e8c09`'s apart from the electrical design-document commit underneath |
  | Test discrimination, the re-anchored mutant | `python3 tests/mutation/run_mutations.py --workers 1 --only electrical-unregistered` on a clean clone of `0a5ff00` | `PASS` -- "baseline green; running 1 mutants", killed by `test_engineering_model.py::TestDocumentationExamples::test_examples_in_modules_that_need_no_cad_kernel [domains]`, "1 of 1 mutants killed", exit 0 (3 min 57 s). It is the only one of the 322 older mutants whose definition the digital branch changed |
  | Test discrimination, the other 321 | `run_mutations.py` | `NOT RUN` here -- last run at `ec37115` or `57f4fee` (T-012) |
  | The `hdl` job's steps on Linux, Icarus 11.0 | an ubuntu:22.04 arm64 container, a clean copy of `11e8c09`: apt `iverilog` (`Icarus Verilog version 11.0 (stable) ()`), Python 3.12.14 (uv's standalone build, where CI uses actions/setup-python), `pip install -r tools/requirements.txt pytest`, then with `ECAD_REQUIRE_HDL_TOOLS=1` the job's `run_all_tests.py --tb=short`, `check` and `validate` | `PASS` -- 428 passed, 61 skipped (the CAD and ngspice tests the job does not install for), 0 failed; `check` exit 0; `validate` exit 0: V0-V3 `PASS`, V4 `BLOCKED` (6 `WARNING`, REQ-DIG-007 `BLOCKED`), source not dirty. Run by the coordinator of the digital branch, not by this session |
  | The `spice` and `hdl` jobs' steps on Linux at `0a5ff00` (this branch rebased onto PR #38's head) | the same ubuntu:22.04 arm64 containers, run by the coordinator: apt ngspice-36 for `spice`, apt Icarus 11.0 for `hdl`, Python 3.12.14, `ECAD_REQUIRE_SPICE_TOOLS=1` or `ECAD_REQUIRE_HDL_TOOLS=1`, the complete suite, `check` and `validate` of the job's sample | `PASS` -- each 428 passed, 61 skipped (the other tools' and the CAD tests), 0 failed; `check` exit 0; `validate`: `servo_supply_001` V0-V3 `PASS`, V4 `BLOCKED` (5 `WARNING`, 3 `BLOCKED`), `uart_loopback_001` V0-V3 `PASS`, V4 `BLOCKED` (6 `WARNING`, REQ-DIG-007 `BLOCKED`) |
  | The `cad-dataset` job's steps on Linux at `0a5ff00` | a python:3.12-slim (Debian 13) arm64 container, run by the coordinator: apt `git libgl1`, `pip install -r tools/requirements.txt -r tools/requirements-cad.txt -c tools/constraints-cad.txt pytest` (cadquery-ocp 8.0.1, mujoco 3.14.0, numpy 2.5.3), `ECAD_REQUIRE_CAD_TOOLS=1`, `check`, the complete suite, `validate datasets/cad/robotic_joint_001` | `PASS` -- `check` exit 0; 469 passed, 20 skipped (the ngspice and Icarus tests), 0 failed; `validate` V0-V3 `PASS`, V4 `BLOCKED` (5 `WARNING`, REQ-XD-001 `BLOCKED`) |
  | Independent review | CLAUDE.md rule 4: two reviewers, correctness and security (CS) and honesty and tests (HT), at `905294f` | `PASS` -- 12 distinct findings (14 IDs, two found by both), all fixed (plan §7.7). The fixes themselves have had no review of their own |
  | CI `hdl` job, Linux x86_64 | the job itself | `NOT RUN` -- push access is read-only, and the fork's workflows wait for a maintainer's approval (`action_required` on #36-#38); the container above is arm64 |
  | Verilator | a run of the harness under Verilator | `NOT RUN` -- Verilator is PLANNED, not an adapter (plan §20 Q9) |
  | Coverage of new and changed code | a coverage tool | `NOT RUN` -- none is installed (no `coverage`, no `pytest-cov`) |

## Completed

| ID | Task | Owner | Verified by | Evidence |
|----|------|-------|-------------|----------|
| T-001 | Product data validation engine, generator, component library, taxonomy manifest, and 67 products | — | `validate_products.py --run` · `generate_products.py --check` · `unittest discover` | `132/132 targets passed`, `0 file(s) stale`, `Ran 76 tests ... OK` (2026-08-08) |
| T-007 | CAD generation and tool-backed CAD validation for every catalog-managed product | — | `validate_products.py --run --render` | `132/132 targets passed`; 67 enclosures rendered by OpenSCAD 2021.01, 67 boards parsed by kiutils, 67 outlines parsed by ezdxf (2026-08-08) |
| T-011 | Stop a hardware factory-test CLI from failing pytest collection | testing | reviewer | `eRadar360_CAD_Design/simulation/factory_test/eradar360_factory_test.py` matches `test_*.py`, but its eleven `test_*(demo: bool)` functions take a mode flag rather than fixtures, so pytest collected them and failed each with `fixture 'demo' not found` — 10 errors per run. Added `pytest.ini` with `testpaths = tests`. The script still runs directly: `--demo` completes with `Verdict: PASS — SHIP`. Result: 85 passed, 1741 subtests, 0 errors. |

---

## Task template

```markdown
### T-000 — <short title>

Owner: <role>
Mode: <see MODES.md>
Status: todo
Depends on: <task ids, or none>

Goal
: <one sentence: what is true afterwards that is not true now>

Acceptance criteria
: - <observable, checkable statement>
  - <observable, checkable statement>

Files in scope
: <paths the owner is expected to touch>

Out of scope
: <what this task deliberately does not change>

Risks
: <what could break, and what would reveal it>

Verification
: | Check | Command | Result |
  |-------|---------|--------|
  | <name> | `<command>` | `NOT RUN` |
```

## Verification commands for this repository

No verification command was detected at the repository root. Establish the build and test commands before reporting any check as `PASS`; until then every check is `UNKNOWN`.

## Rules

- One task per unit of work that can be verified on its own.
- Acceptance criteria are written before work starts and are not edited to match
  what was built. If they were wrong, say so and rewrite them explicitly.
- A task reaches `done` only when the definition of done in
  [ORCHESTRATION.md](./ORCHESTRATION.md) is met and the verification commands
  were actually run.
- `blocked` requires a note naming what it is blocked on and who can unblock it.
