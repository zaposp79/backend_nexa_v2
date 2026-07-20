from __future__ import annotations

from pathlib import Path

from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.hr.api import router as hr_router_module
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import HRVersionDocumentCodec
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_repository import HRRepository
from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)

from .conftest import client_for_router, read_json, workbook_bytes


def _hr_workbook() -> bytes:
    """Minimal HR workbook that satisfies the strict production contract."""
    return workbook_bytes({
        # HR-LV: 5 catalog columns (EquipoHITL and EquipoSoporteMantenimiento removed)
        "HR-LV": (
            ["TipoRecurso", "Cargo", "Prestaciones", "SS&Parafiscales", "Recargo"],
            [["Operativo", "Agente Voz", "Cesantias", "Salud", "Nocturno"]],
        ),
        "HR-SalarioBasico": (["Servicio", "Valor"], [["SAC", 1423000]]),
        # HR-Nomina: 5 columns in production order
        "HR-Nomina": (
            ["Cargo", "TipoRecurso", "Cadena", "Salario", "Comision"],
            [["Agente Voz", "Operativo", "A", 1423000, 0]],
        ),
        "HR-Recargos": (["Recargo", "Valor"], [["Nocturno", 0.35]]),
        "HR-SegSocial": (["SS&Parafiscales", "Proporcion"], [["Salud", 0.085]]),
        "HR-Prestaciones": (["Prestaciones", "Valor"], [["Cesantias", 0.0833]]),
        "HR-Ratios": (["Cargo", "CategoriaServicio", "Tipo", "Agentes"], [["Agente Voz", "SAC", "Operativo", 20]]),
        "HR-Complejidad": (["Complejidad", "Valor"], [["Alta", 0.9]]),
        "HR-Rentabilidad": (["CategoriaServicio", "Minimo", "MargenObjetivo"], [["SAC", "17.00%", "18.00%"]]),
        "HR-Campana": (["CategoriaServicio", "Mes", "Valor"], [["SAC", 1, 1.0]]),
        "HR-CostoFijo": (["Ciudad", "Localidad", "ServicioPublico", "Valor"], [["Bogota", "Sur", "Agua", 100000]]),
        "HR-Med-Seg": (["Ciudad", "CentroCosto", "Valor"], [["Bogota", "CC1", 50000]]),
    })


def _install_service(monkeypatch, tmp_path: Path, version_id: str = "hr-fixed-version") -> HRService:
    store = JsonDocumentStore(tmp_path)
    repository = HRRepository(
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=HR_PARAMETRIZATION_COLLECTION,
        ),
        codec=HRVersionDocumentCodec(),
    )
    repository.new_version_id = lambda: version_id
    repository.now_iso = lambda: "2026-06-04T00:00:00Z"
    service = HRService(repository=repository)
    monkeypatch.setattr(hr_router_module, "_service", service)
    return service


def test_hr_upload_creates_exact_version_file_index_and_http_response(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, hr_router_module.router)

    response = client.post(
        "/parametrization/hr/upload",
        files={"file": ("HR_test.xlsx", _hr_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    # HR response is nested: {summary: {...}, payload: {...}}
    summary = data["summary"]
    # 'id' is the internal UUID; 'version_id' is the Colombia datetime display label
    assert summary["id"] == "hr-fixed-version"
    assert summary["filename"] == "HR_test.xlsx"
    assert summary["sheets_missing"] == []
    assert set(summary["sheets_found"]) == {
        "HR-LV", "HR-SalarioBasico", "HR-Nomina", "HR-Recargos",
        "HR-SegSocial", "HR-Prestaciones", "HR-Ratios",
        "HR-Complejidad", "HR-Rentabilidad", "HR-Campana",
        "HR-CostoFijo", "HR-Med-Seg",
    }

    version_file = tmp_path / "hr" / "hr-fixed-version.json"
    assert version_file.exists()
    payload = read_json(version_file)

    # HR-LV produces a catalog keyed by normalized header (5 columns)
    catalogs = payload["lv"]["catalogs"]
    assert catalogs["tiporecurso"] == [{"name": "Operativo"}]
    assert catalogs["cargo"] == [{"name": "Agente Voz"}]
    assert catalogs["prestaciones"] == [{"name": "Cesantias"}]
    assert catalogs["ssparafiscales"] == [{"name": "Salud"}]
    assert catalogs["recargo"] == [{"name": "Nocturno"}]
    assert "equipohitl" not in catalogs
    assert "equiposoportemantenimiento" not in catalogs

    assert payload["salariobasico"] == [{"servicio": "SAC", "valor": 1423000.0}]
    # HR-Nomina rows now include tiporecurso and cadena
    assert payload["nomina"] == [{
        "cargo": "Agente Voz",
        "salario": 1423000.0,
        "comision": 0.0,
        "tiporecurso": "Operativo",
        "cadena": "A",
    }]
    assert payload["recargos"] == [{"recargo": "Nocturno", "valor": 0.35}]
    assert payload["ratios"][0]["cargo"] == "Agente Voz"
    assert "id" not in payload
    # New version must be persisted with status=active and domain=hr in the document file
    # so that query({"domain": "hr", "status": "active"}) works in both Cosmos and JSON store
    assert payload["status"] == "active"
    assert payload["domain"] == "hr"

    # versions.json index is no longer written — version tracking uses payload fields (status/domain)
    assert not (tmp_path / "hr" / "versions.json").exists()

    # HR versions response: 'id' is the internal UUID, 'version_id' is the Colombia datetime label
    assert client.get("/parametrization/hr/versions").json()["data"][0]["id"] == "hr-fixed-version"


def test_hr_upload_second_version_deactivates_previous(monkeypatch, tmp_path, isolated_app):
    """Uploading a second version must set status=active on new and status=inactive on previous."""
    service = _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, hr_router_module.router)

    # First upload — version_id is deterministic ("hr-fixed-version")
    r1 = client.post(
        "/parametrization/hr/upload",
        files={"file": ("HR_first.xlsx", _hr_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r1.status_code == 201

    # Give second upload a different version_id
    service._repo.new_version_id = lambda: "hr-second-version"
    r2 = client.post(
        "/parametrization/hr/upload",
        files={"file": ("HR_second.xlsx", _hr_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r2.status_code == 201

    # versions.json index is no longer written — is_active state is in the document files
    assert not (tmp_path / "hr" / "versions.json").exists()

    # Individual document files must carry status field
    first_doc = read_json(tmp_path / "hr" / "hr-fixed-version.json")
    second_doc = read_json(tmp_path / "hr" / "hr-second-version.json")
    assert first_doc["status"] == "inactive"
    assert first_doc["domain"] == "hr"
    assert second_doc["status"] == "active"
    assert second_doc["domain"] == "hr"


def test_hr_upload_no_file_returns_400(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, hr_router_module.router)

    response = client.post("/parametrization/hr/upload")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "No se cargó ningún archivo" in body["error"]["message"]


def test_hr_upload_invalid_extension_and_invalid_workbook_are_characterized(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, hr_router_module.router)

    # .txt extension → HTTP 400
    bad_extension = client.post(
        "/parametrization/hr/upload",
        files={"file": ("HR_test.txt", b"not excel", "text/plain")},
    )
    assert bad_extension.status_code == 400

    # .xls extension → HTTP 400 (xls removed from allowed list)
    bad_xls = client.post(
        "/parametrization/hr/upload",
        files={"file": ("HR_test.xls", b"not excel", "application/vnd.ms-excel")},
    )
    assert bad_xls.status_code == 400

    # .xlsx extension but corrupt content → 200 success=False
    invalid_workbook = client.post(
        "/parametrization/hr/upload",
        files={"file": ("HR_test.xlsx", b"not excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert invalid_workbook.status_code == 200
    assert invalid_workbook.json()["success"] is False
    assert invalid_workbook.json()["error"]["code"] in ("INVALID_EXCEL_FILE", "UPLOAD_ERROR")


def test_hr_validation_errors_block_persistence(monkeypatch, tmp_path, isolated_app):
    """Validation errors must NOT be silenced into warnings — no version is created."""
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, hr_router_module.router)

    # Wrong headers in HR-LV (missing required sheets + wrong contract)
    bad_content = workbook_bytes({
        "HR-LV": (["Tipo", "Rol"], [["E", "A"]]),  # missing 4 required headers
    })
    response = client.post(
        "/parametrization/hr/upload",
        files={"file": ("HR_invalid.xlsx", bad_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    assert response.json()["success"] is False

    # No versions.json should have been written
    assert not (tmp_path / "hr" / "versions.json").exists()
