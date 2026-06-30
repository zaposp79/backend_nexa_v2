"""Input diagnostic helper for the calculate capability.

``validate_input`` checks a user_input payload without running the engine,
reporting exactly which section/field fails. Extracted verbatim from
calculate_router.py (FASE Y Batch 4b) — behaviour unchanged.
"""

from __future__ import annotations

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.calculator_motor.validation.contract_validator import ContractValidator

from nexa_engine.modules.calculator.api.calculate_dto import CalculationRequest


def validate_input(body: CalculationRequest):
    """
    Valida el user_input sin ejecutar el motor de cálculo.

    Útil para diagnosticar errores 422: reporta exactamente qué campo
    o sección falla la validación, sin incurrir en el costo de cálculo.

    ## Respuesta exitosa
    ```json
    {
      "valid": true,
      "secciones": {
        "panel_de_control": "OK",
        "condiciones_cadena_a": "OK — 2 perfil(es)",
        "condiciones_cadena_b": "OK — 1 canal(es)",
        "condiciones_cadena_c": "OK — 0 canal(es)"
      }
    }
    ```

    ## Respuesta con error
    ```json
    {
      "valid": false,
      "error_code": "PHASE55_VIOLATION",
      "error_message": "❌ PHASE 5.5 CONTRACT VIOLATION: ...",
      "keys_received": ["panel_de_control", "campo_invalido"],
      "keys_validos": ["panel_de_control", "condiciones_cadena_a", ...]
    }
    ```
    """
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import (
        _CAMPOS_ENTRY_DATA_NUEVO_VALIDOS,
        _CAMPOS_ENTRY_DATA_VALIDOS,
    )

    ui = body.user_input

    # ── Diagnóstico 1: campos desconocidos o pollution ───────────────────────
    pollution = sorted(k for k in ui.keys() if k.startswith("_"))
    campos_validos = (
        _CAMPOS_ENTRY_DATA_NUEVO_VALIDOS
        if "datos_operativos" in ui
        else _CAMPOS_ENTRY_DATA_VALIDOS
    )
    desconocidos = sorted(set(ui.keys()) - campos_validos)

    if pollution:
        return ApiResponse.ok({
            "valid": False,
            "error_code": "POLLUTION_FIELDS",
            "error_message": (
                "El payload contiene campos con prefijo '_' (metadata/debugging). "
                "Estos campos están prohibidos en el contrato entry_data."
            ),
            "campos_rechazados": pollution,
            "keys_recibidas": sorted(ui.keys()),
        })

    if desconocidos:
        return ApiResponse.ok({
            "valid": False,
            "error_code": "UNKNOWN_FIELDS",
            "error_message": (
                "El payload contiene campos no reconocidos por el contrato entry_data. "
                "Revisa los nombres de las secciones."
            ),
            "campos_desconocidos": desconocidos,
            "keys_recibidas": sorted(ui.keys()),
            "keys_validas": sorted(campos_validos),
        })

    if "datos_operativos" in ui:
        contract_result = ContractValidator().validate(ui)
        if not contract_result.is_valid:
            return ApiResponse.ok({
                "valid": False,
                "error_code": "CONTRACT_VALIDATION_ERROR",
                "error_message": "El contrato entry_data no cumple validaciones estrictas.",
                "errors": contract_result.errors,
                "warnings": contract_result.warnings,
                "keys_recibidas": sorted(ui.keys()),
            })

        try:
            user_input = UserInputLoader().cargar_desde_dict(ui)
            return ApiResponse.ok({
                "valid": True,
                "secciones": {
                    "datos_operativos": "OK",
                    "reglas_negocio": "OK",
                    "volumetria": "OK",
                    "condiciones_cadena_a": f"OK — {len(user_input.cadena_a.perfiles)} perfil(es)",
                    "condiciones_cadena_b": f"OK — {len(user_input.cadena_b.canales)} canal(es)",
                    "condiciones_cadena_c": f"OK — {len(user_input.cadena_c.canales)} canal(es)",
                },
                "nota": "Payload contractual válido. Si /calculate falla, revisar parametrización activa o auditoría.",
            })
        except (ValueError, KeyError) as exc:
            return ApiResponse.ok({
                "valid": False,
                "error_code": "PARSE_ERROR",
                "error_message": str(exc),
                "keys_recibidas": sorted(ui.keys()),
            })

    # ── Diagnóstico 2: panel_de_control requerido ────────────────────────────
    if "panel_de_control" not in ui:
        return ApiResponse.ok({
            "valid": False,
            "error_code": "MISSING_PANEL",
            "error_message": "Falta la sección requerida 'panel_de_control'.",
            "keys_recibidas": sorted(ui.keys()),
        })

    panel = ui["panel_de_control"]
    campos_requeridos_panel = ["cliente", "linea_negocio", "meses_contrato", "margen", "op_cont"]
    faltantes = [c for c in campos_requeridos_panel if c not in panel]
    if faltantes:
        return ApiResponse.ok({
            "valid": False,
            "error_code": "MISSING_PANEL_FIELDS",
            "error_message": f"panel_de_control le faltan campos requeridos: {faltantes}",
            "campos_faltantes": faltantes,
            "campos_recibidos": sorted(panel.keys()),
        })

    # ── Diagnóstico 3: intentar construir UserInput ──────────────────────────
    try:
        user_input = UserInputLoader().cargar_desde_dict(ui)
        n_perfiles = len(user_input.cadena_a.perfiles)
        n_b = len(user_input.cadena_b.canales)
        n_c = len(user_input.cadena_c.canales)
        return ApiResponse.ok({
            "valid": True,
            "secciones": {
                "panel_de_control":    f"OK — cliente={panel.get('cliente')!r} ciudad={panel.get('ciudad','Bogota')!r}",
                "condiciones_cadena_a": f"OK — {n_perfiles} perfil(es)",
                "condiciones_cadena_b": f"OK — {n_b} canal(es)",
                "condiciones_cadena_c": f"OK — {n_c} canal(es)",
            },
            "nota": "Payload válido. Si /calculate sigue fallando, el error es de parametrización activa.",
        })
    except (ValueError, KeyError) as exc:
        return ApiResponse.ok({
            "valid": False,
            "error_code": "PARSE_ERROR",
            "error_message": str(exc),
            "keys_recibidas": sorted(ui.keys()),
        })


__all__ = ["validate_input"]
