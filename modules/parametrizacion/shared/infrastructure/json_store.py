"""Atomic JSON file operations for parametrization storage.

Extracted from ``shared/infrastructure/storage/json_store.py`` in
FASE DB.6.5 (2026-06-04) — all parametrization consumers now use this location.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Union

from nexa_engine.modules.shared.exceptions import StorageError


def ensure_dir(path: Union[str, Path]) -> None:
    """Create directory (and parents) if it does not already exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def read_json(path: Union[str, Path]) -> Any:
    """Read and return parsed JSON from *path*.

    Returns an empty list if the file does not exist yet.

    Raises:
        StorageError: if the file exists but cannot be parsed.
    """
    p = Path(path)
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise StorageError(f"Corrupt JSON at {p}: {exc}", str(p)) from exc
    except OSError as exc:
        raise StorageError(f"Cannot read {p}: {exc}", str(p)) from exc


def write_json(path: Union[str, Path], data: Any) -> None:
    """Write *data* as JSON to *path* atomically.

    Writes to a sibling ``.tmp`` file then renames it so readers never see a
    partially-written file.

    Raises:
        StorageError: on any I/O failure.
    """
    p = Path(path)
    ensure_dir(p.parent)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
        except Exception:
            os.unlink(tmp_path)
            raise
        os.replace(tmp_path, p)
    except StorageError:
        raise
    except OSError as exc:
        raise StorageError(f"Cannot write {p}: {exc}", str(p)) from exc
