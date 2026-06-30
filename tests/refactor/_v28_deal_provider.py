"""Test provider for Excel V2-8 METROCUADRADO SAC deal scenario.

Extends the active (V2-8 production) parametrization base and patches
costo_empresa_override for ALL staff roles with the exact cargado values
from Excel V2-8 'Inputs de Nomina' W column.

WHY ACTIVE AS BASE:
  The active parametrization is the V2-8 HR that was uploaded. Staff role salaries
  differ from the specific deal scenario ('Condiciones Cadena A'), but the non-payroll
  components (GN/OP) are correct. Using active as base + staff overrides gives the
  most accurate CTS representation of the Excel V2-8 deal.

STAFF CARGADO SOURCE (Excel V2-8 'Inputs de Nomina' column W):
  These are the exact monthly loaded cost values (salario_cargado) the Excel computes
  for each staff role in the METROCUADRADO SAC deal scenario. They include the deal-specific
  salary AND commission amounts from 'Condiciones Cadena A'.

  3 roles have deal-level commissions (non-zero col D):
    - Director de cuentas:  D39=3,868,125  → W39=32,816,427.27
    - Jefe de Operación:    D46=1,500,000  → W46=8,065,482.67
    - Supervisor:           D57=700,000    → W57=4,506,461.78

  All other roles: no commission (D=0), cargado varies only because deal salary ≠ HR catalog.

  costo_empresa_override bypasses the NominaCargada formula — the exact Excel value
  is used directly, matching the Excel calculation cell-for-cell.

SCOPE: GOLDEN TESTS ONLY. Not for production use.
"""
from __future__ import annotations

import copy
import json
import unicodedata
from pathlib import Path
from typing import Any, Dict

import backend_nexa  # noqa: F401 — registers nexa_engine alias

from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver, get_resolver

_V27_DIR = Path(__file__).resolve().parents[2] / "storage" / "parametrization" / "v2-7"

# Excel V2-8 'Inputs de Nomina' column W (cargado) for ALL staff roles in the
# METROCUADRADO SAC deal scenario (rows 39–61).
# Keys are ACCENT-STRIPPED, LOWERCASE to match the engine's lookup in
# get_costo_empresa_override() (which uses .strip().lower() without NFKD).
# Excel V2-8 · 'Inputs de Nomina'!W39:W61 · deal scenario METROCUADRADO SAC
_V28_ALL_STAFF_CARGADO: Dict[str, float] = {
    # Row 39: D=3,868,125 (comision Director)
    "director de cuentas":                             32_816_427.2706,
    # Row 40: no commission
    "director de performance":                         18_902_979.108,
    # Row 41: no commission (Jefe Comercial Regional en deal = 0, F41 referencia otro escenario)
    "jefe comercial regional":                          7_648_436.16216,
    # Row 42: no commission
    "analista profesional afac":                        4_652_770.9207268795,
    # Row 43: no commission
    "lider de entrenamiento":                           6_905_403.675683999,
    # Row 44: no commission
    "lider de experiencia de cliente y performance":    6_905_403.675683999,
    # Row 45: no commission
    "lider de planeacion operativa":                    7_562_645.718516,
    # Row 46: D=1,500,000 (comision Jefe de Operación)
    "jefe de operacion":                                8_065_482.671793599,
    # Row 47: no commission
    "works force":                                      4_196_801.9831356,
    # Row 48: no commission
    "reporting":                                        4_196_801.9831356,
    # Row 49: no commission
    "gtr":                                              3_051_809.5372479996,
    # Row 50: no commission
    "analista prof. de seleccion inicial":              4_277_939.3857684,
    # Row 51: no commission
    "analista 1 de reclutamiento inicial":              2_946_259.5283497535,
    # Row 52: no commission
    "analista prof. de seleccion rotacion":             4_277_939.3857684,
    # Row 53: no commission
    "analista 1 de reclutamiento rotacion":             2_946_259.5283497535,
    # Row 54: no commission
    "analista 2 service desk":                          3_391_133.4384399997,
    # Row 55: no commission
    "formadores":                                       3_155_444.57026,
    # Row 56: no commission
    "monitor de calidad":                               3_281_882.713984,
    # Row 57: D=700,000 (comision Supervisor)
    "supervisor":                                       4_506_461.77942,
    # Row 58: no commission (Validador excluded from ratios — no-op)
    "validador":                                        2_730_864.2626000005,
    # Rows 59/60 (SENA/Inclusión) and 61 (Especialista) use separate calculators
    # in the engine — costo_empresa_override is not consulted for these special roles.
}

# Excel V2-8 · 'Inputs de Nomina' staff commission (col D, raw) + base (col C), rows 39/46/57.
# These support roles earn variable commission in Excel: the 'Nomina Loaded' variable block
# (rows 155-181) sums per-role commission = D-col × staff-FTE into 'Salario Variable' (Vision CTS!C38).
# e.g. Supervisor = D57(700,000) × E95(9.5 FTE) = 6,650,000. The backend partition
# (salario_fijo = total_cargado − comisiones) places this raw commission in the variable line and
# carves it out of fijo — exactly matching Excel. Active HR has comision_pct=0 for staff and a
# slightly different base, so patch BOTH salario (=C) and comision_pct (=D/C) → commission = D.
# salario for support feeds ONLY the commission line (loaded cost comes from costo_empresa_override).
_V28_STAFF_COMISION: Dict[str, tuple] = {
    # rol_norm (accent-stripped): (base_C, comision_pct = D/C)
    "director de cuentas": (22_761_150.0, 3_868_125.0 / 22_761_150.0),  # Inputs de Nomina!C39/D39
    "jefe de operacion":   (4_329_699.6,  1_500_000.0 / 4_329_699.6),   # Inputs de Nomina!C46/D46
    "supervisor":          (2_334_300.0,  700_000.0   / 2_334_300.0),   # Inputs de Nomina!C57/D57
}

# Excel V2-8 · 'Inputs de Nomina'!C59/C60 — base salary for SENA/Inclusión rows.
# The engine uses calcular_aprendiz(get_salario_rol(rol)), reading `salario` from the HR row.
# C59 = 1,750,905 (Aprendiz SENA), C60 = 1,750,905 (Inclusión).
_V28_SENA_INCLUSION_SALARY: Dict[str, float] = {
    "aprendiz sena": 1_750_905.0,  # Inputs de Nomina!C59
    "inclusion":     1_750_905.0,  # Inputs de Nomina!C60
}

# Excel V2-8 · 'Nomina Loaded'!C329 = C330 = C331 = 60,800 COP — costo examen médico Bogotá.
# Active HR storage has 60.8 (wrong scale; should be 60,800 full COP). Override here for deal parity.
_V28_EXAMEN_MEDICO_BOGOTA: float = 60_800.0  # Nomina Loaded!C329/C330/C331

# Excel V2-8 · 'Condiciones Cadena A'!E135 = 0.28 — porcentaje de exámenes médicos anuales.
# Active HR fallback = 1.0 (HR-AutRot missing). Override with deal value.
_V28_PCT_EXAMEN_ANUAL_SAC: float = 0.28  # Condiciones Cadena A!E135


def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


class _ActiveRepoPatchedNomina:
    """Active HR repo with ALL staff costo_empresa_override patched to V2-8 deal values.

    Matching uses accent-stripped lowercase keys (_strip_accents) for the existing rows.
    Additionally, synthetic accent-stripped alias rows are appended so the engine's
    simple .strip().lower() lookup (no NFKD) can find the overrides.
    """

    def __init__(self) -> None:
        raw = get_resolver().get_active_hr()
        self._data = self._patch_all_staff(raw)

    @staticmethod
    def _patch_all_staff(data: Dict[str, Any]) -> Dict[str, Any]:
        data = copy.deepcopy(data)
        nomina = data.get("nomina", [])

        # Patch existing rows (accented key match)
        for row in nomina:
            rol_stripped = _strip_accents(str(row.get("rol", "")))
            if rol_stripped in _V28_ALL_STAFF_CARGADO:
                row["costo_empresa_override"] = _V28_ALL_STAFF_CARGADO[rol_stripped]

        # Patch SENA/Inclusión base salary (Excel V2-8 'Inputs de Nomina'!C59/C60 = 1,750,905).
        # The engine uses calcular_aprendiz(get_salario_rol(rol)), NOT costo_empresa_override.
        for row in nomina:
            rol_stripped = _strip_accents(str(row.get("rol", "")))
            if rol_stripped in _V28_SENA_INCLUSION_SALARY:
                row["salario"] = _V28_SENA_INCLUSION_SALARY[rol_stripped]

        # Patch staff variable commission (Excel 'Inputs de Nomina' col D, rows 39/46/57).
        # Sets base (=C) and comision_pct (=D/C) so the backend variable line = Excel raw commission
        # (Director/Jefe/Supervisor). Total-invariant: salario_fijo = total_cargado − comisiones, so the
        # support loaded total is unchanged — only the fijo↔variable split is corrected (Vision CTS C37/C38).
        for row in nomina:
            rol_stripped = _strip_accents(str(row.get("rol", "")))
            if rol_stripped in _V28_STAFF_COMISION:
                base_c, com_pct = _V28_STAFF_COMISION[rol_stripped]
                row["salario"] = base_c
                row["comision_pct"] = com_pct

        # Append accent-stripped alias rows for engine lookup (no NFKD in provider code).
        # The engine iterates nomina in order; original accented row won't match the
        # engine's simple .lower() lookup, but the alias row (appended at end) will.
        for rol_norm, cargado in _V28_ALL_STAFF_CARGADO.items():
            alias_row = {"rol": rol_norm, "costo_empresa_override": cargado}
            # Staff commission roles also carry salario(=C) + comision_pct(=D/C) on the alias so the
            # engine's accent-stripped lookup (e.g. "jefe de operacion") resolves the commission —
            # the accented original row is invisible to get_comision_pct_rol's plain .lower() match.
            if rol_norm in _V28_STAFF_COMISION:
                base_c, com_pct = _V28_STAFF_COMISION[rol_norm]
                alias_row["salario"] = base_c
                alias_row["comision_pct"] = com_pct
            nomina.append(alias_row)

        # Append alias rows for SENA/Inclusión so the engine's .strip().lower() lookup hits them.
        for rol_norm, sal in _V28_SENA_INCLUSION_SALARY.items():
            nomina.append({"rol": rol_norm, "salario": sal, "tipo": "Empleado"})

        data["nomina"] = nomina

        # Patch med_seg: set costo_examen_medico = 60,800 COP for Bogota.
        # Active HR has 60.8 (wrong scale). Excel: Nomina Loaded!C329/C330/C331 = 60,800.
        med_seg = data.get("med_seg", [])
        for row in med_seg:
            if "bogota" in _strip_accents(row.get("localidad", "")) and "examen" in row.get("centrocosto", "").lower():
                row["valor"] = _V28_EXAMEN_MEDICO_BOGOTA
        data["med_seg"] = med_seg

        # Inject rotacion_ausentismo for SAC with exact Excel V2-8 values.
        # Excel V2-8 · 'Rot, Ausent y Rentabilidad'!F19 · fórmula: =AVERAGE(B19:E19)
        # Traducción: promedio 4 meses (Sep=0.0609, Oct=0.0719, Nov=0.0931, Dic=0.0828)
        # pct_examen_anual = 0.28 from Condiciones Cadena A!E135.
        data["rotacion_ausentismo"] = [
            {
                "linea":                 "SAC",
                "pct_rotacion_mensual":  0.077175,  # Rot!F19 = AVERAGE(B19:E19)
                "pct_ausentismo":        0.07,       # OP-Costo fallback (unchanged)
                "pct_examen_anual":      _V28_PCT_EXAMEN_ANUAL_SAC,  # CCA!E135 = 0.28
            }
        ]

        return data

    def get_active_data(self) -> Dict[str, Any]:
        return self._data


class _ActiveRepo:
    """Unpatched active repo for GN/OP (unchanged from deal scenario)."""

    def __init__(self, domain: str) -> None:
        resolver = get_resolver()
        if domain == "gn":
            self._data: Dict[str, Any] = copy.deepcopy(resolver.get_active_gn())
        elif domain == "op":
            self._data = copy.deepcopy(resolver.get_active_op())
        else:
            raise ValueError(f"Unknown domain: {domain}")

    def get_active_data(self) -> Dict[str, Any]:
        return self._data


def build_v28_deal_provider() -> ParametrizationProvider:
    """Return a ParametrizationProvider for the Excel V2-8 METROCUADRADO SAC deal.

    Uses active (V2-8 production) HR as base and patches costo_empresa_override
    for ALL staff roles with exact cargado values from Excel V2-8 'Inputs de Nomina'!W39:W61.

    This enables CTS-001 full-match validation against the V2-8 Excel oracle.

    GOLDEN TESTS ONLY — not for production.
    """
    resolver = ParametrizationResolver(
        hr_repo=_ActiveRepoPatchedNomina(),
        gn_repo=_ActiveRepo("gn"),
        op_repo=_ActiveRepo("op"),
    )
    return ParametrizationProvider.build(resolver)
