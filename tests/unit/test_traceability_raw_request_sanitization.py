"""
Unit tests for TraceabilityWriter._sanitize_raw_request.

Validates F3 fix: raw_request persisted to simulation_traceability must not
contain full client/business payload (datos_operativos, panel_context, etc.).
"""
from __future__ import annotations

from nexa_engine.modules.audit.writer import TraceabilityWriter


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _full_request() -> dict:
    """Simulate a realistic body.user_input dict."""
    return {
        "panel_de_control": {
            "cliente": "Bancamia SAC",
            "tipo_cliente": "No Grupo Aval",
            "linea_negocio": "Cobranzas",
            "margen": 0.18,
            "op_cont": 0.025,
            "com_cont": 0.04,
            "meses_contrato": 12,
            "fecha_inicio": "2026-01-01",
            "ciudad": "Bogota",
        },
        "condiciones_cadena_a": {
            "perfiles": [
                {"nombre": "Agente Inbound", "fte": 50, "salario": 1_750_905},
                {"nombre": "Supervisor", "fte": 5, "salario": 3_200_000},
            ]
        },
        "condiciones_cadena_b": {
            "canales": [{"nombre": "WhatsApp", "volumen": 10_000}]
        },
        "condiciones_cadena_c": {
            "canales": [{"nombre": "IA Voice", "costo_unitario": 120}]
        },
        "datos_operativos": {
            "servicio": "Cobranzas Tempranas",
            "cufin": "BANCA-2026",
            "sede_combinada_costo_formacion": 0.03,
        },
        "escenarios_comerciales": [
            {"perfil": "Agente Inbound", "modelo_cobro": "Fijo FTE"}
        ],
        "metadata": {
            "mode": "normal",
            "parametrization_version": "op-v2026-05",
        },
    }


def _sanitize(raw: dict) -> dict:
    return TraceabilityWriter._sanitize_raw_request(raw)


# ────────────────────────────────────────────────────────────────────────────
# Core contract
# ────────────────────────────────────────────────────────────────────────────

def test_sanitized_flag_is_set():
    result = _sanitize(_full_request())
    assert result["_sanitized"] is True


def test_top_level_keys_preserved():
    raw = _full_request()
    result = _sanitize(raw)
    assert "top_level_keys" in result
    assert set(result["top_level_keys"]) == set(raw.keys())


def test_does_not_mutate_original():
    raw = _full_request()
    original_keys = set(raw.keys())
    _sanitize(raw)
    assert set(raw.keys()) == original_keys
    assert raw["panel_de_control"]["cliente"] == "Bancamia SAC"


# ────────────────────────────────────────────────────────────────────────────
# Business-sensitive sections must NOT be stored verbatim
# ────────────────────────────────────────────────────────────────────────────

def test_panel_de_control_values_not_persisted():
    result = _sanitize(_full_request())
    assert "panel_de_control" not in result, (
        "Full panel_de_control must not be stored in sanitized request"
    )
    # Client-identifying values must not appear
    assert "Bancamia SAC" not in str(result)


def test_condiciones_cadena_a_values_not_persisted():
    result = _sanitize(_full_request())
    assert "condiciones_cadena_a" not in result
    # No salary or FTE data
    assert "1750905" not in str(result)
    assert "salario" not in str(result).lower()


def test_condiciones_cadena_b_values_not_persisted():
    result = _sanitize(_full_request())
    assert "condiciones_cadena_b" not in result


def test_condiciones_cadena_c_values_not_persisted():
    result = _sanitize(_full_request())
    assert "condiciones_cadena_c" not in result


def test_datos_operativos_values_not_persisted():
    result = _sanitize(_full_request())
    assert "datos_operativos" not in result
    # Business values must not appear — field names (structural metadata) are fine
    assert "BANCA-2026" not in str(result)
    assert "Cobranzas Tempranas" not in str(result)


def test_escenarios_comerciales_values_not_persisted():
    result = _sanitize(_full_request())
    assert "escenarios_comerciales" not in result


# ────────────────────────────────────────────────────────────────────────────
# Shape metadata retained (for forensic traceability)
# ────────────────────────────────────────────────────────────────────────────

def test_panel_de_control_shape_retained():
    result = _sanitize(_full_request())
    assert "panel_de_control_keys" in result, (
        "panel_de_control_keys (shape info) must be retained for forensic traceability"
    )
    assert "margen" in result["panel_de_control_keys"]


def test_condiciones_cadena_a_shape_retained():
    result = _sanitize(_full_request())
    assert "condiciones_cadena_a_keys" in result


def test_escenarios_comerciales_count_retained():
    result = _sanitize(_full_request())
    assert "escenarios_comerciales_count" in result
    assert result["escenarios_comerciales_count"] == 1


# ────────────────────────────────────────────────────────────────────────────
# Safe metadata keys retained verbatim
# ────────────────────────────────────────────────────────────────────────────

def test_metadata_retained_verbatim():
    result = _sanitize(_full_request())
    assert "metadata" in result
    assert result["metadata"]["mode"] == "normal"
    assert result["metadata"]["parametrization_version"] == "op-v2026-05"


def test_parametrization_version_retained_if_present():
    raw = {"parametrization_version": "v2.8", "panel_de_control": {"cliente": "X"}}
    result = _sanitize(raw)
    assert result.get("parametrization_version") == "v2.8"


def test_no_metadata_key_absent_from_result_when_not_in_request():
    raw = {"panel_de_control": {"cliente": "X"}}
    result = _sanitize(raw)
    assert "metadata" not in result
    assert "parametrization_version" not in result


# ────────────────────────────────────────────────────────────────────────────
# Edge cases
# ────────────────────────────────────────────────────────────────────────────

def test_empty_request_returns_sanitized_flag():
    result = _sanitize({})
    assert result["_sanitized"] is True
    assert result["top_level_keys"] == []


def test_non_dict_input_is_handled():
    result = TraceabilityWriter._sanitize_raw_request("not_a_dict")  # type: ignore
    assert result["_sanitized"] is True
    assert "_type" in result


def test_request_without_sensitive_sections_preserves_shape():
    raw = {"metadata": {"mode": "normal"}}
    result = _sanitize(raw)
    assert result["_sanitized"] is True
    assert result["top_level_keys"] == ["metadata"]
    assert result["metadata"]["mode"] == "normal"


def test_full_client_payload_not_in_persisted_string():
    """Integration: persisted string representation must not contain business values."""
    raw = _full_request()
    result = _sanitize(raw)
    s = str(result)
    # None of the sensitive business values should appear
    assert "Bancamia SAC" not in s
    assert "Cobranzas Tempranas" not in s
    assert "BANCA-2026" not in s
    assert "1750905" not in s
