"""
FASE VISION_IMPRIMIBLE_3/4 — Tests de contrato: riesgo y contingencias.

Verifica:
  1. evaluacion_riesgo expone requiere_aprobacion en el documento persistido.
  2. evaluacion_riesgo expone criterios con riesgo_actual en el documento.
  3. reglas_negocio tiene bloque alerta (activa + mensaje).
  4. reglas_negocio.alerta.mensaje menciona Alta Dirección cuando requiere_aprobacion.
  5. Contingencias (op_cont, com_cont) ya estan serializadas en reglas_negocio.reglas.
  6. aprobaciones_requeridas NO está en el documento persistido (BLOCK_25 removal).
  7. Seccion 08 / firmantes: no existen en el documento (PRINT_ONLY_PLACEHOLDER).
  8. No regresion de comparativo_escenarios (FASE 1) ni ownership (FASE 2).
  9. Cost To Serve no fue tocado.

BLOCK_25: aprobaciones_requeridas removido del backend.
Product decision: Excel "aprobaciones" is only a manual signature area after printing.
"""
from __future__ import annotations

import pytest

from nexa_engine.modules.calculator_motor.serializers import (
    pricing_result_to_dict,
    pricing_result_to_visions_response,
)


# ---------------------------------------------------------------------------
# TAREA 7.1 — evaluacion_riesgo expone requiere_aprobacion (no tocado por BLOCK_25)
# ---------------------------------------------------------------------------

def test_evaluacion_riesgo_contiene_requiere_aprobacion(run_engine, canonical_input):
    """evaluacion_riesgo expone requiere_aprobacion como bool (no tocado por BLOCK_25)."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-aprov-er")

    er = doc.get("evaluacion_riesgo")
    assert er is not None, "evaluacion_riesgo ausente del documento persistido"
    assert "requiere_aprobacion" in er, (
        "REGRESION DE CONTRATO: evaluacion_riesgo debe exponer 'requiere_aprobacion'. "
        "Este campo deriva de RiesgoCalculator (reglas.py:223) con umbral 1000*SMMLV."
    )
    assert isinstance(er["requiere_aprobacion"], bool)


def test_evaluacion_riesgo_score_y_clasificacion_presentes(run_engine, canonical_input):
    """evaluacion_riesgo expone score_total y clasificacion_total."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-aprov-er2")

    er = doc["evaluacion_riesgo"]
    for campo in ("score_total", "score_cliente", "score_operativo", "clasificacion_total"):
        assert campo in er, f"evaluacion_riesgo debe tener '{campo}'"

    assert er["score_total"] >= 0.0
    assert er["clasificacion_total"] in ("Bajo", "Medio", "Alto")


def test_evaluacion_riesgo_criterios_con_riesgo_actual(run_engine, canonical_input):
    """Cada criterio de evaluacion_riesgo tiene riesgo_actual (alias de calificacion)."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-aprov-criterios")

    er = doc["evaluacion_riesgo"]
    criterios = er.get("criterios", [])
    assert len(criterios) == 10
    for c in criterios:
        assert "riesgo_actual" in c
        assert c["riesgo_actual"] == c["calificacion"]


def test_evaluacion_riesgo_en_visions_response(run_engine, canonical_input):
    """evaluacion_riesgo tambien esta en el POST response."""
    resultado = run_engine(canonical_input)
    response = pricing_result_to_visions_response(resultado, result_id="test-aprov-vr")

    vi = response["vision_imprimible"]
    assert "evaluacion_riesgo" in vi
    er = vi["evaluacion_riesgo"]
    assert "requiere_aprobacion" in er


# ---------------------------------------------------------------------------
# TAREA 7.2 — reglas_negocio tiene bloque alerta con aprobacion
# ---------------------------------------------------------------------------

def test_reglas_negocio_tiene_bloque_alerta(run_engine, canonical_input):
    """reglas_negocio serializado incluye bloque alerta con activa y mensaje."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-aprov-rn")

    rn = doc.get("reglas_negocio")
    assert rn is not None
    assert "alerta" in rn
    alerta = rn["alerta"]
    assert "activa" in alerta
    assert "mensaje" in alerta
    assert isinstance(alerta["activa"], bool)
    assert isinstance(alerta["mensaje"], str)


def test_reglas_negocio_alerta_coherente_con_requiere_aprobacion(run_engine, canonical_input):
    """alerta.activa coherente con evaluacion_riesgo.requiere_aprobacion."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-aprov-coh")

    er = doc["evaluacion_riesgo"]
    rn = doc["reglas_negocio"]
    alerta = rn["alerta"]

    if er["requiere_aprobacion"]:
        assert alerta["activa"] is True
        assert "Alta Dirección" in alerta["mensaje"]
    else:
        if alerta["activa"]:
            assert "Alta Dirección" not in alerta["mensaje"]


def test_reglas_negocio_tiene_reglas_y_base_monetaria(run_engine, canonical_input):
    """reglas_negocio incluye lista de reglas y bases monetarias."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-aprov-rn2")

    rn = doc["reglas_negocio"]
    assert "reglas" in rn
    assert isinstance(rn["reglas"], list)
    assert len(rn["reglas"]) > 0
    assert "costo_total" in rn
    assert "valor_total_deal" in rn
    assert rn["costo_total"] > 0
    assert rn["valor_total_deal"] > 0


# ---------------------------------------------------------------------------
# TAREA 7.3 — Contingencias ya serializadas
# ---------------------------------------------------------------------------

def test_contingencias_accesibles_desde_panel_serializado(run_engine, canonical_input):
    """op_cont, com_cont, markup ya estan en el campo 'panel' del documento."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-contingencias")

    panel_doc = doc.get("panel")
    assert panel_doc is not None
    assert "op_cont" in panel_doc
    assert "com_cont" in panel_doc
    assert "markup" in panel_doc
    assert panel_doc["op_cont"] >= 0.0
    assert panel_doc["com_cont"] >= 0.0


def test_reglas_negocio_reglas_tienen_label_y_status(run_engine, canonical_input):
    """Cada regla de negocio tiene label, status."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-reglas-labels")

    for regla in doc["reglas_negocio"]["reglas"]:
        assert "label" in regla
        assert "status" in regla
        assert regla["status"] in ("dentro_rango", "bajo_minimo", "excede_maximo")


# ---------------------------------------------------------------------------
# TAREA 7.4 — aprobaciones_requeridas removido del backend (BLOCK_25)
# ---------------------------------------------------------------------------

def test_aprobaciones_requeridas_no_existe_en_evaluacion_riesgo(run_engine, canonical_input):
    """BLOCK_25: evaluacion_riesgo.aprobaciones_requeridas ya no se persiste."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-block25-no-aprob")

    er = doc.get("evaluacion_riesgo")
    assert er is not None, "evaluacion_riesgo debe estar en el documento"
    assert "aprobaciones_requeridas" not in er, (
        "BLOCK_25: aprobaciones_requeridas no debe estar en evaluacion_riesgo. "
        "Product decision: Excel aprobaciones is only manual signature after printing."
    )


def test_aprobaciones_requeridas_no_existe_en_visions_response_ni_cts(run_engine, canonical_input):
    """BLOCK_25: aprobaciones_requeridas no debe aparecer en visions_response ni en cts."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-block25-no-aprob2")
    response = pricing_result_to_visions_response(resultado, result_id="test-block25-no-aprob3")

    cts = doc.get("cost_to_serve")
    if cts:
        assert "aprobaciones_requeridas" not in cts

    vi = response.get("vision_imprimible", {})
    er = vi.get("evaluacion_riesgo", {})
    assert "aprobaciones_requeridas" not in er, (
        "BLOCK_25: aprobaciones_requeridas no debe estar en visions_response"
    )


# ---------------------------------------------------------------------------
# TAREA 7.5 — Seccion 08 / firmantes: NO existen
# ---------------------------------------------------------------------------

_CAMPOS_FIRMANTES_NO_IMPLEMENTADOS = [
    "firmantes",
    "aprobadores",
    "seccion_08",
    "firma_gerencia_financiera",
    "firma_gerencia_general",
    "firma_alta_direccion",
]


@pytest.mark.parametrize("campo", _CAMPOS_FIRMANTES_NO_IMPLEMENTADOS)
def test_seccion_08_firmantes_no_existen_en_documento(run_engine, canonical_input, campo):
    """Seccion 08 / firmantes NO existen en el documento persistido.

    PRINT_ONLY_PLACEHOLDER: la sección de firmas en la Visión Imprimible es un
    espacio en blanco para firma física posterior a la impresión.
    """
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id=f"test-firmante-{campo}")

    assert campo not in doc, (
        f"PRINT_ONLY_PLACEHOLDER: '{campo}' fue agregado al documento "
        f"sin decisión de negocio sobre flujo de aprobación digital."
    )


# ---------------------------------------------------------------------------
# TAREA 7.6 — No regresion de fases anteriores
# ---------------------------------------------------------------------------

def test_no_regresion_comparativo_escenarios_fase1(run_engine, canonical_input):
    """GAP-VIS-1 sigue cerrado: comparativo_escenarios en doc y response."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-fase3-reg1")
    response = pricing_result_to_visions_response(resultado, result_id="test-fase3-reg1r")

    assert "comparativo_escenarios" in doc
    assert isinstance(doc["comparativo_escenarios"], list)
    assert "comparativo_escenarios" in response["vision_imprimible"]


def test_no_regresion_15_campos_get_endpoint_fase2(run_engine, canonical_input):
    """Los 15 campos del GET vision-imprimible siguen presentes en el documento."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-fase3-reg2")

    campos_requeridos = [
        "ficha_deal", "kpis", "pyg_por_mes", "waterfall_promedio",
        "configuracion_comercial", "reglas_negocio", "evaluacion_riesgo",
        "vision_pyg", "cost_to_serve", "vision_tarifas",
        "vision_por_servicio", "vision_por_canal", "detalle_por_canal",
        "estructura_equipo", "comparativo_escenarios",
    ]
    for campo in campos_requeridos:
        assert campo in doc, (
            f"REGRESION FASE 2: campo '{campo}' ausente del documento. "
            f"El GET /vision-imprimible no podra servir este campo."
        )


# ---------------------------------------------------------------------------
# TAREA 7.7 — Cost To Serve no fue tocado
# ---------------------------------------------------------------------------

def test_cost_to_serve_no_fue_modificado(run_engine, canonical_input):
    """cost_to_serve sigue siendo serializado correctamente sin campos espurios."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-fase3-cts")

    cts = doc.get("cost_to_serve")
    assert cts is not None
    assert isinstance(cts, dict)
    assert "aprobaciones_requeridas" not in cts
    assert "firmantes" not in cts
