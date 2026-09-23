"""Generate and validate v1 product contract documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from jsonschema import Draft7Validator, FormatChecker, RefResolver

from .hashing import sha256_file, sha256_json
from .models import ProductRunResult
from .policy import CONTRACT_VERSION, DOMAINS, LAYERS, REQUIRED_GATES

SCHEMA_BASE = "https://embeddedos.org/schemas/hardware-validation/v1/"
POLICY_REQUIREMENT_IDS = [
    "POLICY:V0-SCHEMA",
    "POLICY:V1-SANITY",
    "POLICY:V2-INVARIANTS",
    "POLICY:V3-GOLDEN",
    "POLICY:V4-CORNER",
]


def schema_directory(repository_root: Path) -> Path:
    return repository_root / "schemas" / "hardware-validation" / "v1"


def load_schemas(repository_root: Path) -> Dict[str, Dict[str, Any]]:
    schemas = {}
    for path in sorted(schema_directory(repository_root).glob("*.schema.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if "$id" in document:
            schemas[path.name] = document
    return schemas


def validate_document(repository_root: Path, schema_name: str, document: Dict[str, Any]) -> None:
    schemas = load_schemas(repository_root)
    if schema_name not in schemas:
        raise ValueError(f"contract schema is missing: {schema_name}")
    schema = schemas[schema_name]
    store = {value["$id"]: value for value in schemas.values()}
    validator = Draft7Validator(
        schema,
        resolver=RefResolver.from_schema(schema, store=store),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(item) for item in error.path) or '<root>'}: {error.message}"
            for error in errors[:10]
        )
        raise ValueError(f"{schema_name} validation failed: {detail}")


def media_type(path: Path) -> str:
    return {
        ".csv": "text/csv",
        ".json": "application/json",
        ".md": "text/markdown",
        ".py": "text/x-python",
        ".v": "text/x-verilog",
        ".sv": "text/x-systemverilog",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
    }.get(path.suffix.lower(), "application/octet-stream")


def artifact_role(path: Path) -> str:
    parts = set(path.parts)
    if "simulation" in parts:
        return "simulation"
    if "validation" in parts:
        return "requirement" if "requirements" in path.name else "configuration"
    if path.suffix.lower() in {".v", ".sv", ".py"}:
        return "model"
    if "hardware" in parts or path.name in {"bom.csv", "product_datasheet.md"}:
        return "design"
    return "other"


def artifact_reference(path: str, digest: str, size_bytes: int, kind: str) -> Dict[str, Any]:
    return {
        "path": path,
        "sha256": digest,
        "media_type": kind,
        "size_bytes": size_bytes,
    }


def build_product_manifest(
    repository_root: Path,
    product: ProductRunResult,
    input_files: Iterable[Path],
) -> Dict[str, Any]:
    artifacts = []
    for index, path in enumerate(sorted(input_files)):
        relative = path.relative_to(repository_root).as_posix()
        artifacts.append(
            {
                "artifact_id": f"artifact:{index:05d}",
                "path": relative,
                "sha256": sha256_file(path),
                "media_type": media_type(path),
                "size_bytes": path.stat().st_size,
                "role": artifact_role(path.relative_to(repository_root / product.product_path)),
                "provenance": {
                    "source_type": "repository",
                    "source_path": relative,
                    "source_commit": product.source_commit,
                    "recorded_at": product.started_at,
                },
            }
        )
    digest_entries = [
        {
            "path": Path(artifact["path"])
            .relative_to(Path(product.product_path))
            .as_posix(),
            "sha256": artifact["sha256"],
        }
        for artifact in artifacts
    ]
    manifest_input_sha256 = sha256_json(digest_entries)
    if manifest_input_sha256 != product.input_sha256:
        raise ValueError(
            f"product inputs changed before manifest generation: {product.product_id}"
        )
    return {
        "$schema": SCHEMA_BASE + "product-manifest.schema.json",
        "contract_version": CONTRACT_VERSION,
        "product": {"id": product.product_id, "path": product.product_path},
        "source": {
            "repository": "https://github.com/embeddedos-org/eCAD-Hardware-Products",
            "commit": product.source_commit,
            "dirty": product.source_dirty,
            "input_sha256": product.input_sha256,
        },
        "generated_at": product.completed_at,
        "artifacts": artifacts,
    }


def build_product_contract(
    product: ProductRunResult,
    requirements_reference: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "$schema": SCHEMA_BASE + "product-contract.schema.json",
        "contract_version": CONTRACT_VERSION,
        "contract_id": f"contract:{product.product_id}",
        "product": {
            "id": product.product_id,
            "name": product.product_id.split(":", 1)[-1],
            "path": product.product_path,
        },
        "validation_scope": {
            "gates": list(REQUIRED_GATES),
            "domains": list(DOMAINS),
            "layers": list(LAYERS),
        },
        "requirements": {
            "catalog": requirements_reference,
            "requirement_ids": POLICY_REQUIREMENT_IDS,
        },
        "provenance": {
            "source_type": "repository",
            "source_path": product.product_path,
            "source_commit": product.source_commit,
            "recorded_at": product.completed_at,
        },
    }
