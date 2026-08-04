from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, model_validator


class CalculationRequestV2(BaseModel):
    """Request para el motor de cálculo v2.

    Acepta el body completo del simulador (request.json) directamente.
    El campo `user_input` puede recibir el objeto plano o envuelto.
    """

    user_input: Dict[str, Any]
    id_draft: Optional[str] = None
    client_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def auto_wrap(cls, values: Any) -> Any:
        """Si el body es plano (no tiene user_input), lo envuelve automáticamente.

        Extrae id_draft y client_id antes de envolver para que no queden
        sepultados dentro de user_input.
        """
        if isinstance(values, dict) and "user_input" not in values:
            id_draft = values.pop("id_draft", None)
            client_id = values.pop("client_id", None)
            wrapped: Dict[str, Any] = {"user_input": values}
            if id_draft is not None:
                wrapped["id_draft"] = id_draft
            if client_id is not None:
                wrapped["client_id"] = client_id
            return wrapped
        return values
