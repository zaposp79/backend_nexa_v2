from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.gn.repositories import (
    gn_active_parametrization_repository as gn_module,
)
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_active_parametrization_repository import (
    GNActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.hr.repositories import (
    hr_active_parametrization_repository as hr_module,
)
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
    HRActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.op.repositories import (
    op_active_parametrization_repository as op_module,
)
from nexa_engine.modules.parametrizacion.op.repositories.collections import (
    OP_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
    OPActiveParametrizationRepository,
)


class RecordOnlyJsonDocumentStore(JsonDocumentStore):
    def get(self, *args: Any, **kwargs: Any) -> dict | None:
        raise AssertionError("active parametrization must use get_record()")


ACTIVE_DOMAINS = [
    pytest.param(
        "gn",
        GN_PARAMETRIZATION_COLLECTION,
        GNActiveParametrizationRepository,
        gn_module,
        "GN_DIR",
        id="gn",
    ),
    pytest.param(
        "hr",
        HR_PARAMETRIZATION_COLLECTION,
        HRActiveParametrizationRepository,
        hr_module,
        "HR_DIR",
        id="hr",
    ),
    pytest.param(
        "op",
        OP_PARAMETRIZATION_COLLECTION,
        OPActiveParametrizationRepository,
        op_module,
        "OP_DIR",
        id="op",
    ),
]


def _write_versions(
    store: JsonDocumentStore,
    collection: CollectionConfig,
    *,
    version_id: str = "v-active",
    path: str | None = None,
) -> None:
    entry = {
        "version_id": version_id,
        "filename": f"{collection.name}.xlsx",
        "uploaded_at": "2026-06-05T00:00:00Z",
        "is_active": True,
        "sheet_count": 1,
        "total_rows": 1,
    }
    if path is not None:
        entry["path"] = path
    store.upsert_record(collection, StoredDocument(id="versions", payload=[entry]))


@pytest.mark.parametrize(
    ("domain", "collection", "repository_cls", "module", "dir_name"),
    ACTIVE_DOMAINS,
)
def test_active_read_uses_get_record_before_legacy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    domain: str,
    collection: CollectionConfig,
    repository_cls: type,
    module: ModuleType,
    dir_name: str,
) -> None:
    store = RecordOnlyJsonDocumentStore(tmp_path)
    payload = {"version_id": "v-active", "domain": domain, "source": "record"}
    _write_versions(store, collection, path="legacy.json")
    store.upsert_record(collection, StoredDocument(id="v-active", payload=payload))
    monkeypatch.setattr(
        module,
        "read_json",
        lambda path: pytest.fail(f"legacy read_json should not be called: {path}"),
    )

    assert repository_cls(store).get_active_data() == payload


@pytest.mark.parametrize(
    ("domain", "collection", "repository_cls", "module", "dir_name"),
    ACTIVE_DOMAINS,
)
def test_active_read_falls_back_to_legacy_path_when_record_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    domain: str,
    collection: CollectionConfig,
    repository_cls: type,
    module: ModuleType,
    dir_name: str,
) -> None:
    domain_dir = tmp_path / domain
    domain_dir.mkdir()
    legacy_payload = {"version_id": "v-active", "domain": domain, "source": "legacy"}
    (domain_dir / "legacy.json").write_text(json.dumps(legacy_payload), encoding="utf-8")
    store = RecordOnlyJsonDocumentStore(tmp_path)
    _write_versions(store, collection, path="legacy.json")
    monkeypatch.setattr(module, dir_name, domain_dir)

    assert repository_cls(store).get_active_data() == legacy_payload


@pytest.mark.parametrize(
    "repository_cls",
    [
        GNActiveParametrizationRepository,
        HRActiveParametrizationRepository,
        OPActiveParametrizationRepository,
    ],
)
def test_active_repositories_use_get_record_as_primary_route(repository_cls: type) -> None:
    source = inspect.getsource(repository_cls.get_active_data)

    assert "get_record(" in source
    assert "self._store.get(" not in source
    if "read_json(" in source:
        assert source.index("get_record(") < source.index("read_json(")
