"""Calculator-motor composition root for CostToServe results.

Ownership: calculator_motor (Block 20C).
CostToServeCalculator ahora vive en calculator_motor.
vision_cost_to_serve retiene solo: api/ (lectura), dto/ (contratos), helpers/.
"""
from __future__ import annotations

from typing import List, Optional

from nexa_engine.modules.shared.models import (
    ParametrosCadenaB,
    ParametrosCadenaC,
    PerfilCadenaA,
    PyGMensual,
    ResultadoCostToServe,
)
from nexa_engine.modules.calculator_motor.formulas.cts.calculator import CostToServeCalculator
from nexa_engine.modules.calculator_motor.formulas.cts.cts_facts import CostToServeFacts


def build_cost_to_serve_result(
    *,
    perfiles_cadena_a: List[PerfilCadenaA],
    parametros_cadena_b: ParametrosCadenaB,
    parametros_cadena_c: Optional[ParametrosCadenaC] = None,
    linea_negocio: str = "",
    cts_facts: Optional[CostToServeFacts] = None,
    pyg_por_mes: List[PyGMensual],
) -> ResultadoCostToServe:
    """Calculator-motor composition root for CostToServe results.

    Calculator-motor owns CTS formula implementation.
    """
    return CostToServeCalculator(
        perfiles_cadena_a,
        parametros_cadena_b,
        parametros_cadena_c=parametros_cadena_c,
        linea_negocio=linea_negocio,
        cts_facts=cts_facts,
    ).calcular(pyg_por_mes)
