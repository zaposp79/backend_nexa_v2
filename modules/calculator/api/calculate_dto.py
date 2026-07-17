"""Request DTO for POST /api/v1/simulation/calculate."""

from __future__ import annotations

from typing import Any, Dict, Optional

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

    `id` es opcional. Cuando se envía, se persiste como ``id_draft`` en el
    documento Cosmos para vincular el resultado con el borrador de origen.
    """
    user_input: Dict[str, Any]
    id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _auto_wrap_flat_body(cls, data: Any) -> Any:
        """
        Acepta dos formas de request body:

          1. Canónica  → {"user_input": {...}, "id": "<draft_id>"}
          2. Plana     → {"datos_operativos": {...}, "polizas": [...], ...}

        Si no hay clave ``user_input``, todo el dict (excepto ``id``) se
        trata como el valor de ``user_input``. El campo ``id`` se extrae
        antes de envolver para que quede en el nivel correcto del modelo.
        """
        if isinstance(data, dict) and "user_input" not in data:
            id_val = data.get("id")
            user_input = {k: v for k, v in data.items() if k != "id"}
            result: Dict[str, Any] = {"user_input": user_input}
            if id_val is not None:
                result["id"] = id_val
            return result
        return data


__all__ = ["CalculationRequest"]
