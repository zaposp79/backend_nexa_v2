from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[3]
GN_RUNTIME_FILES = [
    path
    for path in (BACKEND_ROOT / "modules/parametrizacion/gn").rglob("*.py")
    if "__pycache__" not in path.parts
]


def test_gn_runtime_does_not_import_concrete_providers_or_factories():
    forbidden = [
        "RepositoryFactory",
        "get_provider",
        "get_parametrization_store",
        "db.providers",
    ]
    for path in GN_RUNTIME_FILES:
        source = path.read_text(encoding="utf-8")
        assert not any(token in source for token in forbidden), path


def test_gn_repository_does_not_use_direct_filesystem_writes():
    source = (BACKEND_ROOT / "modules/parametrizacion/gn/repositories/gn_repository.py").read_text(
        encoding="utf-8"
    )

    forbidden = [
        "BaseRepository",
        "open(",
        "json.dump",
        "write_text",
    ]
    assert not any(token in source for token in forbidden)
