from __future__ import annotations

from typing import List, Optional

from nexa_engine.modules.shared.models import (
    EscenarioComercial,
    PanelDeControl,
    ParametrosCadenaB,
    PerfilCadenaA,
    PyGMensual,
    ResultadoVisionTarifas,
)
from nexa_engine.modules.vision_tarifas.models.vt_facts import VisionTarifasFacts
from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator


def build_vision_tarifas_result(
    *,
    perfiles_cadena_a: List[PerfilCadenaA],
    parametros_cadena_b: ParametrosCadenaB,
    panel: PanelDeControl,
    pyg_por_mes: List[PyGMensual],
    vt_facts: Optional[VisionTarifasFacts] = None,
    escenarios: Optional[List[EscenarioComercial]] = None,
    strict_mode: bool = False,
    polizas_usuario: Optional[List] = None,
    calc_financiero: "Optional[object]" = None,
) -> ResultadoVisionTarifas:
    """Calculator-motor composition root for VisionTarifas results.

    Calculator-motor owns tariff result composition and formula implementation.
    """
    return VisionTarifasCalculator(
        perfiles_cadena_a,
        parametros_cadena_b,
        panel,
        vt_facts=vt_facts,
        escenarios=escenarios,
        strict_mode=strict_mode,
        polizas_usuario=polizas_usuario,
        calc_financiero=calc_financiero,
    ).calcular(pyg_por_mes)
