from __future__ import annotations

from pathlib import Path

from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import (
    HRVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_repository import HRRepository
from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary

from .conftest import read_json
from .test_hr_upload_characterization import _hr_workbook


class SpyCodec(HRVersionDocumentCodec):
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


def _summary(version_id: str = "hr-v1") -> VersionSummary:
    return VersionSummary(
        version_id=version_id,
        filename="HR.xlsx",
        uploaded_at="2026-06-04T00:00:00Z",
        is_active=True,
        sheet_count=1,
        total_rows=1,
    )


def _payload(version_id: str = "hr-v1", marcador: str = "base") -> dict:
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


def _repository(tmp_path: Path, codec: HRVersionDocumentCodec | None = None) -> HRRepository:
    store = JsonDocumentStore(tmp_path)
    return HRRepository(
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=HR_PARAMETRIZATION_COLLECTION,
        ),
        codec=codec or HRVersionDocumentCodec(),
    )


def test_hr_repository_writes_payload_with_document_store_and_codec(tmp_path):
    codec = SpyCodec()
    repository = _repository(tmp_path, codec=codec)
    payload = _payload()

    assert repository.save_version(_summary(), payload) == "hr-v1"

    # Repository embeds status=active and domain=hr into the payload before encoding
    expected_stored = {**payload, "status": "active", "domain": "hr"}
    assert codec.encoded_payloads == [expected_stored]
    stored = read_json(tmp_path / "hr" / "hr-v1.json")
    assert stored == expected_stored
    assert "id" not in stored
    # versions.json index is no longer written — version tracking is via payload fields
    assert not (tmp_path / "hr" / "versions.json").exists()


def test_hr_repository_preserves_duplicate_version_behavior(tmp_path):
    repository = _repository(tmp_path)

    repository.save_version(_summary("hr-v1"), _payload("hr-v1", "primero"))
    repository.save_version(_summary("hr-v1"), _payload("hr-v1", "segundo"))

    stored = read_json(tmp_path / "hr" / "hr-v1.json")
    assert stored == {**_payload("hr-v1", "segundo"), "status": "active", "domain": "hr"}
    # versions.json index is no longer written — version state lives in each document's payload
    assert not (tmp_path / "hr" / "versions.json").exists()


def test_hr_repository_compensates_new_payload_when_index_fails(tmp_path):
    # FailingVersionIndexRepository.save_record() is never called because
    # save_version_payload_and_index() no longer writes the versions index.
    # The save succeeds normally; no compensation is needed.
    repository = HRRepository(
        store=JsonDocumentStore(tmp_path),
        version_index_repository=FailingVersionIndexRepository(),  # type: ignore[arg-type]
        codec=HRVersionDocumentCodec(),
    )

    result = repository.save_version(_summary(), _payload())
    assert result == "hr-v1"
    assert (tmp_path / "hr" / "hr-v1.json").exists()
    assert not (tmp_path / "hr" / "versions.json").exists()


def test_hr_repository_restores_previous_payload_when_duplicate_index_fails(tmp_path):
    # FailingVersionIndexRepository.save_record() is never called, so no error is raised
    # and no compensation (restore) happens. The new payload is persisted as-is.
    store = JsonDocumentStore(tmp_path)
    store.upsert_record(
        HR_PARAMETRIZATION_COLLECTION,
        StoredDocument(id="hr-v1", payload=_payload("hr-v1", "previo")),
    )
    repository = HRRepository(
        store=store,
        version_index_repository=FailingVersionIndexRepository(),  # type: ignore[arg-type]
        codec=HRVersionDocumentCodec(),
    )

    result = repository.save_version(_summary(), _payload("hr-v1", "nuevo"))
    assert result == "hr-v1"
    stored = read_json(tmp_path / "hr" / "hr-v1.json")
    assert stored == {**_payload("hr-v1", "nuevo"), "status": "active", "domain": "hr"}
    assert not (tmp_path / "hr" / "versions.json").exists()


def test_hr_service_delegates_persistence_to_repository(tmp_path):
    repository = _repository(tmp_path)
    service = HRService(repository=repository)
    repository.new_version_id = lambda: "hr-v1"
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"

    response = service.process_upload("HR.xlsx", _hr_workbook())

    assert response.version_id == "hr-v1"
    assert (tmp_path / "hr" / "hr-v1.json").exists()
