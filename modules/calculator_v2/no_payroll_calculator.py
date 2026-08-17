"""
Cálculo de OPEX (No Payroll) para Cadena A.

Tres componentes (hoja No Payroll del Excel):
  1. OPEX IT: ítems de opex_fijo de cada perfil (licencias software, internet)
  2. Inversiones: hardware amortizado (computadores, diademas, licencias)
  3. Costos Fijos × Estación: utilities por puesto (energía, arriendo, etc.) — de HR params
"""
from __future__ import annotations

from typing import Any, Dict, List


class NoPayrollCalculator:
    """Calcula el costo total de OPEX mensual para Cadena A."""

    def __init__(
        self,
        request_data: Dict[str, Any],
        costo_fijo_por_estacion: float = 0.0,
    ) -> None:
        self._cadena_a = request_data.get("condiciones_cadena_a", {})
        self._costo_fijo_por_estacion = costo_fijo_por_estacion
        # Excel No payroll fórmula inversiones: SUMPRODUCT(precio × qty) × (1 + Panel!L11)
        indexacion = request_data.get("volumetria", {}).get("indexacion", {})
        self._tasa_interes_mensual = float(indexacion.get("tasa_interes_mensual", 0.0))
        # Excel V2-8: Panel!C19 — fuente canónica del ausentismo; siempre actualizado por el frontend.
        # staffing.calculo_horas_staffing.ausentismo_pago puede estar stale → NO usar para fórmulas.
        datos_op = request_data.get("datos_operativos", {})
        self._pct_ausentismo = float(datos_op.get("pct_ausentismo", 0.0))
        # Excel V2-8: 'Panel de Control General'!C20 — % de rotación para ítems de opex rotación
        self._pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))

    def calcular(self) -> float:
        return self._opex_it() + self._inversiones() + self._costos_fijos()

    def calcular_detalle(self) -> dict:
        """Sub-components for periods format: opex_fijo, inversiones, costos_fijos."""
        return {
            "opex_fijo": self._opex_it(),
            "inversiones": self._inversiones(),
            "costos_fijos": self._costos_fijos(),
        }

    def _opex_it(self) -> float:
        """Suma ítems de opex_fijo de cada perfil (licencias, internet, etc.)."""
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        total = 0.0
        for perfil in perfiles:
            fte = float(perfil.get("fte", 0))
            opex_fijo = perfil.get("opex_fijo", {})
            # semanas y horas del staffing (estables; no cambian con pct_ausentismo)
            staffing = opex_fijo.get("staffing", {}).get("calculo_horas_staffing", {})
            semanas = float(staffing.get("semanas_mes", 4.33))
            horas = float(staffing.get("horas_semanales", 42.0))
            items: List[Dict] = opex_fijo.get("items", [])
            for item in items:
                total += self._valor_item(item, fte, semanas, horas)
        return total

    def _inversiones(self) -> float:
        """Hardware amortizado mensual.

        Formatos soportados para cantidad por perfil (ver _cantidad_total):
          Nuevo:   por_perfil: [{indice_perfil, valor, nombre}, ...]
          Estándar: perfil1=10, perfil2=30, perfilN=...
          Legacy:  valores_por_perfil: {id: qty, ...}

        es_precio_total:
          True  → precio_compra es por unidad; mensual = precio_compra/meses × qty_total
          False → precio_mensual es por unidad; mensual = precio_mensual × qty_total

        Excel No payroll R167: =SUMPRODUCT(precio_mensual × qty) × (1 + Panel!L11)
        El factor (1 + tasa_interes_mensual) se aplica siempre sobre el total de inversiones.
        """
        inversiones: List[Dict] = self._cadena_a.get("inversiones", [])
        total = 0.0
        for inv in inversiones:
            cantidad_total = self._cantidad_total(inv)
            if cantidad_total == 0:
                continue

            es_precio_total = bool(inv.get("es_precio_total", False))
            if es_precio_total:
                # precio_compra es por unidad → amortizar sobre meses_diferimiento
                precio_compra = float(inv.get("precio_compra", 0))
                meses = float(inv.get("meses_diferimiento", 1)) or 1.0
                total += (precio_compra / meses) * cantidad_total
            else:
                # precio_mensual ya es por unidad
                precio_mensual = float(inv.get("precio_mensual", 0))
                total += precio_mensual * cantidad_total

        # Excel No payroll: inversiones × (1 + tasa_interes_mensual)
        # Panel de Control General L11 = tasa_interes_mensual (siempre activo)
        return total * (1.0 + self._tasa_interes_mensual)

    def _costos_fijos(self) -> float:
        """Costos fijos por estación presencial (energía, agua, arriendo, etc.)
        leídos desde parametrización HR para la ciudad del deal."""
        if self._costo_fijo_por_estacion <= 0:
            return 0.0
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        total_estaciones = sum(float(p.get("estaciones_presenciales", 0)) for p in perfiles)
        return self._costo_fijo_por_estacion * total_estaciones

    @staticmethod
    def _cantidad_total(inv: Dict) -> float:
        """Suma de cantidades por perfil.

        Formatos soportados:
          1. Lista:    por_perfil: [{indice_perfil: 0, valor: 10, nombre: "perfil1"}, ...]
          2. Estándar: perfil1=10, perfil2=30, perfil3=40, perfilN=... (formato correcto)
          3. Legacy:   valores_por_perfil: {id: qty, ...}
        """
        if "por_perfil" in inv:
            return sum(
                float(p.get("valor") or p.get("cantidad") or 0)
                for p in inv.get("por_perfil", [])
            )

        total = 0.0
        i = 1
        while True:
            key = f"perfil{i}"
            if key not in inv:
                break
            total += float(inv.get(key, 0))
            i += 1
        if total > 0:
            return total

        return sum(float(v) for v in inv.get("valores_por_perfil", {}).values())

    def _valor_item(
        self,
        item: Dict,
        fte: float = 0.0,
        semanas: float = 4.33,
        horas: float = 42.0,
    ) -> float:
        costo = float(item.get("costo", 0))
        if int(item.get("costo_totalizado", 0)) == 1:
            return costo

        formula = item.get("formula_cantidad")
        if formula == "horas_productivas":
            # Excel V2-8: 'Condiciones Cadena A'!G166 = semanas×horas×(1−ausent)×FTE×60×uso×min
            # pct_ausentismo viene de Panel!C19 (datos_operativos) — siempre actualizado.
            # pct_uso_recurso=50%, pct_costo_minuto=2%: constantes del Excel; opcionales en el item.
            pct_uso = float(item.get("pct_uso_recurso", 0.5))
            pct_min = float(item.get("pct_costo_minuto", 0.02))
            cantidad = semanas * horas * (1.0 - self._pct_ausentismo) * fte * 60.0 * pct_uso * pct_min
            return costo * cantidad

        if formula == "rotacion":
            # Excel V2-8: 'Condiciones Cadena A'!G168 = FTE × Panel!C20 (pct_rotacion)
            return costo * fte * self._pct_rotacion

        return costo * float(item.get("cantidad", 0))
