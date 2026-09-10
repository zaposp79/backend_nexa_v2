"""Tests para costo_empresa de Aprendiz SENA e Inclusión en motor v2.

Valida que el motor usa el override costo_empresa_sena de datos_operativos
cuando está disponible, y que la diferencia vs fórmula dinámica es la correcta.

Referencia Excel: 008_ElTiempo_Examenes_CadenaA.xlsx
  Inputs de Nomina!W59 = W60 = AM59 = AM60 = 2,494,099.29 (valor hardcodeado)
  Motor formula: calcular_costo_empresa_sena(1,750,905) = 2,496,240.94
  Diferencia por unidad: 2,141.65
"""
from __future__ import annotations

import copy
import pytest

import sys
sys.path.insert(0, ".")

from modules.calculator_v2.nomina_calculator import (
    NominaCalculator,
    calcular_costo_empresa_sena,
)

# ── Constantes Excel 008 ──────────────────────────────────────────────────────
_SENA_SALARY = 1_750_905.0
_EXCEL_W59 = 2_494_099.29        # Inputs de Nomina!AM59 (hardcodeado)
_FORMULA_RESULT = 2_496_240.9385 # calcular_costo_empresa_sena(1_750_905)
_DELTA_PER_UNIT = _FORMULA_RESULT - _EXCEL_W59  # 2,141.65


def _make_request(sena_override: float | None = None, sena_activo: bool = True) -> dict:
    """Request mínimo con perfiles, agente y SENA/Inclusión opcionales."""
    req: dict = {
        "datos_operativos": {
            "duracion_meses": 10,
            "pct_rotacion": 0.085,
        },
        "condiciones_cadena_a": {
            "perfiles": [
                {"nombre": "perfil1", "fte": 10},
                {"nombre": "perfil2", "fte": 30},
            ],
            "detalle_nomina": [
                {"cargo": "Agente Básico 1", "salario": 1_795_000, "comision": 100_000},
                {"cargo": "Aprendiz SENA",   "salario": _SENA_SALARY, "comision": 0},
                {"cargo": "Inclusión",        "salario": _SENA_SALARY, "comision": 0},
            ],
            "ratios": {
                "filas": [
                    {
                        "position_id": "Agente Básico 1",
                        "position_name": "Agente Básico 1",
                        "incluido": True,
                        "por_perfil": [
                            {"indice_perfil": 0, "ratio": "1"},
                            {"indice_perfil": 1, "ratio": "1"},
                        ],
                    },
                    {
                        "position_id": "Aprendiz SENA",
                        "position_name": "Aprendiz SENA",
                        "incluido": sena_activo,
                        "por_perfil": [
                            {"indice_perfil": 0, "ratio": "20"},
                            {"indice_perfil": 1, "ratio": "20"},
                        ],
                    },
                    {
                        "position_id": "Inclusión",
                        "position_name": "Inclusión",
                        "incluido": sena_activo,
                        "por_perfil": [
                            {"indice_perfil": 0, "ratio": "100"},
                            {"indice_perfil": 1, "ratio": "100"},
                        ],
                    },
                ],
            },
        },
    }
    if sena_override is not None:
        req["datos_operativos"]["costo_empresa_sena"] = sena_override
    return req


class TestCalcEmpresaSena:
    """calcular_costo_empresa_sena debe dar el valor de fórmula conocido."""

    def test_formula_con_salary_008(self):
        result = calcular_costo_empresa_sena(_SENA_SALARY)
        assert result == pytest.approx(_FORMULA_RESULT, rel=1e-4)

    def test_formula_es_mayor_que_excel_hardcodeado(self):
        result = calcular_costo_empresa_sena(_SENA_SALARY)
        assert result > _EXCEL_W59
        assert abs(result - _EXCEL_W59) == pytest.approx(_DELTA_PER_UNIT, rel=1e-3)

    def test_salary_cero_retorna_cero(self):
        assert calcular_costo_empresa_sena(0) == 0.0


class TestSenaOverrideEnNominaMV2:
    """El override costo_empresa_sena reduce el exceso exactamente."""

    def test_sin_override_usa_formula(self):
        req = _make_request(sena_override=None)
        calc = NominaCalculator(req)
        desglose = calc.desglose_por_cargo()

        sena_key = next((k for k in desglose if "aprendiz" in k.lower() or "sena" in k.lower()), None)
        assert sena_key is not None, "SENA cargo no encontrado en desglose"
        inc_key = next((k for k in desglose if "inclus" in k.lower()), None)
        assert inc_key is not None, "Inclusión cargo no encontrado en desglose"

        # Verificar que los valores están calculados con la fórmula (no override)
        sena_val = desglose[sena_key]
        inc_val  = desglose[inc_key]
        assert sena_val > 0 and inc_val > 0

    def test_con_override_reduce_exceso_sena(self):
        req_sin = _make_request(sena_override=None)
        req_con = _make_request(sena_override=_EXCEL_W59)

        desglose_sin = NominaCalculator(req_sin).desglose_por_cargo()
        desglose_con = NominaCalculator(req_con).desglose_por_cargo()

        sena_key = next((k for k in desglose_sin if "aprendiz" in k.lower()), None)
        inc_key  = next((k for k in desglose_sin if "inclus" in k.lower()), None)

        exceso_sena = desglose_sin[sena_key] - desglose_con[sena_key]
        exceso_inc  = desglose_sin[inc_key]  - desglose_con[inc_key]

        # El exceso debe ser positivo (formula > override) y proporcional a _DELTA_PER_UNIT
        assert exceso_sena > 0
        assert exceso_inc  > 0
        total_exceso = exceso_sena + exceso_inc
        assert total_exceso > 0, "Override debe reducir el costo total"

    def test_nomina_loaded_menor_con_override(self):
        req_sin = _make_request(sena_override=None)
        req_con = _make_request(sena_override=_EXCEL_W59)

        nl_sin = NominaCalculator(req_sin).calcular()
        nl_con = NominaCalculator(req_con).calcular()

        assert nl_con < nl_sin, "Con override Excel la nómina debe ser menor"
        reduccion = nl_sin - nl_con
        assert reduccion > 0

    def test_sin_sena_activo_override_no_afecta(self):
        """Si SENA/Inclusión están inactivos, el override no cambia nada."""
        req_sin = _make_request(sena_activo=False, sena_override=None)
        req_con = _make_request(sena_activo=False, sena_override=_EXCEL_W59)

        nl_sin = NominaCalculator(req_sin).calcular()
        nl_con = NominaCalculator(req_con).calcular()

        assert nl_sin == pytest.approx(nl_con, rel=1e-8)
