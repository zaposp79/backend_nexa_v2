"""
Cálculo de nómina para Cadena A.

Reglas del Excel Nexa - Pricing - Simulador - V2-8.xlsx (Inputs de Nomina, fila 36):
  Salud: 8.5%, Pensión: 12%, ARL: 0.522%, Caja: 4%, ICBF+Sena: 4%
  Cesantías: 8.33%, Primas: 8.33%, Interés Cesantía: 12%, Vacaciones: 4.17%
  Salario Integral (>10 SMLV): contribuciones sobre el 70% de la base.
  Para Salario Integral: Cesantías = Primas = 0.
"""
from __future__ import annotations

from typing import Any, Dict, List

# Tasas de nómina (Excel V2-8, Inputs de Nomina fila 36)
_TASA_SALUD = 0.085
_TASA_PENSION = 0.12
_TASA_ARL = 0.00522
_TASA_CAJA = 0.04
_TASA_ICBF_SENA = 0.04
_TASA_CESANTIAS = 0.0833
_TASA_PRIMAS = 0.0833
_TASA_INTERES_CESANTIA = 0.12
_TASA_VACACIONES = 0.0417

# Valores parametrizados (SMLV 2026, aux transporte y dotaciones mensuales)
_SMLV_DEFAULT = 1_795_000.0
_AUX_TRANSPORTE = 249_095.0
_DOTACIONES_MENSUAL = 15_375.0

# Factores de recargo (Excel V2-8: Condiciones Cadena A D15:D21 / Inputs de Nomina cols X–AL)
# Fórmula: (salario_base / 220) × cantidad × factor — informativo, no suma a costo empresa.
# Excel: col AM = col W → costo empresa base-only; recargos aparecen en cols separadas.
_HORAS_MES_BASE = 220.0
_FACTOR_FESTIVO = 0.90
_FACTOR_DOMINICAL = 0.90
_FACTOR_NOCTURNO = 0.35
_FACTOR_FESTIVO_NOCTURNO = 1.15
_FACTOR_DOMINICAL_NOCTURNO = 1.15
_FACTOR_EXTRA_DIURNO = 1.25
_FACTOR_EXTRA_NOCTURNO = 1.75


def calcular_costo_empresa(
    salario_base: float,
    comision: float,
    smlv: float = _SMLV_DEFAULT,
    recargos: float = 0.0,
) -> float:
    """Costo mensual total a cargo del empleador para un cargo dado.

    Incluye: salario + aux transporte + recargos + seguridad social + parafiscales +
    prestaciones sociales + dotaciones.

    Excel V2-8: Inputs de Nomina H62 = T.Imponible + AuxTransporte + Total_Recargos.
    Los recargos (festivo, dominical, nocturno, etc.) elevan T.Haberes antes de
    calcular Pensión/ARL/Caja/Primas/Vacaciones. No alteran la base para Salud ni
    la condición de aux_transporte (que depende de T.Imponible = sal+com).
    """
    t_imponible = salario_base + comision
    if t_imponible <= 0:
        return 0.0

    aux_transporte = _AUX_TRANSPORTE if 0 < t_imponible < 2 * smlv else 0.0
    # Excel V2-8: H62 = SUM(F62:G62, AL62) = T.Imponible + AuxTransporte + Total_Recargos
    t_haberes = t_imponible + aux_transporte + recargos
    base_ss = t_imponible  # base para Salud, ICBF+Sena (F62 = solo sal+com)
    base_p = t_haberes - aux_transporte  # base para Pensión, ARL, Caja, Vacaciones (H62-G62)

    es_integral = base_ss > 10 * smlv

    # Seguridad social (empleador)
    salud = base_ss * 0.70 * _TASA_SALUD if es_integral else 0.0
    pension = base_p * _TASA_PENSION * (0.70 if base_p > 10 * smlv else 1.0)
    arl = base_p * _TASA_ARL * (0.70 if base_p > 10 * smlv else 1.0)
    seg_social = t_haberes + salud + pension + arl  # t_haberes incluido = costo total de salario

    # Parafiscales
    caja = base_p * _TASA_CAJA * (0.70 if base_p > 10 * smlv else 1.0)
    icbf_sena = base_ss * _TASA_ICBF_SENA * 0.70 if es_integral else 0.0
    parafiscales = caja + icbf_sena

    # Prestaciones sociales
    cesantias = 0.0 if es_integral else t_haberes * _TASA_CESANTIAS
    primas = 0.0 if es_integral else t_haberes * _TASA_PRIMAS
    interes_cesantia = cesantias * _TASA_INTERES_CESANTIA
    vacaciones = base_p * _TASA_VACACIONES * (0.70 if base_p > 10 * smlv else 1.0)
    prestaciones = cesantias + primas + interes_cesantia + vacaciones

    # Dotaciones
    dotaciones = _DOTACIONES_MENSUAL if 0 < t_imponible < 2 * smlv else 0.0

    return seg_social + parafiscales + prestaciones + dotaciones


class NominaCalculator:
    """Calcula el costo total de nómina mensual para Cadena A."""

    def __init__(self, request_data: Dict[str, Any]) -> None:
        self._req = request_data
        self._cadena_a = request_data.get("condiciones_cadena_a", {})

    def calcular(self) -> float:
        return (
            self._nomina_agentes()
            + self._nomina_estructura()
            + self._crucero()
            + self._capacitacion_rotacion()
        )

    def calcular_detalle(self) -> dict:
        """Sub-components for periods format.

        nomina_loaded = agentes + estructura (Salario Fijo + Variable del NL).
        Excel V2-8: 'Visión P&G'!R37 = R38 + R39 = Salario Fijo + Salario Variable.
        salario_variable = comisiones brutas (sin cargas prestacionales).
        Excel V2-8: 'Nomina Loaded'!K198:K217 = sum(comision × FTE/cantidad por cargo).
        salario_fijo = nomina_loaded - salario_variable.
        recargos_horas_extra = informativo (no suma a nómina, igual que Excel col AM = col W).
        """
        nomina_loaded = self._nomina_agentes() + self._nomina_estructura()
        salario_variable = self._nomina_comisiones_brutas()
        return {
            "nomina_loaded": nomina_loaded,
            "crucero_total": self._crucero(),
            "capacitacion_rotacion": self._capacitacion_rotacion(),
            "salario_fijo": nomina_loaded - salario_variable,
            "salario_variable": salario_variable,
            "recargos_horas_extra": self._calcular_recargos_total(),
        }

    def _calcular_recargos_total(self) -> float:
        """Suma de recargos × FTE para todos los perfiles (informativo)."""
        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            fte = float(perfil.get("fte", 0))
            total += self._recargo_perfil(perfil) * fte
        return total

    @staticmethod
    def _recargo_perfil(perfil: Dict) -> float:
        """Costo de recargos por un FTE del perfil (no suma a costo empresa).

        Excel V2-8: Condiciones Cadena A D15:D21 / Inputs de Nomina cols X–AL.
        Fórmula: (salario_base / 220) × cantidad × factor.
        Acepta los conteos en perfil.recargos{} o directamente en perfil{} (flat).
        """
        salario_base = float(perfil.get("salario_base", 0))
        if salario_base <= 0:
            return 0.0
        tarifa = salario_base / _HORAS_MES_BASE
        r: Dict = perfil.get("recargos") or {}

        def _cnt(key: str) -> float:
            return float(r.get(key) or perfil.get(key) or 0)

        return (
            tarifa * _cnt("holidayCount") * _FACTOR_FESTIVO
            + tarifa * _cnt("sundayCount") * _FACTOR_DOMINICAL
            + tarifa * _cnt("nightHoursCount") * _FACTOR_NOCTURNO
            + tarifa * _cnt("nightHolidayCount") * _FACTOR_FESTIVO_NOCTURNO
            + tarifa * _cnt("nightSundayCount") * _FACTOR_DOMINICAL_NOCTURNO
            + tarifa * _cnt("extraDayHoursCount") * _FACTOR_EXTRA_DIURNO
            + tarifa * _cnt("extraNightHoursCount") * _FACTOR_EXTRA_NOCTURNO
        )

    def _nomina_comisiones_brutas(self) -> float:
        """Suma bruta de comisiones de agentes y estructura (sin cargas prestacionales).

        Excel V2-8: 'Nomina Loaded'!K198:K217 donde col A="Activado".
        Incluye comision_mensual × FTE por perfil de agente +
        comision × cantidad pro-rateada por cargo de estructura.
        """
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        detalle: List[Dict] = self._cadena_a.get("detalle_nomina", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])
        detalle_map = {c["cargo"].strip().lower(): c for c in detalle}

        # Comisiones brutas de agentes (FTE)
        total = sum(
            float(p.get("comision_mensual", 0)) * float(p.get("fte", 0))
            for p in perfiles
        )
        # Comisiones brutas de estructura (cantidad pro-rateada)
        for fila in ratios_filas:
            if not fila.get("incluido", False):
                continue
            cargo_data = self._resolver_cargo(fila, detalle_map)
            if not cargo_data:
                continue
            comision = float(cargo_data.get("comision", 0))
            if comision <= 0:
                continue
            cantidad = self._calcular_cantidad(fila, perfiles)
            if cantidad <= 0:
                continue
            total += comision * cantidad
        return total

    def _crucero(self) -> float:
        """Costo operacional mensual plano por agente (sin cargas sociales).

        Excel V2-8: 'Condiciones Cadena A'!E153 = 'Panel de Control General'!C17 × FTE
        La tarifa global (Panel!C17) viene de datos_operativos.crucero.
        Fallback: crucero_mensual por perfil (compatibilidad con requests legacy).
        """
        # Tarifa global por estación — Panel de Control General C17
        crucero_base = float(self._req.get("datos_operativos", {}).get("crucero", 0.0))
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        total = 0.0
        for perfil in perfiles:
            cap = perfil.get("capacitacion") or {}
            crucero_unit = crucero_base or float(cap.get("crucero_mensual", 0))
            fte = float(perfil.get("fte", 0))
            total += crucero_unit * fte
        return total

    def _nomina_agentes(self) -> float:
        """Suma del costo empresa de todos los perfiles de agentes × FTE.

        Excel V2-8: Inputs de Nomina AM62 = W62 = costo_empresa_con_recargos.
        Los recargos por FTE se incluyen en T.Haberes antes de calcular cargas sociales.
        """
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        total = 0.0
        for perfil in perfiles:
            salario = float(perfil.get("salario_base", 0))
            comision = float(perfil.get("comision_mensual", 0))
            fte = float(perfil.get("fte", 0))
            recargo_fte = self._recargo_perfil(perfil)  # base recargo por FTE (Excel AL62)
            costo_fte = calcular_costo_empresa(salario, comision, recargos=recargo_fte)
            total += costo_fte * fte
        return total

    def _nomina_estructura(self) -> float:
        """Suma del costo empresa de cargos de estructura × cantidad calculada por ratio."""
        return sum(self.desglose_por_cargo().values())

    def desglose_por_cargo(self) -> Dict[str, float]:
        """Nómina cargada por cargo de estructura (excl. agente base).

        Retorna TODOS los cargos definidos en ratios_filas (valor=0 para los no activos).
        Usado para el gráfico 'Proporción Nómina por Cargo' en CTS.
        # Excel Graficos: P5:AF29 (SUMIFS por cargo en NominaLoaded por perfil)
        """
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        detalle: List[Dict] = self._cadena_a.get("detalle_nomina", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])
        detalle_map = {c["cargo"].strip().lower(): c for c in detalle}

        result: Dict[str, float] = {}
        for fila in ratios_filas:
            nombre = fila.get("position_name") or fila.get("position_id", "")
            if not nombre:
                continue
            if not fila.get("incluido", False):
                result.setdefault(nombre, 0.0)
                continue
            cargo_data = self._resolver_cargo(fila, detalle_map)
            if not cargo_data:
                result.setdefault(nombre, 0.0)
                continue
            cantidad = self._calcular_cantidad(fila, perfiles)
            if cantidad <= 0:
                result.setdefault(nombre, 0.0)
                continue
            salario = float(cargo_data.get("salario", 0))
            comision = float(cargo_data.get("comision", 0))
            result[nombre] = result.get(nombre, 0.0) + calcular_costo_empresa(salario, comision) * cantidad

        return result

    def _capacitacion_rotacion(self) -> float:
        """Costo mensual de capacitación por rotación (Excel V2-8: 'Nomina Loaded'!E283-E299).

        Por cada perfil con incluye_capacitacion_rotacion=True:
          costo = fte × dias_capacitacion_perfil × tarifa_diaria_capacitacion × pct_rotacion
        Excel V2-8: 'Panel de Control General'!C20 = pct_rotacion; C16 = tarifa_diaria.
        """
        datos_op = self._req.get("datos_operativos", {})
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        tarifa_diaria = float(datos_op.get("tarifa_diaria_capacitacion", 20_000.0))
        if pct_rotacion <= 0 or tarifa_diaria <= 0:
            return 0.0

        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            cap = perfil.get("capacitacion", {})
            if not cap.get("incluye_capacitacion_rotacion", False):
                continue
            fte = float(perfil.get("fte", 0))
            dias = float(cap.get("dias_capacitacion_perfil", 0))
            total += fte * dias * tarifa_diaria * pct_rotacion
        return total

    @staticmethod
    def _resolver_cargo(fila: Dict, detalle_map: Dict) -> Dict:
        """Busca datos salariales del cargo en detalle_nomina (por position_id o position_name)."""
        cargo = detalle_map.get(fila.get("position_id", "").strip().lower())
        if not cargo:
            cargo = detalle_map.get(fila.get("position_name", "").strip().lower())
        return cargo or {}

    @staticmethod
    def _calcular_cantidad(fila: Dict, perfiles: List[Dict]) -> float:
        """Distribución fraccionaria SIN ceil: fte_perfil / ratio (continua, no entera).

        Excel V2-8: Condiciones Cadena A E78 = (fte_total / ratio_cargo).
        Si por_perfil[i].personalizado > 0, se usa ese valor directamente en lugar
        del cálculo automático (equivale a editar manualmente E78/F78/G78 en el Excel).
        """
        total = 0.0
        for pr in fila.get("por_perfil", []):
            # Override manual: si personalizado > 0 se usa tal cual (Excel: celda editada)
            try:
                personalizado_val = float(pr.get("personalizado") or 0)
            except (TypeError, ValueError):
                personalizado_val = 0.0
            if personalizado_val > 0:
                total += personalizado_val
                continue

            # Cálculo estándar: fte / ratio
            indice = pr.get("indice_perfil", 0)
            try:
                ratio_val = float(str(pr.get("ratio", "0")).strip() or "0")
            except ValueError:
                ratio_val = 0.0
            if ratio_val > 0 and indice < len(perfiles):
                total += float(perfiles[indice].get("fte", 0)) / ratio_val
        return total
