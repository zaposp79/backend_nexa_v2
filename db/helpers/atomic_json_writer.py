"""Atomic JSON writes for the JSON document store.

Mirrors the established pattern in
``modules/shared/infrastructure/storage/json_store.py`` (write to a sibling
temp file, then ``os.replace`` for an atomic swap) but raises persistence-layer
exceptions instead of ``StorageError`` so the provider stays self-contained.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from nexa_engine.db.exceptions import DbSerializationError


def write_json_atomic(path: Path, data: Any) -> None:
    """Serialize ``data`` to ``path`` atomically.

    The payload is fully serialized into a temp file in the destination
    directory first; only on success is it ``os.replace``-d over the target so
    readers never observe a partially written file.

    Raises:
        DbSerializationError: ``data`` is not JSON-serializable or the write
            fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception:
            os.unlink(tmp_path)
            raise
        os.replace(tmp_path, path)
    except (TypeError, ValueError) as exc:
        raise DbSerializationError(f"Cannot serialize document to {path}: {exc}") from exc
    except OSError as exc:
        raise DbSerializationError(f"Cannot write document to {path}: {exc}") from exc


def read_json(path: Path) -> Any:
    """Read and parse JSON from ``path``.

    Raises:
        DbSerializationError: the file exists but cannot be parsed.
    """
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise DbSerializationError(f"Corrupt JSON at {path}: {exc}") from exc


__all__ = ["write_json_atomic", "read_json"]
