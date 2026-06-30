from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from nexa_engine.db.exceptions import DbConcurrencyError
from nexa_engine.db.models.atomic_write import AtomicWritePrecondition, AtomicWriteResult
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.gn.api import router as gn_router_module
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import (
    GNVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_repository import GNRepository
from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.hr.api import router as hr_router_module
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import (
    HRVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_repository import HRRepository
from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.op.api import router as op_router_module
from nexa_engine.modules.parametrizacion.op.mappers.op_version_document_codec import (
    OPVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.op.repositories.collections import (
    OP_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_repository import OPRepository
from nexa_engine.modules.parametrizacion.op.services.op_service import OPService
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.shared.repositories.version_payload_persistence import (
    save_version_payload_and_index,
)
from nexa_engine.modules.parametrizacion.shared.models.version_summary import (
    VersionSummary,
)

from .conftest import read_json


class AtomicJsonStore(JsonDocumentStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.atomic_batches: list[tuple[str, list[StoredDocument]]] = []
        self.upsert_record_calls = 0
        self.fail_next_atomic_batch = False
        self._etags: dict[tuple[str, str], str] = {}
        self._etag_counter = 0

    def _next_etag(self) -> str:
        self._etag_counter += 1
        return f"etag-{self._etag_counter}"

    def get_record(self, collection, document_id, *, partition_value=None):  # type: ignore[no-untyped-def]
        record = super().get_record(
            collection,
            document_id,
            partition_value=partition_value,
        )
        if record is None:
            return None
        return StoredDocument(
            id=record.id,
            payload=record.payload,
            partition_value=record.partition_value,
            etag=self._etags.get((collection.name, document_id)),
        )

    def upsert_record(self, collection, record):  # type: ignore[no-untyped-def]
        self.upsert_record_calls += 1
        stored = super().upsert_record(collection, record)
        etag = self._next_etag()
        self._etags[(collection.name, record.id)] = etag
        return StoredDocument(
            id=stored.id,
            payload=stored.payload,
            partition_value=stored.partition_value,
            etag=etag,
        )

    def upsert_records_atomic(
        self,
        collection,
        records: list[StoredDocument],
        *,
        partition_value: str | None = None,
        precondition=None,
    ) -> AtomicWriteResult:
        self.atomic_batches.append((collection.name, list(records)))
        if self.fail_next_atomic_batch:
            self.fail_next_atomic_batch = False
            raise RuntimeError("fallo batch atómico")
        if precondition is not None:
            current_etag = self._etags.get((collection.name, precondition.logical_id))
            if current_etag != precondition.expected_etag:
                raise DbConcurrencyError("fallo de concurrencia")
        stored = tuple(
            JsonDocumentStore.upsert_record(self, collection, record)
            for record in records
        )
        stored_with_etags = []
        for record in stored:
            etag = self._next_etag()
            self._etags[(collection.name, record.id)] = etag
            stored_with_etags.append(
                StoredDocument(
                    id=record.id,
                    payload=record.payload,
                    partition_value=record.partition_value,
                    etag=etag,
                )
            )
        return AtomicWriteResult(records=tuple(stored_with_etags))


class FailingVersionIndexRepository:
    def build_append_record(self, summary: VersionSummary) -> StoredDocument:
        summary.is_active = True
        return StoredDocument(id="versions", payload=[summary.to_dict()])

    def save_record(self, record: StoredDocument) -> None:
        raise RuntimeError("fallo de índice")


def _gn_payload(version_id: str, marcador: str) -> dict[str, Any]:
    return {
        "version_id": version_id,
        "lv": {"name": marcador},
        "sheets": [],
    }


def _hr_payload(version_id: str, marcador: str) -> dict[str, Any]:
    return {
        "version_id": version_id,
        "niveles": {"catalogs": {"rol": [{"name": marcador}]}},
        "salarios": [],
        "nomina": [],
        "recargos": [],
        "seg_social": [],
        "prestaciones": [],
        "ratios": [],
        "rentabilidad": [],
        "campana": [],
        "costo_fijo": [],
        "med_seg": [],
        "extra_sheets": {},
    }


def _op_payload(version_id: str, marcador: str) -> dict[str, Any]:
    return {
        "version_id": version_id,
        "sheets": [
            {
                "name": "OP-LV",
                "key": "lv",
                "catalogs": {"servicio": [{"name": marcador}]},
            }
        ],
    }


UPLOAD_DOMAINS = [
    pytest.param(
        {
            "domain": "gn",
            "repository_cls": GNRepository,
            "service_cls": GNService,
            "router_module": gn_router_module,
            "collection": GN_PARAMETRIZATION_COLLECTION,
            "codec_cls": GNVersionDocumentCodec,
            "payload_factory": _gn_payload,
            "container_service": "gn_upload_service",
        },
        id="gn",
    ),
    pytest.param(
        {
            "domain": "hr",
            "repository_cls": HRRepository,
            "service_cls": HRService,
            "router_module": hr_router_module,
            "collection": HR_PARAMETRIZATION_COLLECTION,
            "codec_cls": HRVersionDocumentCodec,
            "payload_factory": _hr_payload,
            "container_service": "hr_upload_service",
        },
        id="hr",
    ),
    pytest.param(
        {
            "domain": "op",
            "repository_cls": OPRepository,
            "service_cls": OPService,
            "router_module": op_router_module,
            "collection": OP_PARAMETRIZATION_COLLECTION,
            "codec_cls": OPVersionDocumentCodec,
            "payload_factory": _op_payload,
            "container_service": "op_upload_service",
        },
        id="op",
    ),
]


def _summary(domain: str, version_id: str) -> VersionSummary:
    return VersionSummary(
        version_id=version_id,
        filename=f"{domain.upper()}.xlsx",
        uploaded_at="2026-06-04T00:00:00Z",
        is_active=False,
        sheet_count=1,
        total_rows=1,
    )


def _repository(domain_config: dict[str, Any], tmp_path: Path):
    store = JsonDocumentStore(tmp_path)
    return domain_config["repository_cls"](
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=domain_config["collection"],
        ),
        codec=domain_config["codec_cls"](),
    )


def _repository_with_store(domain_config: dict[str, Any], store):
    return domain_config["repository_cls"](
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=domain_config["collection"],
        ),
        codec=domain_config["codec_cls"](),
    )


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_repository_has_document_store_boundary(domain_config):
    repository_cls = domain_config["repository_cls"]
    signature = inspect.signature(repository_cls.__init__)

    # BaseRepository was deleted in FASE DB.6.5 — repos use DocumentStore directly
    assert "store" in signature.parameters
    assert "version_index_repository" in signature.parameters
    assert "codec" in signature.parameters
    assert signature.parameters["store"].default is inspect.Parameter.empty
    assert signature.parameters["version_index_repository"].default is inspect.Parameter.empty
    assert signature.parameters["codec"].default is inspect.Parameter.empty

    source = inspect.getsource(repository_cls)
    assert "save_version_payload_and_index(" in source
    assert "BaseRepository" not in source
    assert "open(" not in source
    assert "json.dump" not in source
    assert "write_text" not in source

    helper_source = inspect.getsource(save_version_payload_and_index)
    assert "upsert_records_atomic(" in helper_source
    assert "AtomicWritePrecondition(" in helper_source
    assert "upsert_record(" in helper_source
    assert "get_record(" in helper_source


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_service_receives_repository_by_constructor(domain_config):
    service_cls = domain_config["service_cls"]
    signature = inspect.signature(service_cls.__init__)

    assert "repository" in signature.parameters
    assert signature.parameters["repository"].default is inspect.Parameter.empty


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_router_resolves_service_from_container(domain_config):
    router_source = inspect.getsource(domain_config["router_module"])

    assert "Depends(_get_service)" in router_source
    assert f"app.state.container.{domain_config['container_service']}" in router_source
    assert "_service =" not in router_source


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_persistence_preserves_payload_and_legacy_index(domain_config, tmp_path):
    repository = _repository(domain_config, tmp_path)
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    payload = domain_config["payload_factory"](version_id, "base")

    assert repository.save_version(_summary(domain, version_id), payload) == version_id

    payload_path = tmp_path / domain / f"{version_id}.json"
    versions_path = tmp_path / domain / "versions.json"
    assert read_json(payload_path) == payload
    assert "id" not in read_json(payload_path)
    assert read_json(versions_path) == [
        {
            "version_id": version_id,
            "filename": f"{domain.upper()}.xlsx",
            "uploaded_at": "2026-06-04T00:00:00Z",
            "is_active": True,
            "sheet_count": 1,
            "total_rows": 1,
        }
    ]


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_duplicate_version_behavior_is_equivalent(domain_config, tmp_path):
    repository = _repository(domain_config, tmp_path)
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    first_payload = domain_config["payload_factory"](version_id, "primero")
    second_payload = domain_config["payload_factory"](version_id, "segundo")

    repository.save_version(_summary(domain, version_id), first_payload)
    repository.save_version(_summary(domain, version_id), second_payload)

    assert read_json(tmp_path / domain / f"{version_id}.json") == second_payload
    versions = read_json(tmp_path / domain / "versions.json")
    assert [entry["version_id"] for entry in versions] == [version_id, version_id]
    assert [entry["is_active"] for entry in versions] == [False, True]


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_compensation_removes_new_payload_when_index_fails(domain_config, tmp_path):
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    repository = domain_config["repository_cls"](
        store=JsonDocumentStore(tmp_path),
        version_index_repository=FailingVersionIndexRepository(),
        codec=domain_config["codec_cls"](),
    )

    with pytest.raises(RuntimeError, match="fallo de índice"):
        repository.save_version(
            _summary(domain, version_id),
            domain_config["payload_factory"](version_id, "nuevo"),
        )

    assert not (tmp_path / domain / f"{version_id}.json").exists()
    assert not (tmp_path / domain / "versions.json").exists()


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_compensation_restores_previous_payload_when_index_fails(domain_config, tmp_path):
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    previous_payload = domain_config["payload_factory"](version_id, "previo")
    store = JsonDocumentStore(tmp_path)
    store.upsert_record(
        domain_config["collection"],
        StoredDocument(id=version_id, payload=previous_payload),
    )
    repository = domain_config["repository_cls"](
        store=store,
        version_index_repository=FailingVersionIndexRepository(),
        codec=domain_config["codec_cls"](),
    )

    with pytest.raises(RuntimeError, match="fallo de índice"):
        repository.save_version(
            _summary(domain, version_id),
            domain_config["payload_factory"](version_id, "nuevo"),
        )

    assert read_json(tmp_path / domain / f"{version_id}.json") == previous_payload


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_uses_single_atomic_batch_when_store_supports_it(domain_config, tmp_path):
    store = AtomicJsonStore(tmp_path)
    repository = _repository_with_store(domain_config, store)
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    payload = domain_config["payload_factory"](version_id, "base")

    repository.save_version(_summary(domain, version_id), payload)

    assert store.upsert_record_calls == 0
    assert len(store.atomic_batches) == 1
    batch_collection, batch_records = store.atomic_batches[0]
    assert batch_collection == domain
    assert [record.id for record in batch_records] == [version_id, "versions"]
    assert batch_records[0].payload == payload
    assert "id" not in batch_records[0].payload
    assert isinstance(batch_records[1].payload, list)
    assert [entry["version_id"] for entry in batch_records[1].payload] == [version_id]
    assert read_json(tmp_path / domain / f"{version_id}.json") == payload


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_atomic_batch_failure_leaves_no_partial_changes(domain_config, tmp_path):
    store = AtomicJsonStore(tmp_path)
    store.fail_next_atomic_batch = True
    repository = _repository_with_store(domain_config, store)
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"

    with pytest.raises(RuntimeError, match="fallo batch atómico"):
        repository.save_version(
            _summary(domain, version_id),
            domain_config["payload_factory"](version_id, "nuevo"),
        )

    assert store.upsert_record_calls == 0
    assert len(store.atomic_batches) == 1
    assert not (tmp_path / domain / f"{version_id}.json").exists()
    assert not (tmp_path / domain / "versions.json").exists()


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_atomic_duplicate_version_preserves_legacy_index_order(domain_config, tmp_path):
    store = AtomicJsonStore(tmp_path)
    repository = _repository_with_store(domain_config, store)
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    first_payload = domain_config["payload_factory"](version_id, "primero")
    second_payload = domain_config["payload_factory"](version_id, "segundo")

    repository.save_version(_summary(domain, version_id), first_payload)
    repository.save_version(_summary(domain, version_id), second_payload)

    assert store.upsert_record_calls == 0
    assert len(store.atomic_batches) == 2
    assert read_json(tmp_path / domain / f"{version_id}.json") == second_payload
    versions = read_json(tmp_path / domain / "versions.json")
    assert [entry["version_id"] for entry in versions] == [version_id, version_id]
    assert [entry["is_active"] for entry in versions] == [False, True]


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_atomic_concurrent_stale_index_is_rejected_without_lost_update(domain_config, tmp_path):
    store = AtomicJsonStore(tmp_path)
    repository = _repository_with_store(domain_config, store)
    domain = domain_config["domain"]
    first_version_id = f"{domain}-v1"
    second_version_id = f"{domain}-v2"
    third_version_id = f"{domain}-v3"

    repository.save_version(
        _summary(domain, first_version_id),
        domain_config["payload_factory"](first_version_id, "primero"),
    )
    stale_versions = store.get_record(domain_config["collection"], "versions")
    repository.save_version(
        _summary(domain, second_version_id),
        domain_config["payload_factory"](second_version_id, "segundo"),
    )

    stale_payload = domain_config["payload_factory"](third_version_id, "tercero")
    stale_index_payload = [
        {"version_id": first_version_id, "is_active": False},
        {"version_id": third_version_id, "is_active": True},
    ]

    with pytest.raises(DbConcurrencyError):
        store.upsert_records_atomic(
            domain_config["collection"],
            [
                StoredDocument(id=third_version_id, payload=stale_payload),
                StoredDocument(
                    id="versions",
                    payload=stale_index_payload,
                    etag=stale_versions.etag,
                ),
            ],
            precondition=AtomicWritePrecondition(
                logical_id="versions",
                expected_etag=stale_versions.etag,
            ),
        )

    assert not (tmp_path / domain / f"{third_version_id}.json").exists()
    versions = read_json(tmp_path / domain / "versions.json")
    assert [entry["version_id"] for entry in versions] == [first_version_id, second_version_id]
    assert [entry["is_active"] for entry in versions] == [False, True]
