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


def calcular_costo_empresa(salario_base: float, comision: float, smlv: float = _SMLV_DEFAULT) -> float:
    """Costo mensual total a cargo del empleador para un cargo dado.

    Incluye: salario + aux transporte + seguridad social + parafiscales +
    prestaciones sociales + dotaciones.
    """
    t_imponible = salario_base + comision
    if t_imponible <= 0:
        return 0.0

    aux_transporte = _AUX_TRANSPORTE if 0 < t_imponible < 2 * smlv else 0.0
    t_haberes = t_imponible + aux_transporte
    base_ss = t_imponible  # base para Salud, ICBF+Sena (sobre T.Imponible)
    base_p = t_haberes - aux_transporte  # base para Pensión, ARL, Caja, Vacaciones

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
        """
        nomina_loaded = self._nomina_agentes() + self._nomina_estructura()
        salario_variable = self._nomina_comisiones_brutas()
        return {
            "nomina_loaded": nomina_loaded,
            "crucero_total": self._crucero(),
            "capacitacion_rotacion": self._capacitacion_rotacion(),
            "salario_fijo": nomina_loaded - salario_variable,
            "salario_variable": salario_variable,
        }

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

        'Agente Básico 1' en ratios.filas (tipo='Agente', ratio=1) mapea a los perfiles.
        El costo por agente viene de perfiles[i].capacitacion.crucero_mensual × perfil.fte.
        """
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        total = 0.0
        for perfil in perfiles:
            crucero_val = float(perfil.get("capacitacion", {}).get("crucero_mensual", 0))
            fte = float(perfil.get("fte", 0))
            total += crucero_val * fte
        return total

    def _nomina_agentes(self) -> float:
        """Suma del costo empresa de todos los perfiles de agentes × FTE."""
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        total = 0.0
        for perfil in perfiles:
            salario = float(perfil.get("salario_base", 0))
            comision = float(perfil.get("comision_mensual", 0))
            fte = float(perfil.get("fte", 0))
            costo_fte = calcular_costo_empresa(salario, comision)
            total += costo_fte * fte
        return total

    def _nomina_estructura(self) -> float:
        """Suma del costo empresa de cargos de estructura × cantidad calculada por ratio."""
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        detalle: List[Dict] = self._cadena_a.get("detalle_nomina", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])
        detalle_map = {c["cargo"].strip().lower(): c for c in detalle}

        total = 0.0
        for fila in ratios_filas:
            if not fila.get("incluido", False):
                continue
            cargo_data = self._resolver_cargo(fila, detalle_map)
            if not cargo_data:
                continue
            cantidad = self._calcular_cantidad(fila, perfiles)
            if cantidad <= 0:
                continue
            salario = float(cargo_data.get("salario", 0))
            comision = float(cargo_data.get("comision", 0))
            total += calcular_costo_empresa(salario, comision) * cantidad

        return total

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
        """Distribución fraccionaria SIN ceil: fte_perfil / ratio (continua, no entera)."""
        total = 0.0
        for pr in fila.get("por_perfil", []):
            indice = pr.get("indice_perfil", 0)
            try:
                ratio_val = float(str(pr.get("ratio", "0")).strip() or "0")
            except ValueError:
                ratio_val = 0.0
            if ratio_val > 0 and indice < len(perfiles):
                total += float(perfiles[indice].get("fte", 0)) / ratio_val
        return total
