"""Request DTO for POST /api/v1/simulation/calculate."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, model_validator


class CalculationRequest(BaseModel):
    """
    Cuerpo de la solicitud de cálculo.

    `user_input` soporta dos formatos:

    **Formato legacy (test_cases):**
      - panel_de_control, condiciones_cadena_a/b/c

    **Formato entry_data:**
      - datos_operativos, polizas, reglas_negocio, volumetria,
        condiciones_cadena_a/b/c (se normaliza automáticamente)

    **Auto-envuelto (flat body):**
    Si el body llega SIN la clave ``user_input`` (e.g. el cliente envía el
    payload directamente como raíz del JSON), el validador lo detecta y lo
    envuelve automáticamente en ``{"user_input": <body>}``.  Esto evita el
    422 cuando el cliente envía un body plano.
    """
    user_input: Dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def _auto_wrap_flat_body(cls, data: Any) -> Any:
        """
        Acepta dos formas de request body:

          1. Canónica  → {"user_input": {...}}
          2. Plana     → {"datos_operativos": {...}, "polizas": [...], ...}

        Si no hay clave ``user_input``, todo el dict se trata como el valor
        de ``user_input`` (equivalente a que el cliente envuelva el payload).
        """
        if isinstance(data, dict) and "user_input" not in data:
            return {"user_input": data}
        return data


__all__ = ["CalculationRequest"]
