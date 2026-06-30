"""Negative tests for cross-field validators in EntryDataV1."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from nexa_engine.modules.shared.contracts.api_v1 import EntryDataV1


def _base_panel(**overrides):
    panel = {
        "cliente": "Test",
        "linea_negocio": "Sac",
        "ciudad": "Bogotá",
        "sede": "Toberin",
        "fecha_inicio": "2026-01-01",
        "meses_contrato": 12,
        "margen": 0.2,
        "op_cont": 0.05,
        "com_cont": 0.0,
        "markup": 0.0,
        "descuento": 0.0,
        "periodo_pago_dias": 30,
    }
    panel.update(overrides)
    return panel


def test_explicit_empty_payload_infers_default_chain() -> None:
    """With no chain data, validator falls back to {"A"} so the engine still runs."""
    entry = EntryDataV1.model_validate({"panel_de_control": _base_panel()})
    assert entry.cadenas_activas == {"A"}


def test_meses_contrato_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        EntryDataV1.model_validate(
            {"panel_de_control": _base_panel(meses_contrato=0)}
        )
    with pytest.raises(ValidationError):
        EntryDataV1.model_validate(
            {"panel_de_control": _base_panel(meses_contrato=200)}
        )


def test_mes_ajuste_indexacion_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        EntryDataV1.model_validate(
            {"panel_de_control": _base_panel(mes_ajuste_indexacion=0)}
        )
    with pytest.raises(ValidationError):
        EntryDataV1.model_validate(
            {"panel_de_control": _base_panel(mes_ajuste_indexacion=13)}
        )


def test_margen_b_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        EntryDataV1.model_validate(
            {"panel_de_control": _base_panel(margen_b=1.5)}
        )


def test_unknown_panel_field_rejected_strict() -> None:
    with pytest.raises(ValidationError):
        EntryDataV1.model_validate(
            {"panel_de_control": _base_panel(unknown_field=123)}
        )


def test_escenario_unknown_canal_rejected() -> None:
    payload = {
        "panel_de_control": _base_panel(),
        "condiciones_cadena_a": {
            "perfiles": [
                {
                    "nombre": "P1",
                    "rol": "Agente Basico",
                    "canal": "Voz",
                    "modalidad": "Inbound",
                    "fte": 5.0,
                    "salario_base": 1750905.0,
                    "modelo_cobro": "Fijo FTE",
                }
            ]
        },
        "escenarios_comerciales": [
            {"nombre": "bad", "canal": "Chat", "modalidad": "Outbound"}
        ],
    }
    with pytest.raises(ValidationError):
        EntryDataV1.model_validate(payload)


def test_panel_nested_cadenas_activas_lifted() -> None:
    payload = {
        "panel_de_control": {
            **_base_panel(),
            "cadenas_activas": {"cadena_a": True, "cadena_b": True, "cadena_c": False},
        }
    }
    entry = EntryDataV1.model_validate(payload)
    assert entry.cadenas_activas == {"A", "B"}


def test_frozen_models_are_immutable() -> None:
    entry = EntryDataV1.model_validate({"panel_de_control": _base_panel()})
    with pytest.raises(ValidationError):
        entry.panel.cliente = "mutated"  # type: ignore[misc]
