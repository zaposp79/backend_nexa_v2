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
        # HR-LV: catalog-by-column — exact production headers
        "HR-LV": (
            ["Tipo", "Rol", "Servicio", "Prestaciones", "SS&Parafiscales", "Recargo"],
            [["Empleado", "Agente", "Cobranzas", "Cesantias", "Salud", "Recargo festivo"]],
        ),
        "HR-SalarioBasico": (["Servicio", "Valor"], [["Cobranzas", 1423000]]),
        # HR-Nomina: trailing None columns allowed by contract
        "HR-Nomina": (["Tipo", "Rol", "Salario", None, None], [["Operativo", "Agente", 1423000, None, None]]),
        "HR-Recargos": (["Recargo", "Valor"], [["Nocturno", 0.35]]),
        "HR-SegSocial": (["SS&Parafiscales", "Proporcion"], [["Salud", 0.085]]),
        "HR-Prestaciones": (["Prestaciones", "Valor"], [["Cesantias", 0.0833]]),
        # HR-Ratios: "Cargo" (without trailing space) — reader strips whitespace
        "HR-Ratios": (["Cargo", "CategoriaServicio", "Tipo", "Agentes"], [["Supervisor", "Cobranzas", "Operativo", 20]]),
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

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["version_id"] == "hr-fixed-version"
    assert data["filename"] == "HR_test.xlsx"
    assert data["sheets_missing"] == []
    assert set(data["sheets_found"]) == {
        "HR-LV", "HR-SalarioBasico", "HR-Nomina", "HR-Recargos",
        "HR-SegSocial", "HR-Prestaciones", "HR-Ratios",
    }

    version_file = tmp_path / "hr" / "hr-fixed-version.json"
    assert version_file.exists()
    payload = read_json(version_file)

    # HR-LV produces a catalog keyed by normalized header
    catalogs = payload["niveles"]["catalogs"]
    assert catalogs["tipo"] == [{"name": "Empleado"}]
    assert catalogs["rol"] == [{"name": "Agente"}]
    assert catalogs["servicio"] == [{"name": "Cobranzas"}]
    assert catalogs["prestaciones"] == [{"name": "Cesantias"}]
    assert catalogs["ssparafiscales"] == [{"name": "Salud"}]
    assert catalogs["recargo"] == [{"name": "Recargo festivo"}]

    assert payload["salarios"] == [{"servicio": "Cobranzas", "valor": 1423000.0}]
    assert payload["nomina"] == [{"tipo": "Operativo", "rol": "Agente", "salario": 1423000.0}]
    assert payload["recargos"] == [{"recargo": "Nocturno", "valor": 0.35}]
    assert payload["ratios"][0]["cargo"] == "Supervisor"
    assert "id" not in payload

    versions = read_json(tmp_path / "hr" / "versions.json")
    assert versions[0]["version_id"] == "hr-fixed-version"
    assert versions[0]["is_active"] is True

    assert client.get("/parametrization/hr/versions").json()["data"][0]["version_id"] == "hr-fixed-version"
    assert client.get("/parametrization/hr/active").json()["data"]["summary"]["is_active"] is True


def test_hr_upload_duplicate_version_id_appends_duplicate_index_entry(monkeypatch, tmp_path, isolated_app):
    _install_service(monkeypatch, tmp_path)
    client = client_for_router(isolated_app, hr_router_module.router)

    for filename in ("HR_first.xlsx", "HR_second.xlsx"):
        response = client.post(
            "/parametrization/hr/upload",
            files={"file": (filename, _hr_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    versions = read_json(tmp_path / "hr" / "versions.json")
    assert [e["version_id"] for e in versions] == ["hr-fixed-version", "hr-fixed-version"]
    assert [e["filename"] for e in versions] == ["HR_first.xlsx", "HR_second.xlsx"]
    assert [e["is_active"] for e in versions] == [False, True]


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
