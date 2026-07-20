from __future__ import annotations

from pathlib import Path

from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.op.api import router as op_router_module
from nexa_engine.modules.parametrizacion.op.mappers.op_version_document_codec import OPVersionDocumentCodec
from nexa_engine.modules.parametrizacion.op.repositories.collections import (
    OP_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_repository import OPRepository
from nexa_engine.modules.parametrizacion.op.services.op_service import OPService
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)

from .conftest import client_for_router, read_json, workbook_bytes


def _op_workbook() -> bytes:
    """Minimal OP workbook that satisfies the strict production contract.

    Uses only sheets that are in the authorized OP contract with exact headers.
    OP-LV production header: ['ICA'] (single catalog column).
    OP-ReglaNegocio is the only required sheet.
    """
    return workbook_bytes({
        "OP-ReglaNegocio": (
            ["ReglaNegocio", "Minimo", "Maximo"],
            [["Regla1", 0.0, 1.0]],
        ),
        "OP-ICA": (
            ["Ciudad", "ICA", "Valor"],
            [["Bogota", "Tasa", 0.0097]],
        ),
        "OP-Poliza": (
            ["Poliza", "Porcentaje", "PorcentajeExigido"],
            [["Cumplimiento", 0.0062, 0.005]],
        ),
        "OP-LV": (
            # production contract: 4 columns (CATALOG_BY_COLUMN)
            ["ICA", "DispositivoRequerido", "DuracionMes", "InteresIndexMensual"],
            [["Tasa", None, None, None], ["Avisos & Tableros", None, None, None]],
        ),
    })


def _install_service(monkeypatch, tmp_path: Path, version_id: str = "op-fixed-version") -> OPService:
    store = JsonDocumentStore(tmp_path)
    repository = OPRepository(
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=OP_PARAMETRIZATION_COLLECTION,
        ),
        codec=OPVersionDocumentCodec(),
    )
    repository.new_version_id = lambda: version_id
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"
    service = OPService(repository=repository)
    monkeypatch.setattr(op_router_module, "_service", service)
    return service


def test_op_upload_creates_exact_version_file_index_and_http_response(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, op_router_module.router)

    response = client.post(
        "/parametrization/op/upload",
        files={"file": ("OP_test.xlsx", _op_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    # OP service uses a Colombia-local datetime as the human-readable version_id in the response
    assert body["data"]["version_id"]  # non-empty
    assert body["data"]["filename"] == "OP_test.xlsx"
    assert set(body["data"]["sheets_found"]) == {"OP-ICA", "OP-Poliza", "OP-LV", "OP-ReglaNegocio"}

    version_file = tmp_path / "op" / "op-fixed-version.json"
    payload = read_json(version_file)
    assert version_file.exists()
    assert "id" not in payload

    # OP-LV: single column ICA — catalog by column
    lv_sheet = next(s for s in payload["sheets"] if s["name"] == "OP-LV")
    assert "catalogs" in lv_sheet
    assert lv_sheet["catalogs"]["ica"] == [{"name": "Tasa"}, {"name": "Avisos & Tableros"}]

    # OP-ICA and OP-Poliza: table rows
    ica_sheet = next(s for s in payload["sheets"] if s["name"] == "OP-ICA")
    assert ica_sheet["rows"][0]["ciudad"] == "Bogota"

    # versions.json index is no longer written — version tracking uses payload fields (status/domain)
    assert not (tmp_path / "op" / "versions.json").exists()
    # New version document must carry status=active and domain=op
    assert payload["status"] == "active"
    assert payload["domain"] == "op"

    # OP versions response: 'id' is the internal UUID, 'version_id' is the Colombia datetime label
    assert client.get("/parametrization/op/versions").json()["data"][0]["id"] == "op-fixed-version"


def test_op_upload_second_version_deactivates_previous(monkeypatch, tmp_path, isolated_app):
    """Uploading a second version must set status=active on new and status=inactive on previous."""
    service = _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, op_router_module.router)

    r1 = client.post(
        "/parametrization/op/upload",
        files={"file": ("OP_first.xlsx", _op_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r1.status_code == 201

    service._repo.new_version_id = lambda: "op-second-version"
    r2 = client.post(
        "/parametrization/op/upload",
        files={"file": ("OP_second.xlsx", _op_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r2.status_code == 201

    # versions.json index is no longer written — is_active state is in the document files
    assert not (tmp_path / "op" / "versions.json").exists()

    first_doc = read_json(tmp_path / "op" / "op-fixed-version.json")
    second_doc = read_json(tmp_path / "op" / "op-second-version.json")
    assert first_doc["status"] == "inactive"
    assert first_doc["domain"] == "op"
    assert second_doc["status"] == "active"
    assert second_doc["domain"] == "op"


def test_op_upload_duplicate_version_id_appends_duplicate_index_entry(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, op_router_module.router)

    for filename in ("OP_first.xlsx", "OP_second.xlsx"):
        response = client.post(
            "/parametrization/op/upload",
            files={"file": (filename, _op_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

    # versions.json index is no longer written — version state lives in each document's payload
    assert not (tmp_path / "op" / "versions.json").exists()


def test_op_upload_no_file_returns_400(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, op_router_module.router)

    response = client.post("/parametrization/op/upload")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "No se cargó ningún archivo" in body["error"]["message"]


def test_op_upload_invalid_extension_and_invalid_workbook_are_characterized(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, op_router_module.router)

    bad_extension = client.post(
        "/parametrization/op/upload",
        files={"file": ("OP_test.txt", b"not excel", "text/plain")},
    )
    assert bad_extension.status_code == 400

    invalid_workbook = client.post(
        "/parametrization/op/upload",
        files={"file": ("OP_test.xlsx", b"not excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert invalid_workbook.status_code == 200
    assert invalid_workbook.json()["success"] is False
    assert invalid_workbook.json()["error"]["code"] in ("INVALID_EXCEL_FILE", "UPLOAD_ERROR")
