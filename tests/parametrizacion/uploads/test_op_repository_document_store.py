from __future__ import annotations

from pathlib import Path

import pytest

from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.json_document_store import JsonDocumentStore
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
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary

from .conftest import read_json, workbook_bytes
from .test_op_upload_characterization import _op_workbook


class SpyCodec(OPVersionDocumentCodec):
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


def _summary(version_id: str = "op-v1") -> VersionSummary:
    return VersionSummary(
        version_id=version_id,
        filename="OP.xlsx",
        uploaded_at="2026-06-04T00:00:00Z",
        is_active=False,
        sheet_count=1,
        total_rows=1,
    )


def _payload(version_id: str = "op-v1", marcador: str = "base") -> dict:
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


def _repository(tmp_path: Path, codec: OPVersionDocumentCodec | None = None) -> OPRepository:
    store = JsonDocumentStore(tmp_path)
    return OPRepository(
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=OP_PARAMETRIZATION_COLLECTION,
        ),
        codec=codec or OPVersionDocumentCodec(),
    )


def test_op_repository_writes_payload_with_document_store_and_codec(tmp_path):
    codec = SpyCodec()
    repository = _repository(tmp_path, codec=codec)
    payload = _payload()

    assert repository.save_version(_summary(), payload) == "op-v1"

    assert codec.encoded_payloads == [payload]
    assert read_json(tmp_path / "op" / "op-v1.json") == payload
    assert "id" not in read_json(tmp_path / "op" / "op-v1.json")
    assert read_json(tmp_path / "op" / "versions.json") == [
        {
            "version_id": "op-v1",
            "filename": "OP.xlsx",
            "uploaded_at": "2026-06-04T00:00:00Z",
            "is_active": True,
            "sheet_count": 1,
            "total_rows": 1,
        }
    ]


def test_op_repository_preserves_duplicate_version_behavior(tmp_path):
    repository = _repository(tmp_path)

    repository.save_version(_summary("op-v1"), _payload("op-v1", "primero"))
    repository.save_version(_summary("op-v1"), _payload("op-v1", "segundo"))

    assert read_json(tmp_path / "op" / "op-v1.json") == _payload("op-v1", "segundo")
    versions = read_json(tmp_path / "op" / "versions.json")
    assert [entry["version_id"] for entry in versions] == ["op-v1", "op-v1"]
    assert [entry["is_active"] for entry in versions] == [False, True]


def test_op_repository_compensates_new_payload_when_index_fails(tmp_path):
    repository = OPRepository(
        store=JsonDocumentStore(tmp_path),
        version_index_repository=FailingVersionIndexRepository(),  # type: ignore[arg-type]
        codec=OPVersionDocumentCodec(),
    )

    with pytest.raises(RuntimeError, match="fallo de índice"):
        repository.save_version(_summary(), _payload())

    assert not (tmp_path / "op" / "op-v1.json").exists()
    assert not (tmp_path / "op" / "versions.json").exists()


def test_op_repository_restores_previous_payload_when_duplicate_index_fails(tmp_path):
    store = JsonDocumentStore(tmp_path)
    store.upsert_record(
        OP_PARAMETRIZATION_COLLECTION,
        StoredDocument(id="op-v1", payload=_payload("op-v1", "previo")),
    )
    repository = OPRepository(
        store=store,
        version_index_repository=FailingVersionIndexRepository(),  # type: ignore[arg-type]
        codec=OPVersionDocumentCodec(),
    )

    with pytest.raises(RuntimeError, match="fallo de índice"):
        repository.save_version(_summary(), _payload("op-v1", "nuevo"))

    assert read_json(tmp_path / "op" / "op-v1.json") == _payload("op-v1", "previo")


def test_op_service_delegates_persistence_to_repository(tmp_path):
    repository = _repository(tmp_path)
    service = OPService(repository=repository)
    repository.new_version_id = lambda: "op-v1"
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"

    response = service.process_upload("OP.xlsx", _op_workbook())

    assert response.version_id == "op-v1"
    assert (tmp_path / "op" / "op-v1.json").exists()


def test_op_ica_tasa_anomaly_now_blocks_upload(tmp_path):
    """ICA 'Tasa' rows > MAX_TASA_ICA_DECIMAL now raise ValidationError (not a warning).

    Previously the validator emitted a warning for "tasa" rows.
    After the ICA guardrail change, a tasa > 0.05 is an ERROR that
    blocks the upload.  This test verifies the new hard-stop behaviour.
    """
    from nexa_engine.modules.shared.exceptions import ValidationError as DomainValidationError

    repository = _repository(tmp_path)
    service = OPService(repository=repository)
    repository.new_version_id = lambda: "op-v1"
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"
    workbook = workbook_bytes({
        "OP-ICA": (
            ["Ciudad", "ICA", "Valor"],
            [["Bogota", "tasa", 0.97]],   # 0.97 > 0.05 — now a hard error
        ),
        "OP-Poliza": (
            ["Poliza", "Porcentaje", "PorcentajeExigido"],
            [["Cumplimiento", 0.0062, 0.005]],
        ),
    })

    with pytest.raises(DomainValidationError) as exc_info:
        service.process_upload("OP.xlsx", workbook)

    assert any("INVALID_ICA_RATE" in e for e in exc_info.value.errors)
    assert any("Bogota" in e for e in exc_info.value.errors)
    # No file should have been persisted
    assert not (tmp_path / "op" / "op-v1.json").exists()


def test_op_poliza_rate_warning_still_works(tmp_path):
    """OP-Poliza anomalous rates still generate warnings (non-blocking)."""
    repository = _repository(tmp_path)
    service = OPService(repository=repository)
    repository.new_version_id = lambda: "op-v1"
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"
    workbook = workbook_bytes({
        "OP-ICA": (
            ["Ciudad", "ICA", "Valor"],
            [["Bogota", "Tasa", 0.0097]],  # valid tasa
        ),
        "OP-Poliza": (
            ["Poliza", "Porcentaje", "PorcentajeExigido"],
            [["Cumplimiento", 2.75, 0.005]],  # 275% Porcentaje — warning but not error
        ),
    })

    response = service.process_upload("OP.xlsx", workbook)

    assert response.version_id == "op-v1"
    assert any("OP-Poliza" in w or "Cumplimiento" in w for w in response.warnings)
