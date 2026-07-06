from __future__ import annotations

from pathlib import Path

from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.gn.api import router as gn_router_module
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import GNVersionDocumentCodec
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_repository import GNRepository
from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)

from .conftest import client_for_router, read_json, workbook_bytes

_GN_LV_HEADERS = [
    "Ciudad", "Localidad", "Servicio", "CategoriaServicio", "CentroCosto",
    "Componente", "Poliza", "ComponenteFijo", "HardwareSoftware", "PeriodoPago",
    "Cadena", "ComponenteVariable", "ModeloCombro", "Modalidad", "ReglaNegocio",
    "Canal", "Metrica", "Cliente", "TipoCobro", "TipoCliente", "Rubro", "UnidadMedida",
    "Divisa",
]

_GN_LV_ROW = [
    "Bogota", "Bogota Norte", "Cobranzas", "Cuentas", "CC01",
    "Op", "Pol1", "Fijo", "PC", "Mensual",
    "A", "Var1", "Fijo", "Inbound", "R1",
    "Digital", "M1", "BancaMia", "TC1", "TipoA", "Rubro1", "Und",
    "COP",
]


def _gn_workbook() -> bytes:
    return workbook_bytes({
        "GN-LV": (_GN_LV_HEADERS, [_GN_LV_ROW]),
    })


def _install_service(monkeypatch, tmp_path: Path, version_id: str = "gn-fixed-version") -> GNService:
    store = JsonDocumentStore(tmp_path)
    repository = GNRepository(
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=GN_PARAMETRIZATION_COLLECTION,
        ),
        codec=GNVersionDocumentCodec(),
    )
    repository.new_version_id = lambda: version_id
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"
    service = GNService(repository=repository)
    monkeypatch.setattr(gn_router_module, "_service", service)
    return service


def test_gn_upload_creates_exact_version_file_index_and_http_response(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, gn_router_module.router)

    response = client.post(
        "/parametrization/gn/upload",
        files={"file": ("GN_test.xlsx", _gn_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    # GN service uses a Colombia-local datetime as the human-readable version_id in the response
    assert body["data"]["version_id"]  # non-empty
    assert body["data"]["sheets_found"] == ["GN-LV"]

    version_file = tmp_path / "gn" / "gn-fixed-version.json"
    assert version_file.exists()
    payload = read_json(version_file)

    # GN-LV is a catalog sheet — lv.catalogs must exist
    assert "lv" in payload
    assert "catalogs" in payload["lv"]
    catalogs = payload["lv"]["catalogs"]

    # Each header column is a catalog key (normalised)
    assert "ciudad" in catalogs
    assert "localidad" in catalogs
    assert "servicio" in catalogs
    # Values must be {name: ...} objects
    assert catalogs["ciudad"] == [{"name": "Bogota"}]
    assert catalogs["localidad"] == [{"name": "Bogota Norte"}]

    assert "id" not in payload
    # New version must be persisted with status=active and domain=gn in the document file
    assert payload["status"] == "active"
    assert payload["domain"] == "gn"

    assert read_json(tmp_path / "gn" / "versions.json")[0]["version_id"] == "gn-fixed-version"

    versions_response = client.get("/parametrization/gn/versions")
    assert versions_response.status_code == 200
    # GN versions response: 'id' is the internal UUID, 'version_id' is the Colombia datetime label
    assert versions_response.json()["data"][0]["id"] == "gn-fixed-version"


def test_gn_upload_second_version_deactivates_previous(monkeypatch, tmp_path, isolated_app):
    """Uploading a second version must set status=active on new and status=inactive on previous."""
    service = _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, gn_router_module.router)

    r1 = client.post(
        "/parametrization/gn/upload",
        files={"file": ("GN_first.xlsx", _gn_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r1.status_code == 201

    service._repo.new_version_id = lambda: "gn-second-version"
    r2 = client.post(
        "/parametrization/gn/upload",
        files={"file": ("GN_second.xlsx", _gn_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r2.status_code == 201

    versions = read_json(tmp_path / "gn" / "versions.json")
    assert [e["version_id"] for e in versions] == ["gn-fixed-version", "gn-second-version"]
    assert [e["is_active"] for e in versions] == [False, True]

    first_doc = read_json(tmp_path / "gn" / "gn-fixed-version.json")
    second_doc = read_json(tmp_path / "gn" / "gn-second-version.json")
    assert first_doc["status"] == "inactive"
    assert first_doc["domain"] == "gn"
    assert second_doc["status"] == "active"
    assert second_doc["domain"] == "gn"


def test_gn_upload_duplicate_version_id_appends_duplicate_index_entry(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, gn_router_module.router)

    for filename in ("GN_first.xlsx", "GN_second.xlsx"):
        response = client.post(
            "/parametrization/gn/upload",
            files={"file": (filename, _gn_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

    versions = read_json(tmp_path / "gn" / "versions.json")
    assert [e["version_id"] for e in versions] == ["gn-fixed-version", "gn-fixed-version"]
    assert [e["filename"] for e in versions] == ["GN_first.xlsx", "GN_second.xlsx"]
    assert [e["is_active"] for e in versions] == [False, True]


def test_gn_upload_invalid_extension_and_invalid_workbook_are_characterized(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, gn_router_module.router)

    bad_extension = client.post(
        "/parametrization/gn/upload",
        files={"file": ("GN_test.txt", b"not excel", "text/plain")},
    )
    assert bad_extension.status_code == 400

    # .xls now rejected at extension check
    bad_xls = client.post(
        "/parametrization/gn/upload",
        files={"file": ("GN_test.xls", b"not excel", "application/vnd.ms-excel")},
    )
    assert bad_xls.status_code == 400

    invalid_workbook = client.post(
        "/parametrization/gn/upload",
        files={"file": ("GN_test.xlsx", b"not excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert invalid_workbook.status_code == 200
    assert invalid_workbook.json()["success"] is False
    assert invalid_workbook.json()["error"]["code"] in ("INVALID_EXCEL_FILE", "UPLOAD_ERROR")
