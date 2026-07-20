from __future__ import annotations

from pathlib import Path

from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import (
    GNVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_repository import GNRepository
from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary

from .conftest import read_json
from .test_gn_upload_characterization import _gn_workbook


class SpyCodec(GNVersionDocumentCodec):
    def __init__(self) -> None:
        self.encoded_payloads: list[dict] = []

    def encode(self, payload: dict, doc_id: str | None = None, root_metadata: dict | None = None) -> StoredDocument:
        self.encoded_payloads.append(payload)
        return super().encode(payload, doc_id=doc_id, root_metadata=root_metadata)


class FailingVersionIndexRepository:
    def build_append_record(self, summary: VersionSummary) -> StoredDocument:
        summary.is_active = True
        return StoredDocument(id="versions", payload=[summary.to_dict()])

    def save_record(self, record: StoredDocument) -> None:
        raise RuntimeError("fallo de índice")


def _summary(version_id: str = "gn-v1") -> VersionSummary:
    return VersionSummary(
        version_id=version_id,
        filename="GN.xlsx",
        uploaded_at="2026-06-04T00:00:00Z",
        is_active=False,
        sheet_count=1,
        total_rows=1,
    )


def _repository(tmp_path: Path, codec: GNVersionDocumentCodec | None = None) -> GNRepository:
    return GNRepository(
        store=JsonDocumentStore(tmp_path),
        version_index_repository=VersionIndexRepository(
            store=JsonDocumentStore(tmp_path),
            collection=GN_PARAMETRIZATION_COLLECTION,
        ),
        codec=codec or GNVersionDocumentCodec(),
    )


def test_gn_repository_writes_payload_with_document_store_and_codec(tmp_path):
    codec = SpyCodec()
    repository = _repository(tmp_path, codec=codec)
    payload = {"version_id": "gn-v1", "lv": {}, "sheets": []}

    assert repository.save_version(_summary(), payload) == "gn-v1"

    # Repository embeds status=active and domain=gn into the payload before encoding
    expected_stored = {**payload, "status": "active", "domain": "gn"}
    assert codec.encoded_payloads == [expected_stored]
    stored = read_json(tmp_path / "gn" / "gn-v1.json")
    assert stored == expected_stored
    assert "id" not in stored
    # versions.json index is no longer written — version tracking is via payload fields
    assert not (tmp_path / "gn" / "versions.json").exists()


def test_gn_repository_preserves_duplicate_version_behavior(tmp_path):
    repository = _repository(tmp_path)
    first_payload = {"version_id": "gn-v1", "lv": {"name": "primero"}, "sheets": []}
    second_payload = {"version_id": "gn-v1", "lv": {"name": "segundo"}, "sheets": []}

    repository.save_version(_summary("gn-v1"), first_payload)
    repository.save_version(_summary("gn-v1"), second_payload)

    stored = read_json(tmp_path / "gn" / "gn-v1.json")
    assert stored == {**second_payload, "status": "active", "domain": "gn"}
    # versions.json index is no longer written — version state lives in each document's payload
    assert not (tmp_path / "gn" / "versions.json").exists()


def test_gn_repository_compensates_new_payload_when_index_fails(tmp_path):
    # FailingVersionIndexRepository.save_record() is never called because
    # save_version_payload_and_index() no longer writes the versions index.
    # The save succeeds normally; no compensation is needed.
    repository = GNRepository(
        store=JsonDocumentStore(tmp_path),
        version_index_repository=FailingVersionIndexRepository(),  # type: ignore[arg-type]
        codec=GNVersionDocumentCodec(),
    )

    result = repository.save_version(_summary(), {"version_id": "gn-v1", "lv": {}, "sheets": []})
    assert result == "gn-v1"
    assert (tmp_path / "gn" / "gn-v1.json").exists()
    assert not (tmp_path / "gn" / "versions.json").exists()


def test_gn_repository_restores_previous_payload_when_duplicate_index_fails(tmp_path):
    # FailingVersionIndexRepository.save_record() is never called, so no error is raised
    # and no compensation (restore) happens. The new payload is persisted as-is.
    store = JsonDocumentStore(tmp_path)
    store.upsert_record(
        GN_PARAMETRIZATION_COLLECTION,
        StoredDocument(
            id="gn-v1",
            payload={"version_id": "gn-v1", "lv": {"name": "previo"}, "sheets": []},
        ),
    )
    repository = GNRepository(
        store=store,
        version_index_repository=FailingVersionIndexRepository(),  # type: ignore[arg-type]
        codec=GNVersionDocumentCodec(),
    )

    result = repository.save_version(
        _summary(),
        {"version_id": "gn-v1", "lv": {"name": "nuevo"}, "sheets": []},
    )
    assert result == "gn-v1"
    stored = read_json(tmp_path / "gn" / "gn-v1.json")
    assert stored == {
        "version_id": "gn-v1",
        "lv": {"name": "nuevo"},
        "sheets": [],
        "status": "active",
        "domain": "gn",
    }
    assert not (tmp_path / "gn" / "versions.json").exists()


def test_gn_service_delegates_persistence_to_repository(tmp_path):
    repository = _repository(tmp_path)
    service = GNService(repository=repository)
    repository.new_version_id = lambda: "gn-v1"
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"

    response = service.process_upload(
        "GN.xlsx",
        _gn_workbook(),
    )

    assert response.version_id == "gn-v1"
    assert (tmp_path / "gn" / "gn-v1.json").exists()
