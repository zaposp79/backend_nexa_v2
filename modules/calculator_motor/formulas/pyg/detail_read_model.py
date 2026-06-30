"""Calculator-owned read model for Vision P&G detail rows."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

from nexa_engine.modules.shared.models import (
    PerfilCadenaA,
    PyGMensual,
    VisionPyGRowDetalle,
)

if TYPE_CHECKING:
    from nexa_engine.modules.cadena_b.reglas import CadenaBCalculator
    from nexa_engine.modules.cadena_c.reglas import CadenaCCalculator
    from nexa_engine.modules.calculator_motor.formulas.no_payroll import NoPayrollCalculator
    from nexa_engine.modules.calculator_motor.formulas.payroll import NominaCalculator


_DETALLE_PAYROLL_A: List[Tuple[str, str, str]] = [
    ("salario_fijo", "Salario Fijo", "salario_fijo"),
    ("salario_variable", "Salario Variable (Comisiones)", "comisiones"),
    ("cap_inicial", "Capacitación Inicial", "capacitacion_inicial"),
    ("cap_rotacion", "Capacitación Rotación", "capacitacion_rotacion"),
    ("examenes", "Exámenes Médicos", "examenes"),
    ("estudios_seguridad", "Estudios de Seguridad", "seguridad"),
    ("crucero", "Crucero", "crucero"),
]
_DETALLE_NO_PAYROLL_A: List[Tuple[str, str, str]] = [
    ("opex_fijo_a", "OPEX Fijo", "opex_ti"),
    ("inversiones_a", "Inversiones", "capex"),
    ("costos_fijos_a", "Costos Fijos", "costos_fijos"),
]
_DETALLE_B: List[Tuple[str, str, str]] = [
    ("opex_fijo_b", "OPEX Fijo", "opex_fijo"),
    ("inversiones_b", "Inversiones", "inversiones"),
    ("sm_b", "S&M", "soporte_mantenimiento"),
    ("tarifa_canal_b", "Tarifa Canal", "costo_variable"),
    ("tasa_escalamiento_b", "Tasa de Escalamiento", "escalamiento"),
    ("hitl_b", "HITL", "hitl"),
]
_DETALLE_C: List[Tuple[str, str, str]] = [
    ("tarifa_proveedor_c", "Tarifa Proveedor", "tarifa_proveedor"),
    ("opex_fijo_integ_c", "OPEX Fijo", "opex_fijo_integ"),
    ("inversiones_integ_c", "Inversiones", "inversiones"),
    ("equipo_integ_c", "Equipo de integración", "equipo_integ"),
    ("tasa_escalamiento_c", "Tasa de Escalamiento", "escalamiento"),
    ("opex_var_integ_c", "OPEX Variable", "opex_var_integ"),
    ("hitl_c", "HITL", "hitl"),
]
_FIN_CADENA: List[Tuple[str, str, str, str]] = [
    ("ica_a", "ICA Cadena A", "ica", "ica_a"),
    ("ica_c", "ICA Cadena C", "ica", "ica_c"),
    ("gmf_a", "GMF Cadena A", "gmf", "gmf_a"),
    ("gmf_c", "GMF Cadena C", "gmf", "gmf_c"),
    ("polizas_a", "Pólizas Cadena A", "polizas", "polizas_a"),
    ("polizas_b", "Pólizas Cadena B", "polizas", "polizas_b"),
    ("polizas_c", "Pólizas Cadena C", "polizas", "polizas_c"),
]


def build_pyg_detail_read_model(
    pyg_por_mes: List[PyGMensual],
    perfiles_cadena_a: Optional[List[PerfilCadenaA]] = None,
    calc_nomina: "Optional[NominaCalculator]" = None,
    calc_no_payroll: "Optional[NoPayrollCalculator]" = None,
    calc_cadena_b: "Optional[CadenaBCalculator]" = None,
    calc_cadena_c: "Optional[CadenaCCalculator]" = None,
) -> List[VisionPyGRowDetalle]:
    """
    Build the serializable detail rows consumed by Vision P&G.

    This function is owned by calculator_motor because it calls formula
    calculators per month. `modules/pyg` can later become a pure reader of the
    resulting rows.
    """
    n = len(pyg_por_mes)
    detalle: List[VisionPyGRowDetalle] = []
    if n == 0:
        return detalle

    perfiles = perfiles_cadena_a or []
    active_indices = [
        index for index, mes in enumerate(pyg_por_mes)
        if mes.ingreso_neto > 0
    ]

    nom_mes = (
        [calc_nomina.calcular_para_mes(perfiles, mes) for mes in range(1, n + 1)]
        if calc_nomina is not None else None
    )
    nop_mes = (
        [calc_no_payroll.calcular_para_mes(perfiles, mes) for mes in range(1, n + 1)]
        if calc_no_payroll is not None else None
    )
    b_mes = (
        [calc_cadena_b.calcular_para_mes(mes) for mes in range(1, n + 1)]
        if calc_cadena_b is not None else None
    )
    c_mes = (
        [calc_cadena_c.calcular_para_mes(mes) for mes in range(1, n + 1)]
        if calc_cadena_c is not None else None
    )

    def add_rows(
        specs: List[Tuple[str, str, str]],
        parent: str,
        seccion: str,
        results: Optional[list],
    ) -> None:
        if results is None:
            return
        for key, label, attr in specs:
            valores = [getattr(result, attr) for result in results]
            detalle.append(_detail_row(key, label, parent, seccion, valores, active_indices))

    add_rows(_DETALLE_PAYROLL_A, "payroll_a", "costos_op", nom_mes)
    add_rows(_DETALLE_NO_PAYROLL_A, "no_payroll_a", "costos_op", nop_mes)
    add_rows(_DETALLE_B, "costo_b", "costos_op", b_mes)
    add_rows(_DETALLE_C, "costo_c", "costos_op", c_mes)

    for key, label, parent, attr in _FIN_CADENA:
        valores = [getattr(mes, attr, 0.0) for mes in pyg_por_mes]
        detalle.append(_detail_row(key, label, parent, "costos_fin", valores, active_indices))

    return detalle


def _detail_row(
    key: str,
    label: str,
    parent: str,
    seccion: str,
    valores: List[float],
    active_indices: List[int],
) -> VisionPyGRowDetalle:
    acumulado = sum(valores)
    promedio = (
        sum(valores[index] for index in active_indices) / len(active_indices)
        if active_indices else 0.0
    )
    return VisionPyGRowDetalle(
        key=key,
        label=label,
        parent=parent,
        seccion=seccion,
        tipo="linea",
        signo="+",
        valores=valores,
        acumulado=acumulado,
        promedio=promedio,
    )
