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
    """
    return workbook_bytes({
        "OP-ICA": (
            ["Ciudad", "ICA", "Valor"],
            [["Bogota", "Tasa", 0.0097]],
        ),
        "OP-Poliza": (
            ["Poliza", "Porcentaje", "PorcentajeExigido"],
            [["Cumplimiento", 0.0062, 0.005]],
        ),
        "OP-LV": (
            ["ICA"],  # production contract: single column ICA
            [["Tasa"], ["Avisos & Tableros"]],
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

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["version_id"] == "op-fixed-version"
    assert body["data"]["filename"] == "OP_test.xlsx"
    assert set(body["data"]["sheets_found"]) == {"OP-ICA", "OP-Poliza", "OP-LV"}

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

    assert read_json(tmp_path / "op" / "versions.json") == [
        {
            "version_id": "op-fixed-version",
            "filename": "OP_test.xlsx",
            "uploaded_at": "2026-06-04T00:00:00Z",
            "is_active": True,
            "sheet_count": 3,
            "total_rows": 4,  # 1 ICA + 1 Poliza + 2 LV
        }
    ]

    assert client.get("/parametrization/op/versions").json()["data"][0]["version_id"] == "op-fixed-version"
    assert client.get("/parametrization/op/active").json()["data"]["summary"]["is_active"] is True


def test_op_upload_duplicate_version_id_appends_duplicate_index_entry(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, op_router_module.router)

    for filename in ("OP_first.xlsx", "OP_second.xlsx"):
        response = client.post(
            "/parametrization/op/upload",
            files={"file": (filename, _op_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    versions = read_json(tmp_path / "op" / "versions.json")
    assert [entry["version_id"] for entry in versions] == ["op-fixed-version", "op-fixed-version"]
    assert [entry["filename"] for entry in versions] == ["OP_first.xlsx", "OP_second.xlsx"]
    assert [entry["is_active"] for entry in versions] == [False, True]


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
