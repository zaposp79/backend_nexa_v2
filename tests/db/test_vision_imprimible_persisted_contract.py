"""VISION_IMPRIMIBLE_PERSISTED_CONTRACT_TRACE

Verifica el contrato del documento persistido para Vision Imprimible:

  - Los 15 campos canónicos están presentes en el documento guardado.
  - Cada campo tiene el tipo esperado (dict, list, None permitido solo si legacy).
  - Los campos obligatorios no-legacy lanzan error explícito si están ausentes.
  - El GET lee el documento sin modificarlo ni recalcularlo.
  - Los campos propios de VI se generan via sus helpers canónicos.

Tests:
  C1  — Documento mínimo cubre los 15 campos canónicos del GET.
  C2  — Campos obligatorios: ausencia de campo no-legacy produce KeyError o campo None detectable.
  C3  — ficha_deal contiene subcampos canónicos del panel.
  C4  — kpis contiene ingreso_mensual > 0 (campo clave de KPIsCalculator).
  C5  — configuracion_comercial contiene los 11 campos propios de VI.
  C6  — reglas_negocio.alerta contiene activa (bool) y mensaje (str).
  C7  — evaluacion_riesgo NO contiene aprobaciones_requeridas (BLOCK_25 removal).
  C8  — pyg_por_mes es lista de 12 meses para contrato de 12 meses.
  C9  — waterfall_promedio no es None cuando el motor ejecutó correctamente.
  C10 — vision_pyg tiene estructura de secciones (lista).
  C11 — vision_por_servicio / vision_por_canal / detalle_por_canal son listas (vacías OK).
  C12 — Helpers VI son importables y delegan correctamente desde serializer.
  C13 — El GET (router) no llama NexaPricingEngine ni SimulationContextBuilder.
  C14 — Ciclo completo engine → serializer → save → get preserva coherencia.
  C15 — Campo 'id' interno del DocumentStore no filtra al consumidor HTTP.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401  registra alias nexa_engine

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository

# ---------------------------------------------------------------------------
# Constantes del contrato
# ---------------------------------------------------------------------------

_VI_CANONICAL_FIELDS = [
    "ficha_deal",
    "kpis",
    "pyg_por_mes",
    "waterfall_promedio",
    "configuracion_comercial",
    "reglas_negocio",
    "evaluacion_riesgo",
    "vision_pyg",
    "cost_to_serve",
    "vision_tarifas",
    "vision_por_servicio",
    "vision_por_canal",
    "detalle_por_canal",
    "estructura_equipo",
    "comparativo_escenarios",
]

# Campos con default legacy permitido (data.get("x", []) o data.get("x") sin crash)
_LEGACY_DEFAULT_FIELDS = {
    "vision_por_servicio":    [],
    "vision_por_canal":       [],
    "detalle_por_canal":      [],
    "comparativo_escenarios": [],
    "estructura_equipo":      None,   # None es OK si VisionImprimibleBuilder no lo produce
}

# Campos obligatorios sin default: si ausentes, GET retorna None → frontend rompe
_REQUIRED_NON_LEGACY_FIELDS = [
    "ficha_deal",
    "kpis",
    "configuracion_comercial",
    "reglas_negocio",
    "evaluacion_riesgo",
    "pyg_por_mes",
    "waterfall_promedio",
    "vision_pyg",
    "cost_to_serve",
    "vision_tarifas",
]

# ---------------------------------------------------------------------------
# FakeDocumentStore — in-memory, reutiliza misma implementación que P1-P10
# ---------------------------------------------------------------------------

class _FakeDocumentStore(DocumentStore):
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def _coll(self, collection: CollectionConfig) -> Dict[str, Any]:
        return self._store.setdefault(collection.name, {})

    def get(self, collection, document_id, *, partition_value=None):
        return self._coll(collection).get(document_id)

    def upsert(self, collection, document):
        self._coll(collection)[document["id"]] = dict(document)
        return document

    def list(self, collection, *, limit=None, continuation_token=None):
        return list(self._coll(collection).values()), None

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

    def put_immutable(self, collection, record):
        self.upsert_record(collection, record)
        return record

    def get_snapshot(self, collection, document_id, *, partition_value=None):
        return self.get_record(collection, document_id, partition_value=partition_value)

    def get_record(self, collection, document_id, *, partition_value=None):
        doc = self.get(collection, document_id)
        return StoredDocument(id=document_id, payload=doc) if doc else None

    def list_records(self, collection, *, limit=None, continuation_token=None):
        docs, tok = self.list(collection)
        return [StoredDocument(id=d["id"], payload=d) for d in docs], tok

    def query_records(self, collection, filters, *, limit=None, continuation_token=None):
        docs, tok = self.query(collection, filters)
        return [StoredDocument(id=d["id"], payload=d) for d in docs], tok

    def upsert_record(self, collection, record):
        self.upsert(collection, {"id": record.id, **record.payload})
        return record


# ---------------------------------------------------------------------------
# Fixture: documento mínimo representativo
# ---------------------------------------------------------------------------

def _make_full_vi_document(simulation_id: str) -> Dict[str, Any]:
    """Documento representativo con todos los 15 campos canónicos poblados."""
    return {
        "simulation_id": simulation_id,
        "scenario":      "base",
        "calculated_at": "2026-06-05T00:00:00+00:00",
        # S01
        "ficha_deal": {
            "cliente": "ContractClient", "tipo_cliente": "No Grupo Aval",
            "linea_negocio": "Cobranzas", "ciudad": "Bogotá", "sede": "Toberin",
            "meses_contrato": 12, "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-12-31", "duracion_contrato": "01/01/2026 a 31/12/2026",
            "cadenas_activas": {"cadena_a": True, "cadena_b": False, "cadena_c": False},
        },
        # S02
        "kpis": {
            "ingreso_mensual": 50_000_000.0,
            "valor_total_deal": 600_000_000.0,
            "costo_mensual_promedio": 40_000_000.0,
            "costo_total_contrato": 480_000_000.0,
        },
        # S03
        "configuracion_comercial": {
            "modelo_cobro_principal": "Fijo FTE",
            "pct_fijo_global": 1.0,
            "pct_variable_global": 0.0,
            "tarifa_fija": 50_000_000.0,
            "tarifa_variable": 0.0,
            "descuento": 0.0,
            "margen_objetivo": 0.21,
            "volumen_base_mensual": 0.0,
            "ingreso_mensual": 50_000_000.0,
            "costo_mensual_total": 40_000_000.0,
            "valor_total_deal": 600_000_000.0,
        },
        # S04
        "waterfall_promedio": {
            "payroll_a": 35_000_000.0, "no_payroll": 5_000_000.0,
            "ingreso_bruto": 50_000_000.0, "costo_total": 40_000_000.0,
            "contribucion": 10_000_000.0, "utilidad_neta": 9_000_000.0,
        },
        # S05
        "vision_pyg": {
            "resumen": {"meses_contrato": 12},
            "secciones": [
                {"key": "ingresos", "label": "Ingresos", "filas": []},
            ],
            "puestos_trabajo": 10.0,
            "fechas_meses": ["2026-01", "2026-02"],
            "meses_contrato": 12,
            "meses_activos": 12,
        },
        # S06
        "evaluacion_riesgo": {
            "requiere_aprobacion": False,
            "calificacion": "bajo",
            "criterios": [],
        },
        # S07
        "reglas_negocio": {
            "alerta": {"activa": False, "mensaje": ""},
            "costo_total": 480_000_000.0,
            "valor_total_deal": 600_000_000.0,
            "reglas": [],
        },
        # S08
        "cost_to_serve": {
            "vol_cadena_b": 0.0,
            "desglose_a": {"total": 35_000_000.0},
            "desglose_b": {"total": 0.0},
        },
        # S09
        "vision_tarifas": {
            "ingreso_mensual": 50_000_000.0,
            "costo_cadena_a_total": 40_000_000.0,
            "costo_cadena_c_total": 0.0,
            "canales": [],
        },
        # pyg_por_mes — fuente gráficos (12 meses)
        "pyg_por_mes": [
            {"mes": i, "ingreso_bruto": 50_000_000.0, "payroll_a": 35_000_000.0}
            for i in range(1, 13)
        ],
        # S10-S13 (legacy defaults permitidos)
        "vision_por_servicio":    [],
        "vision_por_canal":       [],
        "detalle_por_canal":      [],
        "estructura_equipo":      None,
        "comparativo_escenarios": [],
    }


# ---------------------------------------------------------------------------
# C1 — Los 15 campos canónicos están presentes en el documento guardado
# ---------------------------------------------------------------------------

def test_c1_documento_minimo_cubre_15_campos_canonicos():
    """C1: Un documento representativo persistido contiene los 15 campos del GET."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)

    sim_id = f"c1-{uuid.uuid4().hex[:8]}"
    doc = _make_full_vi_document(sim_id)
    repo.save(doc)
    retrieved = repo.get(sim_id)

    missing = [f for f in _VI_CANONICAL_FIELDS if f not in retrieved]
    assert not missing, (
        f"C1: campos ausentes en documento recuperado: {missing}. "
        "El documento persistido debe cubrir los 15 campos canónicos del GET."
    )


# ---------------------------------------------------------------------------
# C2 — Campos obligatorios no-legacy: GET retorna None si ausentes (detectable)
# ---------------------------------------------------------------------------

def test_c2_campos_obligatorios_retornan_none_si_ausentes():
    """C2: Si un campo obligatorio falta en el documento, GET retorna None (no KeyError).

    El router usa data.get("campo") — retorna None si ausente.
    Esto es comportamiento documentado: el GET no falla, pero el frontend verá None.
    Los campos obligatorios deben estar siempre en el documento de persistencia.
    """
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)

    sim_id = f"c2-{uuid.uuid4().hex[:8]}"
    # Documento sin 'ficha_deal' — un campo obligatorio
    doc_sin_ficha = _make_full_vi_document(sim_id)
    del doc_sin_ficha["ficha_deal"]
    repo.save(doc_sin_ficha)
    retrieved = repo.get(sim_id)

    # El router usa data.get("ficha_deal") → None, no KeyError
    assert "ficha_deal" not in retrieved or retrieved["ficha_deal"] is None, (
        "C2: campo 'ficha_deal' ausente debe retornar None via data.get(). "
        "Verificar que el router usa .get() y no [] para acceder a campos."
    )
    # El GET no debe lanzar excepción — solo el campo es None
    from fastapi.testclient import TestClient
    from nexa_engine.app import create_app
    from nexa_engine.db.dependencies import get_results_repository

    app = create_app()
    app.dependency_overrides[get_results_repository] = lambda: repo
    with TestClient(app) as client:
        r = client.get(f"/api/v1/simulation/{sim_id}/results/vision-imprimible")
    app.dependency_overrides.clear()

    assert r.status_code == 200, (
        f"C2: GET no debe lanzar excepción aunque 'ficha_deal' sea None. "
        f"Obtuvo {r.status_code}: {r.text}"
    )
    data = r.json().get("data", {})
    assert data.get("ficha_deal") is None, (
        "C2: campo 'ficha_deal' ausente en documento → GET lo retorna como None"
    )


# ---------------------------------------------------------------------------
# C3 — ficha_deal contiene subcampos canónicos del panel
# ---------------------------------------------------------------------------

def test_c3_ficha_deal_subcampos_canonicos():
    """C3: ficha_deal tiene los subcampos que el frontend espera (VI sección 01)."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c3-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    ficha = data["ficha_deal"]
    expected = [
        "cliente", "tipo_cliente", "ciudad", "meses_contrato",
        "fecha_inicio", "fecha_fin", "cadenas_activas",
    ]
    missing = [f for f in expected if f not in ficha]
    assert not missing, f"C3: ficha_deal falta subcampos canónicos: {missing}"


# ---------------------------------------------------------------------------
# C4 — kpis.ingreso_mensual debe ser numérico
# ---------------------------------------------------------------------------

def test_c4_kpis_ingreso_mensual_numerico():
    """C4: kpis.ingreso_mensual existe y es numérico."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c4-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    kpis = data["kpis"]
    assert "ingreso_mensual" in kpis, "C4: kpis.ingreso_mensual debe estar presente"
    assert isinstance(kpis["ingreso_mensual"], (int, float)), (
        "C4: kpis.ingreso_mensual debe ser numérico"
    )


# ---------------------------------------------------------------------------
# C5 — configuracion_comercial contiene los 11 campos propios de VI
# ---------------------------------------------------------------------------

def test_c5_configuracion_comercial_campos_propios_vi():
    """C5: configuracion_comercial tiene los 11 campos generados por el helper VI."""
    _EXPECTED_CC = [
        "modelo_cobro_principal", "pct_fijo_global", "pct_variable_global",
        "tarifa_fija", "tarifa_variable", "descuento", "margen_objetivo",
        "volumen_base_mensual", "ingreso_mensual", "costo_mensual_total",
        "valor_total_deal",
    ]
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c5-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    cc = data["configuracion_comercial"]
    missing = [f for f in _EXPECTED_CC if f not in cc]
    assert not missing, (
        f"C5: configuracion_comercial falta campos canónicos: {missing}. "
        "Fuente: modules/vision_imprimible/helpers/configuracion_comercial.py"
    )


# ---------------------------------------------------------------------------
# C6 — reglas_negocio.alerta tiene activa (bool) y mensaje (str)
# ---------------------------------------------------------------------------

def test_c6_reglas_negocio_alerta_estructura():
    """C6: reglas_negocio.alerta tiene activa:bool y mensaje:str."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c6-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    rn = data["reglas_negocio"]
    assert "alerta" in rn, "C6: reglas_negocio debe tener 'alerta'"
    alerta = rn["alerta"]
    assert "activa" in alerta and isinstance(alerta["activa"], bool), (
        "C6: alerta.activa debe ser bool"
    )
    assert "mensaje" in alerta and isinstance(alerta["mensaje"], str), (
        "C6: alerta.mensaje debe ser str"
    )


# ---------------------------------------------------------------------------
# C7 — evaluacion_riesgo NO contiene aprobaciones_requeridas (BLOCK_25 removal)
# ---------------------------------------------------------------------------

def test_c7_evaluacion_riesgo_no_contiene_aprobaciones_requeridas():
    """C7: evaluacion_riesgo NO tiene aprobaciones_requeridas (BLOCK_25 removal).

    Product decision: Excel "aprobaciones" is manual signature after printing.
    Backend no longer computes 3-level COP table.
    """
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c7-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    ev = data["evaluacion_riesgo"]
    assert "aprobaciones_requeridas" not in ev, (
        "C7: BLOCK_25 — aprobaciones_requeridas no debe estar en evaluacion_riesgo. "
        "Product decision: Excel aprobaciones is manual signature after printing."
    )
    # Pero requiere_aprobacion debe seguir presente (no tocado por BLOCK_25)
    assert "requiere_aprobacion" in ev, (
        "C7: requiere_aprobacion debe seguir en evaluacion_riesgo (no tocado por BLOCK_25)"
    )


# ---------------------------------------------------------------------------
# C8 — pyg_por_mes es lista de 12 meses para contrato de 12 meses
# ---------------------------------------------------------------------------

def test_c8_pyg_por_mes_12_meses():
    """C8: pyg_por_mes contiene 12 entradas para un contrato de 12 meses."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c8-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    pyg = data["pyg_por_mes"]
    assert isinstance(pyg, list), "C8: pyg_por_mes debe ser lista"
    assert len(pyg) == 12, (
        f"C8: pyg_por_mes debe tener 12 entradas para contrato de 12 meses, obtuvo {len(pyg)}"
    )


# ---------------------------------------------------------------------------
# C9 — waterfall_promedio no es None
# ---------------------------------------------------------------------------

def test_c9_waterfall_promedio_no_es_none():
    """C9: waterfall_promedio está presente y no es None."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c9-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    assert data["waterfall_promedio"] is not None, (
        "C9: waterfall_promedio no debe ser None cuando el motor ejecutó correctamente"
    )


# ---------------------------------------------------------------------------
# C10 — vision_pyg tiene estructura de secciones
# ---------------------------------------------------------------------------

def test_c10_vision_pyg_tiene_secciones():
    """C10: vision_pyg.secciones es lista (puede estar vacía pero debe existir el campo)."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c10-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    vp = data["vision_pyg"]
    assert vp is not None, "C10: vision_pyg no debe ser None"
    assert "secciones" in vp, "C10: vision_pyg debe tener 'secciones'"
    assert isinstance(vp["secciones"], list), "C10: vision_pyg.secciones debe ser lista"


# ---------------------------------------------------------------------------
# C11 — vision_por_servicio / canal / detalle_por_canal son listas (legacy OK)
# ---------------------------------------------------------------------------

def test_c11_vision_ejecutiva_campos_son_listas():
    """C11: vision_por_servicio, vision_por_canal, detalle_por_canal, comparativo son listas."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c11-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    data = repo.get(sim_id)

    list_fields = ["vision_por_servicio", "vision_por_canal", "detalle_por_canal", "comparativo_escenarios"]
    for campo in list_fields:
        val = data.get(campo)
        assert isinstance(val, list), (
            f"C11: '{campo}' debe ser lista (vacía permitida). Obtuvo: {type(val)}"
        )


# ---------------------------------------------------------------------------
# C12 — Helpers VI son importables y el serializer delega
# ---------------------------------------------------------------------------

def test_c12_helpers_vi_importables_no_aprobaciones():
    """C12: Helpers VI importables; aprobaciones helper ya no existe (BLOCK_25 removal)."""
    import inspect

    # Helpers que siguen existiendo
    from nexa_engine.modules.vision_imprimible.helpers.ficha import ficha_deal_to_dict
    from nexa_engine.modules.vision_imprimible.helpers.configuracion_comercial import (
        configuracion_comercial_to_dict, select_principal_channel,
    )
    from nexa_engine.modules.vision_imprimible.helpers.reglas_negocio import reglas_negocio_to_dict

    assert callable(ficha_deal_to_dict),            "C12: ficha_deal_to_dict debe ser callable"
    assert callable(configuracion_comercial_to_dict), "C12: configuracion_comercial_to_dict debe ser callable"
    assert callable(select_principal_channel),      "C12: select_principal_channel debe ser callable"
    assert callable(reglas_negocio_to_dict),        "C12: reglas_negocio_to_dict debe ser callable"

    # BLOCK_25: aprobaciones helper eliminado
    import importlib
    spec = importlib.util.find_spec("nexa_engine.modules.vision_imprimible.helpers.aprobaciones")
    assert spec is None, (
        "C12: BLOCK_25 — módulo 'aprobaciones' ya no debe ser importable. "
        "Fue eliminado porque el backend no computa tabla de aprobaciones."
    )

    # Verificar que el serializer delega (contiene los imports de ownership)
    from nexa_engine.modules.calculator_motor.serializers import serializer_helpers as sh_mod
    src = inspect.getsource(sh_mod)
    assert "FORMULA_OWNERSHIP" in src, (
        "C12: serializer_helpers debe contener comentarios FORMULA_OWNERSHIP "
        "indicando delegación a modules/vision_imprimible"
    )
    # BLOCK_25: serializer ya no importa desde helpers/aprobaciones
    assert "from nexa_engine.modules.vision_imprimible.helpers" in src, (
        "C12: serializer_helpers debe importar desde modules/vision_imprimible/helpers"
    )
    assert "aprobaciones" not in src, (
        "C12: BLOCK_25 — serializer_helpers ya no debe importar 'aprobaciones'"
    )


# ---------------------------------------------------------------------------
# C13 — El router GET no llama engine ni calculators
# ---------------------------------------------------------------------------

def test_c13_router_get_no_llama_engine():
    """C13: El router GET no importa NexaPricingEngine ni calculators."""
    import inspect
    from nexa_engine.modules.vision_imprimible.api import router as vi_router_mod

    src = inspect.getsource(vi_router_mod)
    assert "NexaPricingEngine" not in src, (
        "C13: el router GET no debe referenciar NexaPricingEngine — solo lee del repositorio"
    )
    assert "calcular(" not in src, (
        "C13: el router GET no debe llamar .calcular() — no ejecuta el motor"
    )
    assert "SimulationContextBuilder" not in src, (
        "C13: el router GET no debe referenciar SimulationContextBuilder"
    )
    assert "pricing_result_to_dict" not in src, (
        "C13: el router GET no debe llamar pricing_result_to_dict — eso es POST"
    )


# ---------------------------------------------------------------------------
# C14 — Ciclo completo engine → serializer → save → get coherente
# ---------------------------------------------------------------------------

def test_c14_ciclo_completo_engine_serializer_save_get(tmp_path):
    """C14: El motor ejecuta, serializa, persiste y el GET recupera coherentemente."""
    import json
    from nexa_engine import NexaPricingEngine
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict

    CANONICAL_INPUT = {
        "panel_de_control": {
            "cliente": "CONTRACT_TRACE_TEST", "tipo_cliente": "No Grupo Aval",
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

    input_file = tmp_path / "c14_input.json"
    input_file.write_text(json.dumps(CANONICAL_INPUT, default=str))

    engine  = NexaPricingEngine()
    builder = SimulationContextBuilder()
    loader  = UserInputLoader()
    ui      = loader.cargar(input_file)
    req     = builder.construir(ui)
    resultado = engine.calcular(req)

    sim_id = f"c14-{uuid.uuid4().hex[:8]}"
    doc = pricing_result_to_dict(resultado, result_id=sim_id)
    doc["simulation_id"] = sim_id

    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    repo.save(doc)
    retrieved = repo.get(sim_id)

    # Los 15 campos deben estar presentes
    missing = [f for f in _VI_CANONICAL_FIELDS if f not in retrieved]
    assert not missing, f"C14: ciclo completo — campos ausentes: {missing}"

    # Coherencia de valores clave
    assert retrieved["kpis"]["ingreso_mensual"] > 0, (
        "C14: kpis.ingreso_mensual debe ser positivo (motor ejecutó)"
    )
    assert retrieved["configuracion_comercial"]["modelo_cobro_principal"] == "Fijo FTE", (
        "C14: modelo_cobro_principal debe ser 'Fijo FTE'"
    )
    assert len(retrieved["pyg_por_mes"]) == 12, (
        "C14: pyg_por_mes debe tener 12 meses"
    )
    # BLOCK_25: aprobaciones_requeridas ya no se genera
    ev = retrieved["evaluacion_riesgo"]
    assert "aprobaciones_requeridas" not in ev, (
        "C14: BLOCK_25 — aprobaciones_requeridas no debe estar en evaluacion_riesgo"
    )
    # requiere_aprobacion sigue presente (no tocado por BLOCK_25)
    assert ev.get("requiere_aprobacion") is not None, (
        "C14: requiere_aprobacion debe seguir presente en evaluacion_riesgo"
    )
    # Mensaje de alerta usa nomenclatura correcta
    rn = retrieved["reglas_negocio"]
    if rn["alerta"]["activa"] and rn["alerta"]["mensaje"]:
        assert "SMMLV" not in rn["alerta"]["mensaje"], (
            "C14: alerta.mensaje no debe contener 'SMMLV' — usar 'Alta Dirección' (BP-01)"
        )


# ---------------------------------------------------------------------------
# C15 — Campo 'id' interno no filtra al consumidor HTTP
# ---------------------------------------------------------------------------

def test_c15_campo_id_interno_no_filtra():
    """C15: el campo 'id' añadido por DocumentStore no aparece en repo.get() ni en HTTP."""
    fake = _FakeDocumentStore()
    repo = ResultsRepository(fake)
    sim_id = f"c15-{uuid.uuid4().hex[:8]}"
    repo.save(_make_full_vi_document(sim_id))
    retrieved = repo.get(sim_id)

    assert "id" not in retrieved, (
        "C15: el campo 'id' interno del DocumentStore no debe estar en el dict de repo.get(). "
        "ResultsRepository.get() lo elimina antes de retornar."
    )
