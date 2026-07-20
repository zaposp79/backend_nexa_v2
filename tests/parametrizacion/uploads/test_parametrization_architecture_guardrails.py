from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from nexa_engine.modules.parametrizacion.gn.repositories.gn_active_parametrization_repository import (
    GNActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_repository import GNRepository
from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
    HRActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_repository import HRRepository
from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
    OPActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_repository import OPRepository
from nexa_engine.modules.parametrizacion.shared.repositories.version_payload_persistence import (
    save_version_payload_and_index,
)


BACKEND_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOTS = [BACKEND_ROOT / "db", BACKEND_ROOT / "modules"]
ACTIVE_REPOSITORIES = [
    GNActiveParametrizationRepository,
    HRActiveParametrizationRepository,
    OPActiveParametrizationRepository,
]
UPLOAD_REPOSITORIES = [GNRepository, HRRepository, OPRepository]


def _runtime_python_files() -> list[Path]:
    files: list[Path] = []
    for root in RUNTIME_ROOTS:
        files.extend(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    return files


def test_parametrization_json_store_is_only_hardcoded_in_factory() -> None:
    offenders = []
    allowed = BACKEND_ROOT / "db/factory.py"
    for path in _runtime_python_files():
        source = path.read_text(encoding="utf-8")
        if "JsonDocumentStore(PARAMETRIZATION_DIR)" in source and path != allowed:
            offenders.append(str(path.relative_to(BACKEND_ROOT)))

    assert offenders == []


@pytest.mark.parametrize("repository_cls", ACTIVE_REPOSITORIES)
def test_active_repositories_use_store_api_and_not_store_get(repository_cls: type) -> None:
    source = inspect.getsource(repository_cls.get_active_data)

    assert "self._store.query(" in source
    assert "self._store.get(" not in source


@pytest.mark.parametrize("repository_cls", ACTIVE_REPOSITORIES)
def test_active_repositories_keep_filesystem_only_after_record_lookup(
    repository_cls: type,
) -> None:
    source = inspect.getsource(repository_cls.get_active_data)

    if "read_json(" not in source:
        return
    assert source.index("get_record(") < source.index("read_json(")


@pytest.mark.parametrize("repository_cls", UPLOAD_REPOSITORIES)
def test_upload_repositories_do_not_use_direct_filesystem_or_json_provider(
    repository_cls: type,
) -> None:
    source = inspect.getsource(repository_cls)
    forbidden = [
        "JsonDocumentStore",
        "Path(",
        "from pathlib import Path",
        "open(",
        "json.dump",
        "read_json(",
        "write_json(",
        "write_text(",
        "self._store.get(",
    ]

    assert [token for token in forbidden if token in source] == []


def test_upload_persistence_uses_record_api_as_primary_write_route() -> None:
    source = inspect.getsource(save_version_payload_and_index)

    assert "upsert_record(" in source
    assert "upsert_records_atomic(" not in source
    assert "self._store.get(" not in source
    assert "open(" not in source
    assert "json.dump" not in source


def test_parametrization_provider_is_selected_by_configuration_only() -> None:
    from nexa_engine.db import container, factory

    factory_source = inspect.getsource(factory)
    container_source = inspect.getsource(container)

    assert "build_parametrization_document_store" in factory_source
    assert "load_config()" in container_source
    assert "build_parametrization_document_store(db_config)" in container_source
    assert "JsonDocumentStore" not in container_source
    assert "CosmosDocumentStore" not in container_source


def test_business_rules_repository_was_removed_from_active_parametrization() -> None:
    import importlib.util

    assert importlib.util.find_spec(
        "nexa_engine.modules.parametrizacion.business_rules"
    ) is None


# ===========================================================================
# Contract alignment guardrails — Excel definitivo V2-8
# ===========================================================================

def test_op_billing_componente_not_in_op_contract() -> None:
    """OP-BillingComponente must not exist in OP_CONTRACT — removed in Excel V2-8."""
    from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT

    sheet_names = {s.excel_name for s in OP_CONTRACT.sheets}
    assert "OP-BillingComponente" not in sheet_names
    assert "OP-HITLCadenaB" not in sheet_names
    assert "OP-Tasa" not in sheet_names
    assert "OP-DatosOperativos" not in sheet_names


def test_op_poliza_uses_definitive_headers() -> None:
    """OP-Poliza must have headers [Poliza, Porcentaje, PorcentajeExigido] — Excel V2-8."""
    from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT

    poliza = next(s for s in OP_CONTRACT.sheets if s.excel_name == "OP-Poliza")
    assert list(poliza.headers) == ["Poliza", "Porcentaje", "PorcentajeExigido"]



def test_gn_lv_includes_divisa_column() -> None:
    """GN-LV must include 'Divisa' as the last column — added in Excel V2-8."""
    from nexa_engine.modules.parametrizacion.gn.contracts import GN_CONTRACT

    lv = next(s for s in GN_CONTRACT.sheets if s.excel_name == "GN-LV")
    headers = lv.headers
    assert "Divisa" in headers
    assert headers[-1] == "Divisa"
    assert len(headers) == 23


def test_op_new_sheets_registered_in_contract() -> None:
    """OP-PolizaFija, OP-Costo and OP-MargenObjetivo must exist in OP_CONTRACT."""
    from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT

    sheet_names = {s.excel_name for s in OP_CONTRACT.sheets}
    assert "OP-PolizaFija" in sheet_names
    assert "OP-Costo" in sheet_names
    assert "OP-MargenObjetivo" in sheet_names
