from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from nexa_engine.db.providers.json_document_store import JsonDocumentStore
from nexa_engine.modules.parametrizacion.gn.api import router as gn_router_module
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import (
    GNVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_repository import GNRepository
from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.hr.api import router as hr_router_module
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import (
    HRVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_repository import HRRepository
from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.op.api import router as op_router_module
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
from nexa_engine.modules.parametrizacion.shared.repositories.version_payload_persistence import (
    save_version_payload_and_index,
)
from nexa_engine.modules.parametrizacion.shared.models.version_summary import (
    VersionSummary,
)

from .conftest import read_json




def _gn_payload(version_id: str, marcador: str) -> dict[str, Any]:
    return {
        "version_id": version_id,
        "lv": {"name": marcador},
        "sheets": [],
    }


def _hr_payload(version_id: str, marcador: str) -> dict[str, Any]:
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


def _op_payload(version_id: str, marcador: str) -> dict[str, Any]:
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


UPLOAD_DOMAINS = [
    pytest.param(
        {
            "domain": "gn",
            "repository_cls": GNRepository,
            "service_cls": GNService,
            "router_module": gn_router_module,
            "collection": GN_PARAMETRIZATION_COLLECTION,
            "codec_cls": GNVersionDocumentCodec,
            "payload_factory": _gn_payload,
            "container_service": "gn_upload_service",
        },
        id="gn",
    ),
    pytest.param(
        {
            "domain": "hr",
            "repository_cls": HRRepository,
            "service_cls": HRService,
            "router_module": hr_router_module,
            "collection": HR_PARAMETRIZATION_COLLECTION,
            "codec_cls": HRVersionDocumentCodec,
            "payload_factory": _hr_payload,
            "container_service": "hr_upload_service",
        },
        id="hr",
    ),
    pytest.param(
        {
            "domain": "op",
            "repository_cls": OPRepository,
            "service_cls": OPService,
            "router_module": op_router_module,
            "collection": OP_PARAMETRIZATION_COLLECTION,
            "codec_cls": OPVersionDocumentCodec,
            "payload_factory": _op_payload,
            "container_service": "op_upload_service",
        },
        id="op",
    ),
]


def _summary(domain: str, version_id: str) -> VersionSummary:
    return VersionSummary(
        version_id=version_id,
        filename=f"{domain.upper()}.xlsx",
        uploaded_at="2026-06-04T00:00:00Z",
        is_active=False,
        sheet_count=1,
        total_rows=1,
    )


def _repository(domain_config: dict[str, Any], tmp_path: Path):
    store = JsonDocumentStore(tmp_path)
    return domain_config["repository_cls"](
        store=store,
        version_index_repository=VersionIndexRepository(
            store=store,
            collection=domain_config["collection"],
        ),
        codec=domain_config["codec_cls"](),
    )



@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_repository_has_document_store_boundary(domain_config):
    repository_cls = domain_config["repository_cls"]
    signature = inspect.signature(repository_cls.__init__)

    # BaseRepository was deleted in FASE DB.6.5 — repos use DocumentStore directly
    assert "store" in signature.parameters
    assert "version_index_repository" in signature.parameters
    assert "codec" in signature.parameters
    assert signature.parameters["store"].default is inspect.Parameter.empty
    assert signature.parameters["version_index_repository"].default is inspect.Parameter.empty
    assert signature.parameters["codec"].default is inspect.Parameter.empty

    source = inspect.getsource(repository_cls)
    assert "save_version_payload_and_index(" in source
    assert "BaseRepository" not in source
    assert "open(" not in source
    assert "json.dump" not in source
    assert "write_text" not in source

    helper_source = inspect.getsource(save_version_payload_and_index)
    assert "upsert_record(" in helper_source
    assert "upsert_records_atomic(" not in helper_source
    assert "AtomicWritePrecondition(" not in helper_source


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_service_receives_repository_by_constructor(domain_config):
    service_cls = domain_config["service_cls"]
    signature = inspect.signature(service_cls.__init__)

    assert "repository" in signature.parameters
    assert signature.parameters["repository"].default is inspect.Parameter.empty


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_router_resolves_service_from_container(domain_config):
    router_source = inspect.getsource(domain_config["router_module"])

    assert "Depends(_get_service)" in router_source
    assert f"app.state.container.{domain_config['container_service']}" in router_source
    assert "_service =" not in router_source


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_persistence_saves_payload_without_versions_index(domain_config, tmp_path):
    repository = _repository(domain_config, tmp_path)
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    payload = domain_config["payload_factory"](version_id, "base")

    assert repository.save_version(_summary(domain, version_id), payload) == version_id

    payload_path = tmp_path / domain / f"{version_id}.json"
    versions_path = tmp_path / domain / "versions.json"
    assert payload_path.exists()
    assert read_json(payload_path).get("version_id") == version_id
    assert not versions_path.exists()


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_duplicate_version_overwrites_payload(domain_config, tmp_path):
    repository = _repository(domain_config, tmp_path)
    domain = domain_config["domain"]
    version_id = f"{domain}-v1"
    first_payload = domain_config["payload_factory"](version_id, "primero")
    second_payload = domain_config["payload_factory"](version_id, "segundo")

    repository.save_version(_summary(domain, version_id), first_payload)
    repository.save_version(_summary(domain, version_id), second_payload)

    stored = read_json(tmp_path / domain / f"{version_id}.json")
    assert stored.get("version_id") == version_id
    assert not (tmp_path / domain / "versions.json").exists()


@pytest.mark.parametrize("domain_config", UPLOAD_DOMAINS)
def test_upload_two_versions_no_versions_index_written(domain_config, tmp_path):
    repository = _repository(domain_config, tmp_path)
    domain = domain_config["domain"]
    v1_id = f"{domain}-v1"
    v2_id = f"{domain}-v2"

    repository.save_version(_summary(domain, v1_id), domain_config["payload_factory"](v1_id, "primero"))
    repository.save_version(_summary(domain, v2_id), domain_config["payload_factory"](v2_id, "segundo"))

    assert (tmp_path / domain / f"{v1_id}.json").exists()
    assert (tmp_path / domain / f"{v2_id}.json").exists()
    assert not (tmp_path / domain / "versions.json").exists()
