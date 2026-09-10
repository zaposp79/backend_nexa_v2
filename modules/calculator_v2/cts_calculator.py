"""
Cálculo de Cost-to-Serve por perfil para Cadena A.

Excel V2-8: 'Visión Cost To Serve' — Estructura del Equipo (filas 122-178)
  - Payroll: salario cargado (costo empresa) + crucero por perfil
  - No Payroll: OPEX IT + Inversiones + Costos Fijos x Estación por perfil
  - Financiero: componente_financiero_total asignado proporcionalmente a costo_directo
  - Ingreso teórico por perfil: costo_total / (1 - margen) [fórmula I160 del Excel CTS]
  - Tarifa x FTE: ingreso_teorico / fte
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .nomina_calculator import calcular_costo_empresa, NominaCalculator


class CTSCalculator:
    """Calcula el desglose de Cost-to-Serve por perfil de Cadena A."""

    def __init__(
        self,
        request_data: Dict[str, Any],
        costo_fijo_por_estacion: float = 0.0,
    ) -> None:
        cadena_a = request_data.get("condiciones_cadena_a") or {}
        self._perfiles: List[Dict] = cadena_a.get("perfiles", [])
        self._inversiones: List[Dict] = cadena_a.get("inversiones", [])
        self._costo_fijo_estacion = costo_fijo_por_estacion
        indexacion = request_data.get("volumetria", {}).get("indexacion", {})
        self._tasa_interes = float(indexacion.get("tasa_interes_mensual", 0.0))
        # Tarifa global por estación (Panel de Control General C17)
        # Excel V2-8: 'Condiciones Cadena A'!E153 = Panel!C17 × FTE
        self._crucero_base = float(request_data.get("datos_operativos", {}).get("crucero", 0.0))
        # Reglas de negocio (Panel de Control General C67-C70)
        # Excel V2-8 · 'Visión Cost To Serve'!I160 = I159/((1-C63)*(1-C67)*(1-C68)*(1-C69)*(1-C70))
        reglas = request_data.get("reglas_negocio", {})
        self._cont_op = self._extract_regla(reglas.get("contingencia_operativa", 0))
        self._cont_com = self._extract_regla(reglas.get("contingencia_comercial", 0))
        self._markup = self._extract_regla(reglas.get("markup", 0))
        dv = reglas.get("descuento_volumen", {})
        self._descuento = float(dv.get("valor", 0)) if isinstance(dv, dict) else float(dv or 0)

    @staticmethod
    def _extract_regla(field: Any) -> float:
        if isinstance(field, dict):
            return float(field.get("valor", 0))
        return float(field) if field is not None else 0.0

    def calcular(
        self,
        margen: float,
        componente_financiero_total: float,
        nomina_base: float = 0.0,
        componentes_fin: Optional[Dict[str, float]] = None,
        estructura_por_perfil: Optional[Dict[str, float]] = None,
        comisiones_estructura_pp: Optional[Dict[str, float]] = None,
        costos_nominalizados_pp: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[Dict[str, Any]]:
        """Desglose CTS por perfil.

        Args:
            margen: Margen objetivo Cadena A (ej. 0.18).
            componente_financiero_total: ICA + GMF + Comisión + Pólizas (una vez cada uno).
                Se asigna por perfil proporcional a costo_directo.
            nomina_base: Nómina total del NominaCalculator (incluye agentes + staff ratios).
                Permite distribuir el overhead de supervisores/coordinadores por FTE.
                Si es 0, se usa solo costo_empresa_agente (sin overhead de ratios).
            componentes_fin: Desglose individual del financiero:
                {'ica': float, 'gmf': float, 'polizas': float, 'comision': float, 'financiacion': float}
                Si None, el total se asigna pro-rata pero sin desglose.

        Returns:
            Lista de dicts con CTS desglosado por perfil.
        """
        n = len(self._perfiles)
        if n == 0:
            return []

        inversiones_por_perfil = self._inversiones_por_perfil(n)

        # Overhead de staff ratios por FTE (supervisores, coordinadores, directores)
        # Excel V2-8 CTS F173: Costo Empresa Agente Básico (sin ratios staff)
        # Excel V2-8 CTS F139: Nomina Loaded = costo_empresa + ratios_overhead × FTE
        total_costo_empresa_agentes = sum(
            calcular_costo_empresa(float(p.get("salario_base", 0)), float(p.get("comision_mensual", 0)))
            * float(p.get("fte", 0))
            for p in self._perfiles
        )
        fte_total = sum(float(p.get("fte", 0)) for p in self._perfiles)
        # nomina_base (de NominaCalculator) incluye crucero; hay que excluirlo antes de calcular
        # el overhead de staff ratios, porque crucero se suma por separado a cada perfil.
        # Excel V2-8 CTS F139: Nomina Loaded = costo_empresa_agente + staff_overhead (sin crucero)
        # Excel V2-8 CTS F138: Payroll = Nomina Loaded + Crucero
        total_crucero = sum(
            (self._crucero_base or float((p.get("capacitacion") or {}).get("crucero_mensual", 0)))
            * float(p.get("fte", 0))
            for p in self._perfiles
        )
        nomina_sin_crucero = max(0.0, nomina_base - total_crucero)
        overhead_per_fte = (
            (nomina_sin_crucero - total_costo_empresa_agentes) / max(fte_total, 1)
            if nomina_sin_crucero > total_costo_empresa_agentes
            else 0.0
        )

        _fin = componentes_fin or {}
        fte_total_deal = max(sum(float(p.get("fte", 0)) for p in self._perfiles), 1)

        # Primera pasada: payroll + no_payroll + costo_directo por perfil
        perfiles_cts: List[Dict] = []
        costo_directo_total = 0.0

        for i, perfil in enumerate(self._perfiles):
            fte = float(perfil.get("fte", 0))
            salario = float(perfil.get("salario_base", 0))
            comision = float(perfil.get("comision_mensual", 0))
            cap = perfil.get("capacitacion") or {}
            crucero_unit = self._crucero_base or float(cap.get("crucero_mensual", 0))
            perfil_nombre = str(perfil.get("nombre", f"perfil{i + 1}"))

            recargo_fte = NominaCalculator._recargo_perfil(perfil)
            costo_fte = calcular_costo_empresa(salario, comision, recargos=recargo_fte)
            salario_cargado = costo_fte * fte
            # Excel NL SUM(C43:C80) per perfil: usar costo real de estructura por perfil cuando
            # está disponible; si no, fallback a distribución uniforme por FTE.
            if estructura_por_perfil is not None:
                estructura = estructura_por_perfil.get(perfil_nombre, 0.0)
                nomina_loaded = salario_cargado + estructura
            else:
                nomina_loaded = salario_cargado + overhead_per_fte * fte
            crucero = crucero_unit * fte
            payroll = nomina_loaded + crucero
            # salario_variable = comisiones brutas agente + comisiones de estructura por perfil
            # Excel CTS I141: incluye comisiones de todos los cargos del perfil, no solo agentes
            com_estructura = (comisiones_estructura_pp or {}).get(perfil_nombre, 0.0)
            salario_variable = comision * fte + com_estructura
            salario_fijo = nomina_loaded - salario_variable

            opex_items = perfil.get("opex_fijo", {}).get("items", [])
            opex_it = sum(self._valor_item(item) for item in opex_items)

            inv = inversiones_por_perfil[i]

            estaciones = float(perfil.get("estaciones_presenciales", 0))
            costos_fijos = self._costo_fijo_estacion * estaciones

            no_payroll = opex_it + inv + costos_fijos
            costo_directo = payroll + no_payroll
            costo_directo_total += costo_directo

            # Pesos de staffing: participación del perfil en el equipo total
            peso_staff_agente = round(fte / fte_total_deal, 4) if fte_total_deal > 0 else 0.0

            _nom_pp = (costos_nominalizados_pp or {}).get(perfil_nombre, {})
            _cap_ini  = _nom_pp.get("capacitacion_inicial", 0.0)
            _cap_rot  = _nom_pp.get("capacitacion_rotacion", 0.0)
            _examenes = _nom_pp.get("examenes_medicos", 0.0)
            _estudios = _nom_pp.get("estudios_seguridad", 0.0)
            # Excel Payroll = Nomina Loaded + Cap Ini + Cap Rot + Exámenes + Estudios + Crucero
            payroll_total = nomina_loaded + crucero + _cap_ini + _cap_rot + _examenes + _estudios
            costo_directo_real = payroll_total + no_payroll
            costo_directo_total += costo_directo_real - costo_directo  # ajustar acumulado
            perfiles_cts.append({
                "nombre": perfil_nombre,
                "canal": str(perfil.get("canal", "")),
                "modalidad": str(perfil.get("modalidad", "")),
                "fte": int(fte),
                "nomina_loaded": round(nomina_loaded, 2),
                "salario_fijo": round(salario_fijo, 2),
                "salario_variable": round(salario_variable, 2),
                "capacitacion_inicial": round(_cap_ini, 2),
                "capacitacion_rotacion": round(_cap_rot, 2),
                "examenes": round(_examenes, 2),
                "estudios_seguridad": round(_estudios, 2),
                "crucero": round(crucero, 2),
                "salario_cargado": round(salario_cargado, 2),
                "payroll": round(payroll_total, 2),
                "nomina": round(salario_cargado, 2),  # costo empresa agente (sin overhead)
                "opex_it": round(opex_it, 2),
                "inversiones": round(inv, 2),
                "costos_fijos": round(costos_fijos, 2),
                "no_payroll": round(no_payroll, 2),
                "costo_directo": round(costo_directo_real, 2),
                "peso_staff_agente": peso_staff_agente,
                "_costo_directo_raw": costo_directo_real,
            })

        # Segunda pasada: financiero asignado pro-rata + totales por perfil
        # Excel V2-8 · 'Visión Cost To Serve'!I160 = I159/((1-C63)*(1-C67)*(1-C68)*(1-C69)*(1-C70))
        # C63=margen, C67=cont_op, C68=cont_com, C69=markup, C70=descuento (Panel de Control General)
        fm = (
            (1.0 - margen)
            * (1.0 - self._cont_op)
            * (1.0 - self._cont_com)
            * (1.0 - self._markup)
            * (1.0 - self._descuento)
        )
        if fm <= 0:
            fm = 1.0 - margen if margen < 1.0 else 1.0

        for p in perfiles_cts:
            weight = (p["_costo_directo_raw"] / costo_directo_total) if costo_directo_total > 0 else 0.0
            fin = componente_financiero_total * weight
            # Desglose individual del financiero pro-rata al mismo weight
            ica = _fin.get("ica", 0.0) * weight
            gmf = _fin.get("gmf", 0.0) * weight
            polizas = _fin.get("polizas", 0.0) * weight
            comision_admin = _fin.get("comision", 0.0) * weight
            costo_financiacion = _fin.get("financiacion", 0.0) * weight

            costo_total = p["costo_directo"] + fin
            ingreso = costo_total / fm
            fte = max(p["fte"], 1)

            p.update({
                "ica": round(ica, 2),
                "gmf": round(gmf, 2),
                "polizas": round(polizas, 2),
                "comision_administracion": round(comision_admin, 2),
                "costo_financiacion": round(costo_financiacion, 2),
                "financiero": round(fin, 2),
                "costo_total": round(costo_total, 2),
                "costo_directo_por_fte": round(p["costo_directo"] / fte, 2),
                "costo_total_por_fte": round(costo_total / fte, 2),
                "ingreso": round(ingreso, 2),
                "ingreso_total": round(ingreso, 2),
                "tarifa_fte": round(ingreso / fte, 2),
            })
            del p["_costo_directo_raw"]

        return perfiles_cts

    def _inversiones_por_perfil(self, n_perfiles: int) -> List[float]:
        """Costo mensual de inversiones por perfil con factor de interés."""
        result = [0.0] * n_perfiles

        for inv in self._inversiones:
            es_precio_total = bool(inv.get("es_precio_total", False))
            precio_compra = float(inv.get("precio_compra", 0))
            precio_mensual = float(inv.get("precio_mensual", 0))
            meses = float(inv.get("meses_diferimiento", 1)) or 1.0

            if "por_perfil" in inv:
                for pp in inv["por_perfil"]:
                    idx = int(pp.get("indice_perfil", -1))
                    qty = float(pp.get("valor") or pp.get("cantidad") or 0)
                    if 0 <= idx < n_perfiles and qty > 0:
                        if es_precio_total:
                            result[idx] += (precio_compra / meses) * qty
                        else:
                            result[idx] += precio_mensual * qty
            else:
                for i in range(n_perfiles):
                    qty = float(inv.get(f"perfil{i + 1}", 0))
                    if qty > 0:
                        if es_precio_total:
                            result[i] += (precio_compra / meses) * qty
                        else:
                            result[i] += precio_mensual * qty

        factor = 1.0 + self._tasa_interes
        return [v * factor for v in result]

    @staticmethod
    def _valor_item(item: Dict) -> float:
        costo = float(item.get("costo", 0))
        cantidad = float(item.get("cantidad", 0))
        if int(item.get("costo_totalizado", 0)) == 1:
            return costo
        return costo * cantidad
