from __future__ import annotations

from pathlib import Path

import pytest

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

    def encode(self, payload: dict) -> StoredDocument:
        self.encoded_payloads.append(payload)
        return super().encode(payload)


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

    assert codec.encoded_payloads == [payload]
    assert read_json(tmp_path / "hr" / "hr-v1.json") == payload
    assert "id" not in read_json(tmp_path / "hr" / "hr-v1.json")
    assert read_json(tmp_path / "hr" / "versions.json") == [
        {
            "version_id": "hr-v1",
            "filename": "HR.xlsx",
            "uploaded_at": "2026-06-04T00:00:00Z",
            "is_active": True,
            "sheet_count": 1,
            "total_rows": 1,
        }
    ]


def test_hr_repository_preserves_duplicate_version_behavior(tmp_path):
    repository = _repository(tmp_path)

    repository.save_version(_summary("hr-v1"), _payload("hr-v1", "primero"))
    repository.save_version(_summary("hr-v1"), _payload("hr-v1", "segundo"))

    assert read_json(tmp_path / "hr" / "hr-v1.json") == _payload("hr-v1", "segundo")
    versions = read_json(tmp_path / "hr" / "versions.json")
    assert [entry["version_id"] for entry in versions] == ["hr-v1", "hr-v1"]
    assert [entry["is_active"] for entry in versions] == [False, True]


def test_hr_repository_compensates_new_payload_when_index_fails(tmp_path):
    repository = HRRepository(
        store=JsonDocumentStore(tmp_path),
        version_index_repository=FailingVersionIndexRepository(),  # type: ignore[arg-type]
        codec=HRVersionDocumentCodec(),
    )

    with pytest.raises(RuntimeError, match="fallo de índice"):
        repository.save_version(_summary(), _payload())

    assert not (tmp_path / "hr" / "hr-v1.json").exists()
    assert not (tmp_path / "hr" / "versions.json").exists()


def test_hr_repository_restores_previous_payload_when_duplicate_index_fails(tmp_path):
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

    with pytest.raises(RuntimeError, match="fallo de índice"):
        repository.save_version(_summary(), _payload("hr-v1", "nuevo"))

    assert read_json(tmp_path / "hr" / "hr-v1.json") == _payload("hr-v1", "previo")


def test_hr_service_delegates_persistence_to_repository(tmp_path):
    repository = _repository(tmp_path)
    service = HRService(repository=repository)
    repository.new_version_id = lambda: "hr-v1"
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"

    response = service.process_upload("HR.xlsx", _hr_workbook())

    assert response.version_id == "hr-v1"
    assert (tmp_path / "hr" / "hr-v1.json").exists()
