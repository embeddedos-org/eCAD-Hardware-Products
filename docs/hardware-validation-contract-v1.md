# Hardware validation contract v1

The eCAD v1 contract records what was checked, against which exact inputs, by
which tools, and with what evidence. It is a reporting contract, not a claim
that a product was fabricated, is safe, is production-ready, or satisfies a
regulatory regime.

The schemas are in `schemas/hardware-validation/v1/`. Every instance sets
`contract_version` to `1.0.0` and uses its schema's canonical
`https://embeddedos.org/schemas/hardware-validation/v1/` identifier. A new
incompatible field or meaning requires a new versioned directory and schema
identifier.

## Documents

| Document | Purpose |
|---|---|
| `product-contract.schema.json` | Identifies a product, its V0-V4 scope, applicable domains and layers, requirement catalog, and historical blocking findings. |
| `requirements.schema.json` | Defines normative requirements, acceptance criteria, and required evidence. |
| `product-manifest.schema.json` | Inventories every input used for a product run with repository-relative paths, SHA-256 hashes, sizes, media types, and provenance. |
| `validation-cases.schema.json` | Defines executable V3 golden and V4 corner cases, adapters, inputs, requirements, metrics, tolerances, limits, seeds, and timeouts. |
| `validation-receipt.schema.json` | Records tools, settings, execution status, verdicts, reason codes, metrics, and evidence for every gate. |
| `evidence-index.schema.json` | Binds receipt evidence identifiers to immutable artifacts and their provenance. |
| `bundle.schema.json` | Hash-binds the five product documents above for transport to downstream consumers such as ebuild. |
| `repository-bundle.schema.json` | Indexes every product receipt plus the repository summary and shared evidence index for one inventory revision. |

`common.schema.json` contains shared closed definitions. Producers must reject
unknown fields rather than silently discarding them. A repository run also
emits `summary.json`, `summary.md`, `junit.xml`, and per-product Markdown and
HTML reports. These presentation files do not override the signed-off verdicts
or hash-bound contract documents.

## Validation model

Every product receipt contains exactly one result for each gate:

| Gate | Meaning |
|---|---|
| `V0` | Schema: required files and fields parse and conform to their declared formats. |
| `V1` | Sanity: local values, units, identifiers, geometry, and basic tool-readable structure are plausible. |
| `V2` | Invariants: relationships across BOM, schematic, layout, model, and configuration agree. |
| `V3` | Golden: measured outputs match checked-in expected results within declared tolerances. |
| `V4` | Corner: declared boundary, adverse, and failure cases were executed and satisfied. |

Checks are classified into exactly one of six domains:
`eda_circuit`, `physical_design`, `system_design`, `device_modeling`,
`data_management`, or `integrated_physics`. They also identify one of four
layers: `design`, `model`, `simulation`, or `validation`.

A receipt's `execution_complete` answers whether every check actually ran;
`skipped` and `unavailable` make it false. `eligible_for_ebuild` answers whether
every required gate passed. These are deliberately separate: complete
execution can produce failures, while an incomplete run can never be
release-eligible.

The repository bundle's `all_products_executed` field records inventory and
gate coverage: every inventoried product has a receipt with exact V0-V4 gate
entries. It can be true while a receipt's `execution_complete` is false because
a required tool or input was unavailable. Each repository receipt entry repeats
`execution_complete` and `eligible_for_ebuild` so coverage, actual execution,
and release eligibility remain separately machine-readable.

## Verdicts

| Verdict | Required interpretation |
|---|---|
| `PASS` | The check completed, all acceptance criteria were satisfied, and at least one hash-bound evidence artifact exists. |
| `FAIL` | The check completed, or failed decisively, and established that an acceptance criterion was violated. |
| `WARNING` | An advisory finding was established. It does not satisfy a required check and therefore blocks eligibility when it is the required gate result. |
| `NOT_RUN` | The check was not attempted. This is not success and cannot make a product eligible. |
| `BLOCKED` | A required decision could not be made because an input, tool, dependency, or evidence artifact was missing. An empty evidence list is always `BLOCKED`. |
| `INCONCLUSIVE` | The check ran but its output could not establish pass or fail. This is not success and blocks eligibility. |

Gate and product aggregation is fail-closed. `FAIL` takes precedence, followed
by `BLOCKED` (including a required `WARNING`), `INCONCLUSIVE`, `NOT_RUN`, and
finally `PASS`. A product is eligible only when V0, V1, V2, V3, and V4 are all
`PASS`, execution is complete, and `overall_verdict` is `PASS`.

A historical baseline is an attribution record, not a waiver. A check carrying
`baseline_finding_id` must remain `FAIL` or `BLOCKED`; producers must never use
a baseline entry to turn a non-pass result into `PASS`.

## Evidence and reproducibility

Paths are repository-relative and cannot traverse above the repository or
embed a host-specific absolute path. Every input and evidence artifact records
its lowercase SHA-256, byte size, media type, and provenance. Every invoked tool
records its name, exact version, argument vector, and effective settings; an
executable hash should be included when it can be obtained.

A producer must compute artifact and document-reference hashes from the exact
stored bytes. eCAD-generated JSON is UTF-8 without a byte-order mark, preserves
Unicode characters, rejects NaN and infinity, sorts object keys, uses compact
`,` and `:` separators, and ends the stored document with one LF byte. The
SHA-256 recorded for that JSON file therefore includes the final LF. A digest
of an in-memory JSON value uses the same canonical serialization without the
file-ending LF. Non-JSON artifacts are hashed byte-for-byte without
normalization.

A producer must verify that every receipt evidence reference resolves to
exactly one evidence-index record, that IDs are unique, and that referenced
tool and requirement IDs exist. JSON Schema cannot prove file existence, hash
contents, cross-document identity, or ID uniqueness by a selected object
field, so these are mandatory producer and consumer checks.

If a required input or evidence file is absent, emit `BLOCKED` with a specific
reason code. If a tool was not invoked, emit `NOT_RUN` for an optional check or
`BLOCKED` for a required check. Never synthesize a tool version, metric, hash,
evidence path, execution result, or passing verdict.

## What this proves

A schema-valid bundle proves only that the report has the v1 shape. After a
consumer verifies all hashes and references, it additionally proves that the
reported documents are internally bound to the inspected bytes.

It does not by itself prove that:

- any PCB or enclosure was fabricated or assembled;
- a simulation predicts physical behavior accurately;
- a CAD artifact is manufacturable;
- safety, EMC, environmental, medical, defense, or regulatory requirements are met;
- a vendor part, price, stock level, or certification claim is current;
- a human reviewed or approved the product.

Those claims require their own requirements, qualified tools or facilities,
traceable evidence, and an independently reviewed receipt. Documentation-only
changes never upgrade product maturity or compliance status.
