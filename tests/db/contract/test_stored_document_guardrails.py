from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[3]
CODEC_FILES = [
    BACKEND_ROOT / "modules/parametrizacion/gn/mappers/gn_version_document_codec.py",
    BACKEND_ROOT / "modules/parametrizacion/hr/mappers/hr_version_document_codec.py",
    BACKEND_ROOT / "modules/parametrizacion/op/mappers/op_version_document_codec.py",
    BACKEND_ROOT / "modules/parametrizacion/shared/mappers/version_index_document_codec.py",
]


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_codecs_do_not_import_concrete_providers():
    for path in CODEC_FILES:
        assert not any(".providers." in imported for imported in _imports(path)), path


def test_json_document_store_record_api_does_not_merge_metadata_into_payload():
    source = (BACKEND_ROOT / "db/providers/json_document_store.py").read_text(encoding="utf-8")
    upsert_record_source = source.split("def upsert_record", 1)[1].split("def get(", 1)[0]

    assert "payload[FIELD_ID]" not in upsert_record_source
    assert 'payload["id"]' not in upsert_record_source
    assert "record.partition_value" not in upsert_record_source.split("write_json_atomic", 1)[0]
