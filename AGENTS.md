# Repository Guidance for Agents

## Scope and architecture

eCAD-Hardware-Products is a collection of hardware and PCB designs organized by
application domain. Each `*_CAD_Design/` directory is an independent design
surface with its own maturity. Typical product lines contain datasheets, CSV
bills of materials, Python power-budget simulations, and `hardware/pcb/`,
`hardware/cad/`, or `hardware/antenna/` artifacts. Some designs contain KiCad
schematics and layouts; many artifact directories are intentionally placeholders.

Read the affected domain README, product datasheet, and design notes before
editing. Do not propagate a part, net, unit, power assumption, or maturity claim
across product lines unless the checked-in sources establish that relationship.
Follow the specialist role briefs in [`.ai/`](./.ai/) and the handoff protocol in
[`HANDOFF.md`](./HANDOFF.md). The implementer must not act as the approving
reviewer.

## Validation

Use checks that match the changed artifact and report unavailable hardware or CAD
tooling explicitly.

- For repository Python tests, run `python run_all_tests.py`; it invokes the
  checked-in pytest suites under `tests/`.
- For a power-budget change, run the affected product's
  `simulation/power_budget_sim.py` as documented in [`README.md`](./README.md)
  and compare its output with the datasheet and BOM assumptions.
- For BOM changes, verify identifiers, quantities, units, sourcing fields, and
  references against the affected schematic, layout, datasheet, and power model.
- For KiCad or mechanical CAD changes, review the native artifact with the
  appropriate installed tool and record any checks that could not be performed.
- Documentation-only governance changes do not prove a hardware design, build,
  simulation, fabrication package, or compliance claim.

The root CMake commands in [`CONTRIBUTING.md`](./CONTRIBUTING.md) do not map
to a root `CMakeLists.txt` in the current tree. Do not report those commands as
a successful repository build unless the missing build definition is reconciled.

## Hardware change discipline

Keep changes inside the affected domain and product line. Preserve units,
reference designators, net names, layer-stack assumptions, and BOM-to-design
traceability. Do not commit generated fabrication output, vendor libraries,
large exports, credentials, or proprietary source material unless the repository
already tracks that exact artifact and the change requires it.

Treat design, prototype, pre-production, certification, safety, medical,
defense, and regulatory statements as evidence-backed status claims. Never
upgrade a maturity or compliance claim based only on a document edit or
simulation result.

Every human-authored pull request must use a GitHub-recognized closing keyword
for an issue in this repository, for example `Fixes #123`. Cross-repository
issues and plain issue mentions do not satisfy the linked-issue policy. Follow
[`.github/PULL_REQUEST_TEMPLATE.md`](./.github/PULL_REQUEST_TEMPLATE.md), and
keep the published Wiki snapshot in [`docs/wiki/`](./docs/wiki/) synchronized
when Wiki content changes.
