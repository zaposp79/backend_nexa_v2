"""
Evaluador de fórmulas para rubros maestro.

Las fórmulas son expresiones Python válidas definidas en Cosmos DB por el sistema
(no por usuarios finales). El namespace de evaluación se restringe a las variables
del contexto + funciones matemáticas seguras.
"""
from __future__ import annotations

import math
from typing import Any, Dict

_MATH_NAMESPACE: Dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "int": int,
    "float": float,
    "bool": bool,
    "len": len,
    "range": range,
    "ceil": math.ceil,
    "floor": math.floor,
    "sqrt": math.sqrt,
    "True": True,
    "False": False,
    "None": None,
}


def evaluate_formula(expresion: str, context: Dict[str, Any]) -> float:
    """Evalúa una expresión de rubro en el contexto dado.

    Retorna 0.0 en división por cero. Lanza ValueError si la expresión es inválida.
    """
    namespace = {**_MATH_NAMESPACE, **context}
    try:
        result = eval(expresion, {"__builtins__": {}}, namespace)  # noqa: S307
        if result is None:
            return 0.0
        return float(result)
    except ZeroDivisionError:
        return 0.0
    except Exception as exc:
        raise ValueError(f"Error evaluando fórmula '{expresion}': {exc}") from exc
