"""Canonical hashing helpers for portable validation evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for digest and signature inputs."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path, paths: Iterable[Path]) -> str:
    """Hash relative paths and file contents without embedding host paths."""
    entries = []
    resolved_root = root.resolve()
    candidates = sorted(set(paths), key=lambda candidate: candidate.as_posix())
    for candidate in candidates:
        if candidate.is_symlink():
            raise ValueError(
                f"symbolic links are not valid evidence inputs: {candidate}"
            )
        path = candidate.resolve()
        try:
            relative = path.relative_to(resolved_root).as_posix()
        except ValueError as exc:
            raise ValueError(f"evidence path escapes product root: {path}") from exc
        if path.is_file():
            entries.append({"path": relative, "sha256": sha256_file(path)})
    return sha256_json(entries)
