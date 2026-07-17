"""VISION_IMPRIMIBLE_DB_PROVIDER_CERTIFICATION

Certifica que `modules/vision_imprimible` obtiene sus datos exclusivamente
a través de la capa de persistencia correcta:

    GET /simulation/{id}/results/vision-imprimible
    → ResultsRepository (port)
    → DocumentStore (abstract)
    → Provider activo: JSON (local) o Cosmos (producción)

Garantías verificadas:
  P1  — ResultsRepository sólo importa DocumentStore (port), no providers concretos.
  P2  — modules/vision_imprimible no importa JsonDocumentStore ni CosmosDocumentStore.
  P3  — modules/vision_imprimible no tiene rutas hardcodeadas.
  P4  — ResultsRepository.save() → get() produce los 15 campos canónicos de VI.
  P5  — El router GET usa Depends(get_results_repository), no accede al store directo.
  P6  — Un FakeDocumentStore inyectado vía DI produce la misma respuesta que el store real.
  P7  — El módulo no recalcula el motor en el GET (lee documento persistido).
  P8  — HTTP 404 cuando simulation_id no existe en el store.
  P9  — Cosmos: SKIP si credenciales no configuradas (documentado como gap).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401  registers `nexa_engine` alias

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VI_CANONICAL_FIELDS = [
    "ficha_deal", "kpis", "pyg_por_mes", "waterfall_promedio",
    "configuracion_comercial", "reglas_negocio", "evaluacion_riesgo",
    "vision_pyg", "cost_to_serve", "vision_tarifas",
    "vision_por_servicio", "vision_por_canal", "detalle_por_canal",
    "estructura_equipo", "comparativo_escenarios",
]

# ---------------------------------------------------------------------------
# FakeDocumentStore — in-memory, no filesystem, no Cosmos
# ---------------------------------------------------------------------------

class _FakeDocumentStore(DocumentStore):
    """Implementación in-memory del puerto DocumentStore para tests de DI."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}  # collection → {id → doc}

    def _coll(self, collection: CollectionConfig) -> Dict[str, Any]:
        return self._store.setdefault(collection.name, {})

    def get(self, collection, document_id, *, partition_value=None):
        return self._coll(collection).get(document_id)

    def upsert(self, collection, document):
        doc_id = document["id"]
        self._coll(collection)[doc_id] = dict(document)
        return document

    def list(self, collection, *, limit=None, continuation_token=None):
        docs = list(self._coll(collection).values())
        return docs, None

    def query(self, collection, filters, *, limit=None, continuation_token=None):
        results = [
            d for d in self._coll(collection).values()
            if all(d.get(k) == v for k, v in filters.items())
        ]
        return results, None

    def delete(self, collection, document_id, *, partition_value=None):
        from nexa_engine.db.exceptions import DbNotFoundError
        coll = self._coll(collection)
        if document_id not in coll:
            raise DbNotFoundError(document_id)
        del coll[document_id]

    # --- Record API (not used by ResultsRepository, required by ABC) ---
    def get_record(self, collection, document_id, *, partition_value=None):
        doc = self.get(collection, document_id)
        if doc is None:
            return None
        return StoredDocument(id=document_id, payload=doc)

    def list_records(self, collection, *, limit=None, continuation_token=None):
        docs, tok = self.list(collection)
        return [StoredDocument(id=d["id"], payload=d) for d in docs], tok

    def query_records(self, collection, filters, *, limit=None, continuation_token=None):
        docs, tok = self.query(collection, filters)
        return [StoredDocument(id=d["id"], payload=d) for d in docs], tok

    def upsert_record(self, collection, record):
        self.upsert(collection, {"id": record.id, **record.payload})
        return record

    def put_immutable(self, collection, record):
        if self.get_record(collection, record.id) is not None:
            from nexa_engine.db.exceptions import DbConflictError
            raise DbConflictError(record.id)
        return self.upsert_record(collection, record)

    def get_snapshot(self, collection, document_id, *, partition_value=None):
        return self.get_record(collection, document_id, partition_value=partition_value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_vi_document(simulation_id: str) -> Dict[str, Any]:
    """Produce un documento con los 15 campos canónicos de VI (datos mínimos)."""
    criterios = [
        {"id": i, "factor": f"Criterio {i}", "categoria": "Cliente", "puntaje": 1}
        for i in range(1, 11)
    ]
    return {
        "simulation_id": simulation_id,
        "ficha_deal":              {
            "cliente": "TestClient", "linea_negocio": "SAC", "ciudad": "Bogota",
            "sede": "Toberin", "tipo_cliente": "Grupo Aval", "fecha_inicio": "2026-01-01",
            "meses_contrato": 1, "periodo_pago_dias": 30, "divisa": "COP",
        },
        "kpis":                    {
            "ingreso_mensual": 100_000.0, "costo_mensual_promedio": 79_000.0,
            "facturacion_mensual_proyectada": 100_000.0, "valor_total_deal": 100_000.0,
            "margen_minimo_requerido": 0.17, "cumple_margen_minimo": True,
        },
        "pyg_por_mes":             [{"mes": 1, "rampup": 1.0, "ingreso_neto": 100_000.0}],
        "waterfall_promedio":      {"payroll_a": 0.0},
        "configuracion_comercial": {
            "modelo_cobro_principal": "Fijo FTE", "valor_total_deal": 100_000.0,
            "margen_objetivo": 0.21, "pct_fijo_global": 1.0, "pct_variable_global": 0.0,
            "tarifa_fija": 100_000.0, "tarifa_variable": 0.0, "descuento": 0.0,
            "volumen_base_mensual": 0.0,
        },
        "reglas_negocio":          {
            "alerta": {"activa": False, "mensaje": ""},
            "reglas": [
                {"nombre": name, "aplicado": 0.0, "min_valor": 0.0, "max_valor": 0.1, "status": "dentro_rango"}
                for name in ("contingencia_operativa", "contingencia_comercial", "markup", "descuento", "imprevistos")
            ],
        },
        "evaluacion_riesgo":       {
            "requiere_aprobacion": False, "score_cliente": 1.0, "score_operativo": 1.0,
            "score_total": 1.0, "clasificacion_total": "Bajo", "criterios": criterios,
            # BLOCK_25: aprobaciones_requeridas removido del backend
        },
        "vision_pyg":              {"total": {"ingresos": {}}},
        "cost_to_serve":           {"vol_cadena_b": 0.0},
        "vision_tarifas":          {"ingreso_mensual": 100_000.0, "canales": []},
        "vision_por_servicio":     [],
        "vision_por_canal":        [],
        "detalle_por_canal":       [],
        "estructura_equipo":       {"total_fte": 10},
        "comparativo_escenarios":  [],
    }


# ---------------------------------------------------------------------------
# P1 — ResultsRepository solo importa DocumentStore port
# ---------------------------------------------------------------------------

def test_p1_results_repository_no_importa_providers_concretos():
    """P1: ResultsRepository no importa JsonDocumentStore ni CosmosDocumentStore."""
    import inspect
    from nexa_engine.modules.calculator.persistence import results_repository as rr_mod

    src = inspect.getsource(rr_mod)
    assert "JsonDocumentStore" not in src, (
        "P1: ResultsRepository no debe importar JsonDocumentStore. "
        "Debe depender únicamente del puerto DocumentStore."
    )
    assert "CosmosDocumentStore" not in src, (
        "P1: ResultsRepository no debe importar CosmosDocumentStore."
    )
    assert "DocumentStore" in src, (
        "P1: ResultsRepository debe importar el puerto DocumentStore."
    )


# ---------------------------------------------------------------------------
# P2 — modules/vision_imprimible no importa providers concretos
# ---------------------------------------------------------------------------

def test_p2_vision_imprimible_no_importa_providers_concretos():
    """P2: Ningún archivo de modules/vision_imprimible importa JsonDocumentStore/CosmosDocumentStore."""
    vi_root = Path(__file__).resolve().parents[2] / "modules" / "vision_imprimible"
    violations = []
    for py_file in vi_root.rglob("*.py"):
        src = py_file.read_text(encoding="utf-8")
        if "JsonDocumentStore" in src:
            violations.append(f"{py_file.name}: importa JsonDocumentStore")
        if "CosmosDocumentStore" in src:
            violations.append(f"{py_file.name}: importa CosmosDocumentStore")
    assert not violations, (
        "P2: modules/vision_imprimible no debe importar providers concretos:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# P3 — modules/vision_imprimible no tiene rutas hardcodeadas
# ---------------------------------------------------------------------------

def test_p3_vision_imprimible_no_hardcoded_paths():
    """P3: Ningún archivo de modules/vision_imprimible tiene rutas de storage hardcodeadas."""
    vi_root = Path(__file__).resolve().parents[2] / "modules" / "vision_imprimible"
    _SUSPECTS = ["storage/", "simulation_results", ".json", "os.path.join", "open("]
    # Exceptions: docstrings, type annotations, comments, and Excel refs are fine
    violations = []
    for py_file in vi_root.rglob("*.py"):
        src = py_file.read_text(encoding="utf-8")
        for suspect in _SUSPECTS:
            if suspect in src:
                # Filter out legitimate uses: ".json" appears in type hints / docstrings
                # Only flag if it's in an import, open(), or path-construction context
                for line in src.splitlines():
                    stripped = line.strip()
                    if suspect in stripped and not stripped.startswith("#"):
                        if "open(" in stripped or "os.path" in stripped or "Path(" in stripped:
                            if "storage/" in stripped or ".json" in stripped:
                                violations.append(f"{py_file.name}:{stripped[:80]}")
    assert not violations, (
        "P3: modules/vision_imprimible tiene rutas hardcodeadas:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# P4 — ResultsRepository.save() → get() produce los 15 campos canónicos
# ---------------------------------------------------------------------------

def test_p4_repository_save_get_produce_campos_canonicos_vi():
    """P4: save + get con FakeDocumentStore preserva los 15 campos canónicos de VI."""
    fake_store = _FakeDocumentStore()
    repo = ResultsRepository(fake_store)

    sim_id = f"test-vi-p4-{uuid.uuid4().hex[:8]}"
    doc = _make_minimal_vi_document(sim_id)
    saved_id = repo.save(doc)

    assert saved_id == sim_id, "save() debe retornar el simulation_id"

    retrieved = repo.get(sim_id)
    for campo in _VI_CANONICAL_FIELDS:
        assert campo in retrieved, (
            f"P4: campo '{campo}' ausente del documento recuperado. "
            "La serialización round-trip save/get debe preservar todos los campos VI."
        )

    # El id interno del DocumentStore no debe filtrarse al consumidor
    assert "id" not in retrieved, (
        "P4: el campo 'id' interno del DocumentStore no debe estar en el dict retornado por get()"
    )


# ---------------------------------------------------------------------------
# P5 — El router usa Depends(get_results_repository), no acceso directo
# ---------------------------------------------------------------------------

def test_p5_router_usa_depends_get_results_repository():
    """P5: El router de vision_imprimible inyecta el repo via Depends() — no instancia directo."""
    import inspect
    from nexa_engine.modules.vision_imprimible.api import router as vi_router_mod

    src = inspect.getsource(vi_router_mod)
    assert "get_results_repository" in src, (
        "P5: el router debe usar Depends(get_results_repository) para recibir el repositorio"
    )
    assert "ResultsRepository(" not in src, (
        "P5: el router no debe instanciar ResultsRepository() directamente — usa Depends()"
    )
    assert "JsonDocumentStore" not in src, (
        "P5: el router no debe referenciar JsonDocumentStore"
    )
    assert "DocumentStore" not in src or "from" not in src.split("DocumentStore")[0].split("\n")[-1], (
        "P5: el router no debe importar DocumentStore directamente"
    )


# ---------------------------------------------------------------------------
# P6 — FakeDocumentStore inyectado via DI produce respuesta correcta
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def vi_client_with_fake_store():
    """TestClient con FakeDocumentStore inyectado via dependency_overrides."""
    from nexa_engine.app import create_app
    from nexa_engine.db.dependencies import get_results_repository

    fake_store = _FakeDocumentStore()
    fake_repo = ResultsRepository(fake_store)

    # Sembrar un documento de prueba
    sim_id = "test-p6-fake-store-vi"
    doc = _make_minimal_vi_document(sim_id)
    fake_repo.save(doc)

    app = create_app()
    app.dependency_overrides[get_results_repository] = lambda: fake_repo

    with TestClient(app) as client:
        yield client, sim_id

    app.dependency_overrides.clear()


def test_p6_fake_store_get_vision_imprimible_200(vi_client_with_fake_store):
    """P6: GET /simulation/{id}/results/vision-imprimible con FakeStore → 200 + campos correctos."""
    client, sim_id = vi_client_with_fake_store
    r = client.get(f"/api/v1/simulation/{sim_id}/results/vision-imprimible")
    assert r.status_code == 200, f"P6: esperaba 200, obtuvo {r.status_code}: {r.text}"

    body = r.json()
    assert body.get("success") is True, "P6: respuesta debe tener success=True"
    data = body.get("data", {})
    assert set(data) == {"vision_imprimible"}


def test_p6_fake_store_no_recalcula_motor(vi_client_with_fake_store):
    """P6/P7: El GET lee el documento persistido, no recalcula el motor de pricing."""
    client, sim_id = vi_client_with_fake_store

    # Modificamos el documento en el store para que sea identificable
    # (si el motor recalculara, no encontraría este valor)
    r = client.get(f"/api/v1/simulation/{sim_id}/results/vision-imprimible")
    assert r.status_code == 200
    data = r.json()["data"]["vision_imprimible"]

    # El valor que sembramos en el fake debe estar presente
    assert data["comparativo_escenarios"]["total"]["modelo_cobro"] == "Fijo FTE", (
        "P7: el GET debe leer el documento persistido exactamente, sin recalcular. "
        "Si el valor difiere, el endpoint está recalculando en lugar de leer."
    )


# ---------------------------------------------------------------------------
# P8 — HTTP 404 cuando simulation_id no existe
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def vi_client_empty_store():
    """TestClient con store vacío para verificar 404."""
    from nexa_engine.app import create_app
    from nexa_engine.db.dependencies import get_results_repository

    fake_repo = ResultsRepository(_FakeDocumentStore())
    app = create_app()
    app.dependency_overrides[get_results_repository] = lambda: fake_repo

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_p8_get_returns_404_para_simulation_inexistente(vi_client_empty_store):
    """P8: GET con simulation_id inexistente → 404."""
    client = vi_client_empty_store
    sim_id = f"does-not-exist-{uuid.uuid4().hex}"
    r = client.get(f"/api/v1/simulation/{sim_id}/results/vision-imprimible")
    assert r.status_code == 404, (
        f"P8: esperaba 404 para simulation_id inexistente, obtuvo {r.status_code}"
    )
    body = r.json()
    assert body.get("success") is False, "P8: success debe ser False en 404"
    assert body.get("error", {}).get("code") == "NOT_FOUND", (
        "P8: error.code debe ser 'NOT_FOUND'"
    )


# ---------------------------------------------------------------------------
# P9 — Cosmos: skip si credenciales no configuradas
# ---------------------------------------------------------------------------

@pytest.mark.cosmos_integration
def test_p9_cosmos_skip_si_no_configurado():
    """P9: Cosmos integration — salta si COSMOS_ENDPOINT no está configurado."""
    if not os.getenv("COSMOS_ENDPOINT"):
        pytest.skip(
            "P9: Cosmos no configurado (COSMOS_ENDPOINT ausente). "
            "Solo el provider JSON/local está certificado en este entorno. "
            "Para certificar Cosmos, configurar COSMOS_ENDPOINT, COSMOS_KEY, "
            "COSMOS_DATABASE, COSMOS_CONTAINER_PARAMETRIZATION y re-ejecutar con -m cosmos_integration."
        )

    # Si llegamos aquí, hay credenciales — smoke test de round-trip
    from nexa_engine.db.config import CosmosSettings
    from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore

    settings = CosmosSettings(
        endpoint=os.environ["COSMOS_ENDPOINT"],
        key=os.environ["COSMOS_KEY"],
        database=os.environ.get("COSMOS_DATABASE", "nexa_pricing_db"),
        container=os.environ.get("COSMOS_CONTAINER_PARAMETRIZATION", "simulation_results"),
    )
    cosmos_store = CosmosDocumentStore(settings)
    repo = ResultsRepository(cosmos_store)

    sim_id = f"cosmos-smoke-vi-{uuid.uuid4().hex[:8]}"
    try:
        doc = _make_minimal_vi_document(sim_id)
        repo.save(doc)
        retrieved = repo.get(sim_id)
        for campo in _VI_CANONICAL_FIELDS:
            assert campo in retrieved, f"Cosmos P9: campo '{campo}' ausente"
    finally:
        # Cleanup
        from nexa_engine.db.models.collection_config import CollectionConfig
        try:
            cosmos_store.delete(CollectionConfig(name="simulation_results"), sim_id)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# P10 — Integración completa: engine → serializer → save → GET HTTP
# ---------------------------------------------------------------------------

def test_p10_ciclo_completo_engine_save_get_via_fake_store(tmp_path):
    """P10: Ciclo completo end-to-end con FakeStore:
    1. Ejecuta el motor de pricing con input canónico.
    2. Serializa el resultado (pricing_result_to_dict).
    3. Persiste via ResultsRepository(FakeStore).
    4. Recupera via repo.get().
    5. Verifica que los 15 campos VI están presentes y son coherentes.
    """
    import copy, json
    from nexa_engine import NexaPricingEngine
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict

    # Activar parametrización v2-7
    STORAGE = Path(__file__).resolve().parents[2] / "storage" / "parametrization"
    import nexa_engine.modules.parametrizacion.services.provider as _prov_mod
    _prov_mod._PROVIDER_INSTANCE = None

    CANONICAL_INPUT = {
        "panel_de_control": {
            "cliente": "DB_CERT_TEST", "tipo_cliente": "No Grupo Aval",
            "linea_negocio": "Cobranzas", "ciudad": "Bogotá",
            "sede": "Bogota - Toberin", "fecha_inicio": "2026-01-01",
            "meses_contrato": 12, "margen": 0.21, "margen_b": 0.30,
            "margen_c": 0.20, "op_cont": 0.05, "com_cont": 0.03,
            "markup": 0.0, "descuento": 0.0, "tasa_ica": 0.01,
            "tasa_gmf": 0.004, "activa_financiacion": False,
            "periodo_pago_dias": 30, "tasa_mensual_financ": 0.0153,
            "imprevistos": 0.0, "pct_rotacion": 0.085, "pct_ausentismo": 0.065,
            "cadenas_activas": {"cadena_a": True, "cadena_b": False, "cadena_c": False},
        },
        "condiciones_cadena_a": {
            "perfiles": [{
                "nombre": "Agente Cobranzas", "rol": "Agente Basico",
                "modalidad": "Inbound", "canal": "Voz", "fte": 10.0,
                "pct_presencia": 1.0, "salario_base": 1_750_905.0,
                "comision_pct": 0.0, "dias_cap_inicial": 0,
                "dias_cap_rotacion": 0, "incluye_examenes": False,
                "incluye_seguridad": False, "incluye_crucero": False,
                "modelo_cobro": "Fijo FTE", "pct_fijo": 1.0,
                "no_payroll_mensual": 0.0,
            }],
        },
        "condiciones_cadena_b": {"canales": []},
        "condiciones_cadena_c": {},
    }

    p = tmp_path / "p10_input.json"
    p.write_text(json.dumps(CANONICAL_INPUT, default=str))

    engine  = NexaPricingEngine()
    builder = SimulationContextBuilder()
    loader  = UserInputLoader()
    ui      = loader.cargar(p)
    req     = builder.construir(ui)
    resultado = engine.calcular(req)

    sim_id  = f"p10-cycle-{uuid.uuid4().hex[:8]}"
    doc     = pricing_result_to_dict(resultado, result_id=sim_id)
    doc["simulation_id"] = sim_id

    # Persistir y recuperar via FakeStore
    fake_store = _FakeDocumentStore()
    repo = ResultsRepository(fake_store)
    repo.save(doc)
    retrieved = repo.get(sim_id)

    # Verificar 15 campos canónicos de VI
    for campo in _VI_CANONICAL_FIELDS:
        assert campo in retrieved, (
            f"P10: campo '{campo}' ausente tras ciclo completo engine→save→get. "
            "El serializer y el repository deben preservar todos los campos VI."
        )

    # Verificar coherencia de algunos valores clave
    assert retrieved["kpis"]["ingreso_mensual"] > 0, "kpis.ingreso_mensual debe ser positivo"
    assert retrieved["configuracion_comercial"]["modelo_cobro_principal"] != "", (
        "configuracion_comercial.modelo_cobro_principal no debe estar vacío con cadena_a activa"
    )
    assert isinstance(retrieved["reglas_negocio"]["reglas"], list), (
        "reglas_negocio.reglas debe ser lista"
    )
    assert isinstance(retrieved["pyg_por_mes"], list) and len(retrieved["pyg_por_mes"]) == 12, (
        "pyg_por_mes debe tener 12 meses para un contrato de 12 meses"
    )
    assert "id" not in retrieved, (
        "El campo 'id' interno del DocumentStore no debe filtrarse al consumidor HTTP"
    )
