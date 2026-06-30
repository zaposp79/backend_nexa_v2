"""Contract tests for the public screen-ready vision_imprimible response."""
from __future__ import annotations

from copy import deepcopy

from nexa_engine.modules.calculator.api.results_router import get_results
from nexa_engine.modules.vision_imprimible.api.public_mapper import build_public_vision_imprimible
from nexa_engine.modules.vision_imprimible.api.response_models import VisionImprimibleDataV1
from nexa_engine.modules.vision_imprimible.api.router import get_vision_imprimible


def _persisted_result() -> dict:
    return {
        "simulation_id": "sim-typed-1",
        "vision_imprimible": {
            "ficha_deal": {
                "cliente": "Cliente A",
                "linea_negocio": "SAC",
                "ciudad": "Bogota",
                "sede": "Toberin",
                "tipo_cliente": "Grupo Aval",
                "antiguedad_cliente": "Cliente Antiguo",
                "fecha_inicio": "2026-07-01",
                "meses_contrato": 3,
                "periodo_pago_dias": 30,
                "ajuste_precio_tipo": "IPC",
                "ajuste_precio_tecnologico": "SMMLV",
                "ajuste_precio_frecuencia": "Anual",
                "divisa": "COP",
            },
            "kpis": {
                "costo_mensual_promedio": 75.0,
                "facturacion_mensual_proyectada": 100.0,
                "valor_total_deal": 300.0,
                "margen_minimo_requerido": 0.17,
                "cumple_margen_minimo": True,
                "ingreso_mensual": 100.0,
            },
            "pyg_por_mes": [
                {"mes": 1, "ingreso_neto": 90.0},
                {"mes": 2, "ingreso_neto": 100.0},
                {"mes": 3, "ingreso_neto": 105.0},
            ],
            "waterfall_promedio": {
                "contribucion": 30.0,
                "ingreso_neto": 100.0,
            },
            "configuracion_comercial": {
                "modelo_cobro_principal": "Variable",
                "pct_fijo_global": 0.0,
                "pct_variable_global": 1.0,
                "tarifa_fija": 0.0,
                "tarifa_variable": 10.0,
                "descuento": 0.0,
                "margen_objetivo": 0.21,
                "volumen_base_mensual": 1000.0,
                "ingreso_mensual": 100.0,
                "costo_mensual_total": 75.0,
                "valor_total_deal": 300.0,
            },
            "reglas_negocio": {
                "reglas": [
                    {"nombre": "contingencia_operativa", "aplicado": 0.05, "min_valor": 0.05, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "contingencia_comercial", "aplicado": 0.01, "min_valor": 0.01, "max_valor": 0.03, "status": "dentro_rango"},
                    {"nombre": "markup", "aplicado": 0.02, "min_valor": 0.02, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "descuento", "aplicado": 0.0, "min_valor": 0.0, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "imprevistos", "aplicado": 0.0, "min_valor": 0.0, "max_valor": 1.0, "status": "dentro_rango"},
                ]
            },
            "evaluacion_riesgo": {
                "score_cliente": 1.6,
                "score_operativo": 2.1,
                "score_total": 1.9,
                "clasificacion_total": "Medio",
                "requiere_aprobacion": True,
                "criterios": [{"id": 1, "factor": "Criterio 1", "categoria": "Cliente", "puntaje": 2}],
            },
            "comparativo_escenarios": [
                {"escenario": "Escenario 1", "modalidad_canal": "Inbound - Voz", "modelo_cobro": "Variable", "canales": "Voz"},
            ],
        },
        "vision_tarifas": {
            "canales": [
                {
                    "componente_fijo": "",
                    "pct_fijo": 0.0,
                    "componente_variable": "Transaccion",
                    "pct_variable": 1.0,
                    "tarifa_fijo_fte": 0.0,
                    "tarifa_variable": 10.0,
                }
            ]
        },
    }


def test_mapper_returns_new_screen_contract():
    result = build_public_vision_imprimible(_persisted_result()).model_dump(mode="json")

    assert set(result) == {"version", "simulation_id", "header", "summary_cards", "sections", "charts", "metadata"}
    assert result["version"] == "v1"


def test_model_validates_screen_contract():
    result = build_public_vision_imprimible(_persisted_result()).model_dump(mode="json")
    validated = VisionImprimibleDataV1.model_validate(result)

    assert validated.version == "v1"
    assert validated.header["cliente"] == "Cliente A"


def test_sections_hide_technical_blocks():
    result = build_public_vision_imprimible(_persisted_result()).model_dump(mode="json")
    serialized = str(result)

    for forbidden in (
        "vision_imprimible",
        "vision_pyg",
        "vision_tarifas",
        "cost_to_serve",
        "detalle_por_canal",
        "estructura_equipo",
    ):
        assert forbidden not in result
    assert "formula" not in serialized
    assert "excel_row" not in serialized


def test_routes_share_the_same_public_payload():
    persisted = _persisted_result()

    class Repo:
        def get(self, simulation_id):
            assert simulation_id == "sim-1"
            return persisted

    complete = get_results("sim-1", repo=Repo()).model_dump(mode="json")
    dedicated = get_vision_imprimible("sim-1", repo=Repo()).model_dump(mode="json")

    assert complete["data"] == dedicated["data"]


def test_missing_approval_actors_reported_without_inventing_people():
    persisted = deepcopy(_persisted_result())
    result = build_public_vision_imprimible(persisted).model_dump(mode="json")
    section_ids = {section["id"] for section in result["sections"]}

    assert "aprobaciones" not in section_ids
    assert "aprobaciones.elaborador_pricing" in result["metadata"]["missing_fields"]
