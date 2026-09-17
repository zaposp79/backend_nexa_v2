"""
Cálculo de nómina para Cadena A.

Reglas del Excel Nexa - Pricing - Simulador - V2-8.xlsx (Inputs de Nomina, fila 36):
  Salud: 8.5%, Pensión: 12%, ARL: 0.522%, Caja: 4%, ICBF+Sena: 4%
  Cesantías: 8.33%, Primas: 8.33%, Interés Cesantía: 12%, Vacaciones: 4.17%
  Salario Integral (>10 SMLV): contribuciones sobre el 70% de la base.
  Para Salario Integral: Cesantías = Primas = 0.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# ── Tabla estática: cargo → grupo (Excel Graficos AM5:AN28) ─────────────────
# Fuente: 001_ElTiempo.xlsx · Graficos!AM5:AN28
# Los nombres se normalizan a minúsculas para el matching con position_name.
_GRUPOS_ORDEN: List[str] = ["Operaciones", "Recursos humanos", "Otros"]

_CARGO_GRUPO_MAP: Dict[str, str] = {
    # Operaciones (14 cargos)
    "director de cuentas":                            "Operaciones",
    "director de performance":                        "Operaciones",
    "analista profesional afac":                      "Operaciones",
    "validador":                                      "Operaciones",
    "gtr":                                            "Operaciones",
    "reporting":                                      "Operaciones",
    "works force":                                    "Operaciones",
    "jefe de operación":                              "Operaciones",
    "lider de planeación operativa":                  "Operaciones",
    "lider de experiencia de cliente y performance":  "Operaciones",
    "jefe comercial regional":                        "Operaciones",
    "cargos adicionales":                             "Operaciones",
    "monitor de calidad":                             "Operaciones",
    "supervisor":                                     "Operaciones",
    # Recursos humanos (10 cargos — incluye variantes (Rotación) e (Inicial) de Excel Graficos!AM5:AN28)
    "lider de entrenamiento":                         "Recursos humanos",
    "formadores":                                     "Recursos humanos",
    "analista prof. de selección":                    "Recursos humanos",
    "analista prof. de selección (rotación)":         "Recursos humanos",
    "analista prof. de selección (inicial)":          "Recursos humanos",
    "analista 1 de reclutamiento":                    "Recursos humanos",
    "analista 1 de reclutamiento (rotación)":         "Recursos humanos",
    "analista 1 de reclutamiento (inicial)":          "Recursos humanos",
    "aprendiz sena":                                  "Recursos humanos",
    "inclusión":                                      "Recursos humanos",
    # Otros (2 cargos)
    "especialista de proyectos":                      "Otros",
    "analista 2 service desk":                        "Otros",
}

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


def calcular_costo_empresa_sena(
    salario_base: float,
    comision: float = 0.0,
    smlv: float = _SMLV_DEFAULT,
    aux_transporte: float = _AUX_TRANSPORTE,
) -> float:
    """Costo mensual para Aprendiz SENA e Inclusión (solo t_haberes).

    Excel V2-8: INP!W59 = H59 = salario + comision + aux_transporte.
    J/N/P/Q/R/S/T/U/V = 0 (sin carga parafiscal ni prestacional).
    Cuando hay comisión en CCA!F65/F66, se suma al costo como parte de t_haberes.
    """
    if salario_base <= 0:
        return 0.0
    # Excel V2-8 · INP!G59 = IF(AND(F59<2*C4, F59>0), C5, 0)
    # F59 = T.Imponible = salario + comision (NO solo salario_base).
    t_imponible = salario_base + comision
    aux = aux_transporte if 0 < t_imponible < 2 * smlv else 0.0
    # Excel V2-8 · INP!W59 = C59 + D59 + G59 = salario + comision + aux
    return salario_base + comision + aux


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
        self._cadena_a = request_data.get("condiciones_cadena_a") or {}

    def calcular(self) -> float:
        return (
            self._nomina_agentes()
            + self._nomina_estructura()
            + self._crucero()
            + self._capacitacion_rotacion()
            + self._cargos_adicionales()
            + self._examenes_medicos()
            + self._estudios_seguridad()
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
        # Los cargos adicionales son salario fijo (comision=0) → se incluyen en nomina_loaded.
        # Excel V2-8: NominaLoaded!C69 forma parte del bloque de nómina, no es un rubro aparte.
        nomina_loaded = self._nomina_agentes() + self._nomina_estructura() + self._cargos_adicionales()
        salario_variable = self._nomina_comisiones_brutas()
        return {
            "nomina_loaded": nomina_loaded,
            "crucero_total": self._crucero(),
            "capacitacion_rotacion": self._capacitacion_rotacion(),
            "capacitacion_inicial": self._capacitacion_inicial(),
            "cargos_adicionales": 0.0,
            "examenes_medicos": self._examenes_medicos(),
            "estudios_seguridad": self._estudios_seguridad(),
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
        comision × cantidad por cargo de estructura.

        SENA e Inclusión usan la misma fórmula de cantidad que desglose_por_cargo():
          SENA_qty  = (regular_hc + cargos_add_hc) / ratio_sena
          Incl_qty  = (regular_hc + cargos_add_hc + aprendiz_qty) / ratio_incl
        No _calcular_cantidad() (que usa FTE/ratio — incorrecto para estos cargos).
        """
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        detalle: List[Dict] = self._cadena_a.get("detalle_nomina", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])
        detalle_map = {c["cargo"].strip().lower(): c for c in detalle}
        datos_op = self._req.get("datos_operativos", {})
        total_fte = sum(float(p.get("fte", 0)) for p in perfiles)

        # Complejidad (mismo método que desglose_por_cargo)
        _cplx = self._cadena_a.get("ratios", {}).get("complejidad") or ""
        if isinstance(_cplx, dict):
            _cplx = _cplx.get("label") or _cplx.get("valor") or ""
        complejidad_str = str(_cplx).strip().lower()
        complejidad_factor = {"alta": 0.5, "media": 0.5, "baja": 0.20}.get(complejidad_str, 0.20)

        # Comisiones brutas de agentes (FTE × comision_mensual)
        total = sum(
            float(p.get("comision_mensual", 0)) * float(p.get("fte", 0))
            for p in perfiles
        )
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        cargos_add_hc = sum(
            sum(float(c.get("cantidad", 0)) for c in (p.get("cargos_adicionales") or [])
                if (c.get("nombre") or "").strip())
            for p in perfiles
        )

        # Acumular regular_hc (mismo que desglose_por_cargo) para SENA/Inclusión.
        regular_hc = 0.0
        fila_aprendiz = fila_inclusion = fila_especialista = None

        for fila in ratios_filas:
            nombre = fila.get("position_name") or fila.get("position_id", "")
            nombre_lower = nombre.lower()

            # Diferir cargos especiales.
            if "aprendiz sena" in nombre_lower:
                fila_aprendiz = fila
                continue
            if "inclus" in nombre_lower:
                fila_inclusion = fila
                continue
            if "especialista" in nombre_lower:
                fila_especialista = fila
                continue

            if not fila.get("incluido", False):
                continue

            _is_rot = "otaci" in nombre_lower and "(" in nombre
            cantidad = self._calcular_cantidad(
                fila, perfiles, pct_rotacion=pct_rotacion, is_rotation=_is_rot
            )
            if cantidad > 0:
                regular_hc += cantidad

            # Agente Básico 1 ya contabilizado por FTE arriba — no sumar comisión aquí.
            if fila.get("tipo", "").lower() == "agente":
                continue

            cargo_data = self._resolver_cargo(fila, detalle_map)
            if not cargo_data or cantidad <= 0:
                continue
            comision_c = float(cargo_data.get("comision", 0))
            if comision_c <= 0:
                continue
            total += comision_c * cantidad

        # Especialista: factor mixto personalizado/pct_fte (mismo fix que desglose_por_cargo).
        if fila_especialista is not None and fila_especialista.get("incluido", False):
            cargo_data = self._resolver_cargo(fila_especialista, detalle_map)
            if cargo_data:
                comision_esp = float(cargo_data.get("comision", 0))
                if comision_esp > 0:
                    factor_total = 0.0
                    for pr in fila_especialista.get("por_perfil", []):
                        try:
                            pval = float(pr.get("personalizado") or 0)
                        except (TypeError, ValueError):
                            pval = 0.0
                        if pval > 0:
                            factor_total += pval
                        else:
                            idx = pr.get("indice_perfil", 0)
                            if idx < len(perfiles) and total_fte > 0:
                                factor_total += float(perfiles[idx].get("fte", 0)) / total_fte
                    if factor_total <= 0:
                        factor_total = 1.0
                    total += comision_esp * factor_total

        # SENA: cantidad = (regular_hc + cargos_add_hc) / ratio (misma fórmula que desglose_por_cargo).
        aprendiz_qty = 0.0
        aprendiz_hc_pp: Dict[int, float] = {}
        if fila_aprendiz is not None and fila_aprendiz.get("incluido", False):
            cargo_data = self._resolver_cargo(fila_aprendiz, detalle_map)
            if cargo_data:
                comision_ap = float(cargo_data.get("comision", 0))
                any_personalizado_ap = any(
                    float(pr.get("personalizado") or 0) > 0
                    for pr in fila_aprendiz.get("por_perfil", [])
                )
                if any_personalizado_ap:
                    for pr in fila_aprendiz.get("por_perfil", []):
                        try:
                            pval = float(pr.get("personalizado") or 0)
                        except (TypeError, ValueError):
                            pval = 0.0
                        indice = pr.get("indice_perfil", 0)
                        if pval > 0:
                            aprendiz_hc_pp[indice] = pval
                            aprendiz_qty += pval
                        else:
                            try:
                                ratio_val = float(str(pr.get("ratio", "0")).strip() or "0")
                            except ValueError:
                                ratio_val = 0.0
                            if ratio_val > 0 and indice < len(perfiles) and total_fte > 0:
                                fte_i = float(perfiles[indice].get("fte", 0))
                                cadd_i = sum(
                                    float(c.get("cantidad", 0))
                                    for c in (perfiles[indice].get("cargos_adicionales") or [])
                                    if (c.get("nombre") or "").strip()
                                )
                                q = (regular_hc * fte_i / total_fte + cadd_i) / ratio_val
                                aprendiz_hc_pp[indice] = q
                                aprendiz_qty += q
                else:
                    ratio_ap = self._get_ratio_global(fila_aprendiz)
                    if ratio_ap > 0:
                        aprendiz_qty = (regular_hc + cargos_add_hc) / ratio_ap
                if comision_ap > 0:
                    total += comision_ap * aprendiz_qty

        # Inclusión: cantidad = (regular_hc + cargos_add_hc + aprendiz_qty) / ratio.
        if fila_inclusion is not None and fila_inclusion.get("incluido", False):
            cargo_data = self._resolver_cargo(fila_inclusion, detalle_map)
            if cargo_data:
                comision_inc = float(cargo_data.get("comision", 0))
                if comision_inc > 0:
                    any_personalizado_inc = any(
                        float(pr.get("personalizado") or 0) > 0
                        for pr in fila_inclusion.get("por_perfil", [])
                    )
                    if any_personalizado_inc:
                        inclusion_qty = 0.0
                        for pr in fila_inclusion.get("por_perfil", []):
                            try:
                                pval = float(pr.get("personalizado") or 0)
                            except (TypeError, ValueError):
                                pval = 0.0
                            indice = pr.get("indice_perfil", 0)
                            if pval > 0:
                                inclusion_qty += pval
                            else:
                                try:
                                    ratio_val = float(str(pr.get("ratio", "0")).strip() or "0")
                                except ValueError:
                                    ratio_val = 0.0
                                if ratio_val > 0 and indice < len(perfiles) and total_fte > 0:
                                    fte_i = float(perfiles[indice].get("fte", 0))
                                    cadd_i = sum(
                                        float(c.get("cantidad", 0))
                                        for c in (perfiles[indice].get("cargos_adicionales") or [])
                                        if (c.get("nombre") or "").strip()
                                    )
                                    aprendiz_i = aprendiz_hc_pp.get(
                                        indice,
                                        aprendiz_qty * fte_i / total_fte if total_fte > 0 else 0.0,
                                    )
                                    inclusion_qty += (regular_hc * fte_i / total_fte + cadd_i + aprendiz_i) / ratio_val
                    else:
                        ratio_inc = self._get_ratio_global(fila_inclusion)
                        inclusion_qty = (
                            (regular_hc + cargos_add_hc + aprendiz_qty) / ratio_inc
                            if ratio_inc > 0 else 0.0
                        )
                    total += comision_inc * inclusion_qty

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
            # Cargos adicionales del perfil — misma tarifa crucero por estación
            for cargo in perfil.get("cargos_adicionales") or []:
                if not (cargo.get("nombre") or "").strip():
                    continue
                cantidad = float(cargo.get("cantidad", 0.0))
                if cantidad > 0:
                    total += crucero_unit * cantidad
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
        datos_op = self._req.get("datos_operativos", {})
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        duracion_meses = float(datos_op.get("duracion_meses", 1) or 1)

        total_fte = sum(float(p.get("fte", 0)) for p in perfiles)
        _cplx = self._cadena_a.get("ratios", {}).get("complejidad") or ""
        if isinstance(_cplx, dict):
            # Frontend envía {"label": "Media", "value": 0.5} — leer label para el lookup
            _cplx = _cplx.get("label") or _cplx.get("valor") or ""
        complejidad_str = str(_cplx).strip().lower()
        # Excel V2-8 · NL!A66: IFS(CCA!B101="Baja",20%,"Media",50%,"Alta",50%)
        # Default 0.20 (Baja) cuando null — coincide con el comportamiento estándar del Excel.
        complejidad_factor = {"alta": 0.5, "media": 0.5, "baja": 0.20}.get(complejidad_str, 0.20)

        # Cantidad directa de cargos adicionales (CCA!E27/E31/E35) sumada de todos los perfiles.
        cargos_add_hc = sum(
            sum(float(c.get("cantidad", 0)) for c in (p.get("cargos_adicionales") or [])
                if (c.get("nombre") or "").strip())
            for p in perfiles
        )

        sena_unit_cost = float(datos_op.get("costo_empresa_sena") or 0.0)

        result: Dict[str, float] = {}
        fila_aprendiz = fila_inclusion = fila_especialista = None
        # Headcount total de cargos regulares activos (espejo de CCA SUM(E78:E98)).
        regular_hc = 0.0
        # Headcount por perfil — necesario para la fórmula SENA/Inclusión en el caso mixto
        # donde algunos perfiles tienen personalizado (no proporcional a FTE) y otros usan
        # fórmula. Sin esto, la distribución regular_hc×fte_i/total_fte contamina a los
        # perfiles fórmula con el exceso de personalizado de otros perfiles.
        regular_hc_pp: Dict[int, float] = {}

        for fila in ratios_filas:
            nombre = fila.get("position_name") or fila.get("position_id", "")
            if not nombre:
                continue
            nombre_lower = nombre.lower()

            # Defer cargos especiales — se procesan en fases posteriores.
            if "aprendiz sena" in nombre_lower:
                fila_aprendiz = fila
                result.setdefault(nombre, 0.0)
                continue
            if "inclus" in nombre_lower:
                fila_inclusion = fila
                result.setdefault(nombre, 0.0)
                continue
            if "especialista" in nombre_lower:
                fila_especialista = fila
                result.setdefault(nombre, 0.0)
                continue

            if not fila.get("incluido", False):
                result.setdefault(nombre, 0.0)
                continue

            # Cantidad (con ajuste de rotación por perfil si aplica).
            # Excel CCA!E91:E92 = (FTE/ratio) × Panel!C20 para cargos "(Rotación)".
            # _calcular_cantidad aplica pct_rotacion solo a los perfils SIN personalizado,
            # permitiendo mixes parciales (un perfil override + otro auto).
            _is_rot = "otaci" in nombre_lower and "(" in nombre
            cantidad = self._calcular_cantidad(
                fila, perfiles, pct_rotacion=pct_rotacion, is_rotation=_is_rot
            )

            # Acumular headcount para Aprendiz/Inclusión (incluye Agente Básico 1 ratio=1).
            if cantidad > 0:
                regular_hc += cantidad

            # Acumular headcount POR PERFIL para fórmula SENA/Inclusión mixta.
            for _pr in fila.get("por_perfil", []):
                _idx = _pr.get("indice_perfil", 0)
                if _idx >= len(perfiles):
                    continue
                try:
                    _pval = float(_pr.get("personalizado") or 0)
                except (TypeError, ValueError):
                    _pval = 0.0
                if _pval > 0:
                    regular_hc_pp[_idx] = regular_hc_pp.get(_idx, 0.0) + _pval
                else:
                    try:
                        _ratio_pr = float(str(_pr.get("ratio", "0")).strip() or "0")
                    except ValueError:
                        _ratio_pr = 0.0
                    _fte_pr = float(perfiles[_idx].get("fte", 0))
                    _rot_factor = pct_rotacion if _is_rot else 1.0
                    _q_pr = (_fte_pr / _ratio_pr * _rot_factor) if _ratio_pr > 0 else 0.0
                    regular_hc_pp[_idx] = regular_hc_pp.get(_idx, 0.0) + _q_pr

            # Agente Básico 1 (tipo="Agente") se contabiliza directamente por FTE en CTS —
            # excluir del overhead de estructura para evitar doble conteo.
            if fila.get("tipo", "").lower() == "agente":
                result.setdefault(nombre, 0.0)
                continue

            cargo_data = self._resolver_cargo(fila, detalle_map)
            if not cargo_data or cantidad <= 0:
                result.setdefault(nombre, 0.0)
                continue
            salario = float(cargo_data.get("salario", 0))
            comision = float(cargo_data.get("comision", 0))
            costo = calcular_costo_empresa(salario, comision) * cantidad
            # Excel NL!C54 = costo_empresa × (FTE/ratio) × (1/Panel!C11) para "(Inicial)".
            if "nicial" in nombre_lower and "(" in nombre:
                costo /= duracion_meses
            result[nombre] = result.get(nombre, 0.0) + costo

        # ── Aprendiz SENA ─────────────────────────────────────────────────────
        # Excel CCA!E99 = (SUM(E78:E98) + E27+E31+E35) / E126
        # Si por_perfil[i].personalizado > 0 → usa ese valor directo (celda editada en Excel).
        # Perfiles sin personalizado: fórmula proporcional (regular_hc × fte_i/total_fte) / ratio.
        aprendiz_cantidad = 0.0
        # aprendiz_hc_pp tracks per-profile SENA FTE for use in Inclusión formula.
        aprendiz_hc_pp: Dict[int, float] = {}
        if fila_aprendiz is not None:
            nombre_ap = fila_aprendiz.get("position_name") or fila_aprendiz.get("position_id", "")
            if fila_aprendiz.get("incluido", False):
                any_personalizado_ap = any(
                    float(pr.get("personalizado") or 0) > 0
                    for pr in fila_aprendiz.get("por_perfil", [])
                )
                if any_personalizado_ap:
                    for pr in fila_aprendiz.get("por_perfil", []):
                        try:
                            pval = float(pr.get("personalizado") or 0)
                        except (TypeError, ValueError):
                            pval = 0.0
                        indice = pr.get("indice_perfil", 0)
                        if pval > 0:
                            aprendiz_hc_pp[indice] = pval
                            aprendiz_cantidad += pval
                        else:
                            try:
                                ratio_val = float(str(pr.get("ratio", "0")).strip() or "0")
                            except ValueError:
                                ratio_val = 0.0
                            if ratio_val > 0 and indice < len(perfiles) and total_fte > 0:
                                fte_i = float(perfiles[indice].get("fte", 0))
                                cadd_i = sum(
                                    float(c.get("cantidad", 0))
                                    for c in (perfiles[indice].get("cargos_adicionales") or [])
                                    if (c.get("nombre") or "").strip()
                                )
                                # Usar headcount real por perfil en lugar de distribución proporcional.
                                # regular_hc × fte_i/total_fte es incorrecto cuando otro perfil tiene
                                # personalizado no proporcional (ej. Validador P1=4 vs fórmula=0.2).
                                rhc_i = regular_hc_pp.get(indice, regular_hc * fte_i / total_fte)
                                q = (rhc_i + cadd_i) / ratio_val
                                aprendiz_hc_pp[indice] = q
                                aprendiz_cantidad += q
                else:
                    ratio_ap = self._get_ratio_global(fila_aprendiz)
                    if ratio_ap > 0:
                        aprendiz_cantidad = (regular_hc + cargos_add_hc) / ratio_ap

                cargo_data = self._resolver_cargo(fila_aprendiz, detalle_map)
                if cargo_data and aprendiz_cantidad > 0:
                    # Excel V2-8 · INP!W59 = salario + comision + aux (solo t_haberes).
                    _smlv = float(datos_op.get("smlv") or _SMLV_DEFAULT)
                    _aux_tr = float(datos_op.get("aux_transporte") or _AUX_TRANSPORTE)
                    _sal_ap = float(cargo_data.get("salario", 0))
                    _com_ap = float(cargo_data.get("comision", 0))
                    _costo_ap = calcular_costo_empresa_sena(_sal_ap, _com_ap, _smlv, _aux_tr)
                    result[nombre_ap] = (_costo_ap or sena_unit_cost) * aprendiz_cantidad

        # ── Inclusión ─────────────────────────────────────────────────────────
        # Excel CCA!E100 = (SUM(E78:E99) + E27+E31+E35) / E127  (incluye Aprendiz SENA)
        # Excel V2-8: INP!D60 = Inclusión usa su propia comisión de CCA!F66 (no la del Especialista).
        # INP!W60 = H60 = salario + comision + aux (solo t_haberes, igual que SENA).
        if fila_inclusion is not None:
            nombre_inc = fila_inclusion.get("position_name") or fila_inclusion.get("position_id", "")
            if fila_inclusion.get("incluido", False):
                cargo_data = self._resolver_cargo(fila_inclusion, detalle_map)
                costo_inc_unit = 0.0
                if cargo_data:
                    # Excel V2-8 · INP!W60 = C60 + D60 + G60 = salario + comision_inclusión + aux.
                    _smlv = float(datos_op.get("smlv") or _SMLV_DEFAULT)
                    _aux_tr = float(datos_op.get("aux_transporte") or _AUX_TRANSPORTE)
                    _sal_inc = float(cargo_data.get("salario", 0))
                    _com_inc = float(cargo_data.get("comision", 0))
                    costo_inc_unit = calcular_costo_empresa_sena(_sal_inc, _com_inc, _smlv, _aux_tr)

                any_personalizado_inc = any(
                    float(pr.get("personalizado") or 0) > 0
                    for pr in fila_inclusion.get("por_perfil", [])
                )
                if any_personalizado_inc:
                    inclusion_cantidad = 0.0
                    for pr in fila_inclusion.get("por_perfil", []):
                        try:
                            pval = float(pr.get("personalizado") or 0)
                        except (TypeError, ValueError):
                            pval = 0.0
                        if pval > 0:
                            inclusion_cantidad += pval
                        else:
                            indice = pr.get("indice_perfil", 0)
                            try:
                                ratio_val = float(str(pr.get("ratio", "0")).strip() or "0")
                            except ValueError:
                                ratio_val = 0.0
                            if ratio_val > 0 and indice < len(perfiles) and total_fte > 0:
                                fte_i = float(perfiles[indice].get("fte", 0))
                                cadd_i = sum(
                                    float(c.get("cantidad", 0))
                                    for c in (perfiles[indice].get("cargos_adicionales") or [])
                                    if (c.get("nombre") or "").strip()
                                )
                                # Use exact per-profile SENA FTE when available (mixed personalizado case).
                                aprendiz_i = aprendiz_hc_pp.get(
                                    indice,
                                    aprendiz_cantidad * fte_i / total_fte if total_fte > 0 else 0.0,
                                )
                                # Igual que SENA: usar headcount real por perfil en lugar de distribución
                                # proporcional para evitar contaminación entre perfiles con personalizado.
                                rhc_i = regular_hc_pp.get(indice, regular_hc * fte_i / total_fte)
                                inclusion_cantidad += (rhc_i + cadd_i + aprendiz_i) / ratio_val
                else:
                    ratio_inc = self._get_ratio_global(fila_inclusion)
                    inclusion_cantidad = (
                        (regular_hc + cargos_add_hc + aprendiz_cantidad) / ratio_inc if ratio_inc > 0 else 0.0
                    )

                if cargo_data and inclusion_cantidad > 0 and costo_inc_unit > 0:
                    result[nombre_inc] = costo_inc_unit * inclusion_cantidad

        # ── Especialista de Proyectos ─────────────────────────────────────────
        # Excel NL!C66 = costo_empresa × complejidad_factor × 3 × pct_perfil / Panel!C11
        # Si "personalizado" > 0 en por_perfil, se usa ese valor en lugar de pct_i=fte_i/total_fte.
        # El total es sum(factor_i): cuando no hay personalizado, sum(pct_i)=1; con personalizado,
        # puede diferir si el usuario deliberadamente ingresa valores distintos a la distribución FTE.
        if fila_especialista is not None:
            nombre_esp = fila_especialista.get("position_name") or fila_especialista.get("position_id", "")
            if fila_especialista.get("incluido", False) and total_fte > 0:
                cargo_data = self._resolver_cargo(fila_especialista, detalle_map)
                if cargo_data:
                    # Excel V2-8 · NL!C66 = INP!AM61 × complejidad × 3 × pct / Panel!C11.
                    # INP!AM61 incluye comisión (D61=500k) → CE con comisión completa.
                    costo_esp = self._get_costo_empresa(cargo_data)
                    # Mixed personalizado: profiles with personalizado use that value;
                    # profiles without use fte_i/total_fte. Sum = 1.0 when all formula-based.
                    factor_total = 0.0
                    for pr in fila_especialista.get("por_perfil", []):
                        try:
                            pval = float(pr.get("personalizado") or 0)
                        except (TypeError, ValueError):
                            pval = 0.0
                        if pval > 0:
                            factor_total += pval
                        else:
                            idx = pr.get("indice_perfil", 0)
                            if idx < len(perfiles) and total_fte > 0:
                                factor_total += float(perfiles[idx].get("fte", 0)) / total_fte
                    if factor_total <= 0:
                        factor_total = 1.0
                    # Excel V2-8 · P&G NL = zona1 (CE via NL!C66) + zona2 (raw commission via NL!C178).
                    # Esp aparece en AMBAS zonas: CE_with_commission×factor (zona1) + commission×factor (zona2).
                    # Motor NL debe incluir ambas para coincidir con Excel P&G NL.
                    comision_esp = float(cargo_data.get("comision", 0))
                    result[nombre_esp] = (
                        costo_esp * complejidad_factor * 3.0 * factor_total / duracion_meses
                        + comision_esp * factor_total
                    )

        return result

    def desglose_por_cargo_por_perfil(self) -> Dict[str, Dict[str, float]]:
        """Nómina por cargo desglosada POR PERFIL (excl. agente base).

        Retorna todos los cargos de estructura para cada perfil, incluyendo
        aquellos con valor 0 (no incluidos o sin cantidad).
        # Excel Graficos: AR5:BH28 — cada columna es un perfil activo del deal
        """
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        detalle: List[Dict] = self._cadena_a.get("detalle_nomina", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])
        detalle_map = {c["cargo"].strip().lower(): c for c in detalle}

        result: Dict[str, Dict[str, float]] = {
            p.get("nombre", f"perfil{i+1}"): {} for i, p in enumerate(perfiles)
        }

        datos_op = self._req.get("datos_operativos", {})
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        duracion_meses = float(datos_op.get("duracion_meses", 1) or 1)
        total_fte = sum(float(p.get("fte", 0)) for p in perfiles)
        _cplx = self._cadena_a.get("ratios", {}).get("complejidad") or ""
        if isinstance(_cplx, dict):
            # Frontend envía {"label": "Media", "value": 0.5} — leer label para el lookup
            _cplx = _cplx.get("label") or _cplx.get("valor") or ""
        complejidad_str = str(_cplx).strip().lower()
        # Excel V2-8 · NL!A66: IFS(CCA!B101="Baja",20%,"Media",50%,"Alta",50%)
        # Default 0.20 (Baja) cuando null — coincide con el comportamiento estándar del Excel.
        complejidad_factor = {"alta": 0.5, "media": 0.5, "baja": 0.20}.get(complejidad_str, 0.20)

        sena_unit_cost = float(datos_op.get("costo_empresa_sena") or 0.0)

        fila_aprendiz = fila_inclusion = fila_especialista = None
        # Headcount acumulado por índice de perfil para base de Aprendiz/Inclusión.
        regular_hc_pp: Dict[int, float] = {i: 0.0 for i in range(len(perfiles))}

        for fila in ratios_filas:
            cargo_nombre = fila.get("position_name") or fila.get("position_id", "")
            if not cargo_nombre:
                continue
            cargo_nombre_lower = cargo_nombre.lower()

            # Defer cargos especiales.
            if "aprendiz sena" in cargo_nombre_lower:
                fila_aprendiz = fila
                for pn in result:
                    result[pn].setdefault(cargo_nombre, 0.0)
                continue
            if "inclus" in cargo_nombre_lower:
                fila_inclusion = fila
                for pn in result:
                    result[pn].setdefault(cargo_nombre, 0.0)
                continue
            if "especialista" in cargo_nombre_lower:
                fila_especialista = fila
                for pn in result:
                    result[pn].setdefault(cargo_nombre, 0.0)
                continue

            costo_unit = 0.0
            if fila.get("incluido", False):
                cargo_data = self._resolver_cargo(fila, detalle_map)
                if cargo_data:
                    salario = float(cargo_data.get("salario", 0))
                    comision = float(cargo_data.get("comision", 0))
                    costo_unit = calcular_costo_empresa(salario, comision)

            for pr in fila.get("por_perfil", []):
                indice = pr.get("indice_perfil", 0)
                if indice >= len(perfiles):
                    continue
                perfil_nombre = perfiles[indice].get("nombre", f"perfil{indice+1}")
                if perfil_nombre not in result:
                    result[perfil_nombre] = {}

                if not fila.get("incluido", False):
                    result[perfil_nombre].setdefault(cargo_nombre, 0.0)
                    continue

                try:
                    personalizado = float(pr.get("personalizado") or 0)
                except (TypeError, ValueError):
                    personalizado = 0.0

                if personalizado > 0:
                    cantidad = personalizado
                else:
                    try:
                        ratio = float(str(pr.get("ratio", "0")).strip() or "0")
                    except ValueError:
                        ratio = 0.0
                    fte = float(perfiles[indice].get("fte", 0))
                    cantidad = fte / ratio if ratio > 0 else 0.0
                    # Excel CCA!E91:E92 = (FTE/ratio) × pct_rotacion para cargos "(Rotación)".
                    if "otaci" in cargo_nombre_lower and "(" in cargo_nombre:
                        cantidad *= pct_rotacion

                # Acumular headcount por perfil (incluye Agente Básico 1 ratio=1).
                if cantidad > 0:
                    regular_hc_pp[indice] = regular_hc_pp.get(indice, 0.0) + cantidad

                # Agente Básico 1 (tipo="Agente") se contabiliza directamente por FTE en CTS —
                # excluir del overhead de estructura para evitar doble conteo.
                if fila.get("tipo", "").lower() == "agente":
                    result[perfil_nombre].setdefault(cargo_nombre, 0.0)
                    continue

                if costo_unit <= 0:
                    result[perfil_nombre].setdefault(cargo_nombre, 0.0)
                    continue

                costo = costo_unit * cantidad
                # Excel NL!C54:D55 = costo_empresa × (FTE/ratio) × (1/Panel!C11) para "(Inicial)".
                if "nicial" in cargo_nombre_lower and "(" in cargo_nombre:
                    costo /= duracion_meses

                result[perfil_nombre][cargo_nombre] = (
                    result[perfil_nombre].get(cargo_nombre, 0.0) + costo
                )

        # ── Aprendiz SENA (por perfil) ────────────────────────────────────────
        # Excel CCA!E99 = (SUM(E78:E98) + E27+E31+E35) / E126 — por cada columna de perfil
        aprendiz_hc_pp: Dict[int, float] = {}
        if fila_aprendiz is not None:
            nombre_ap = fila_aprendiz.get("position_name") or fila_aprendiz.get("position_id", "")
            costo_unit_ap = 0.0
            if fila_aprendiz.get("incluido", False):
                cargo_data = self._resolver_cargo(fila_aprendiz, detalle_map)
                if cargo_data:
                    # Excel V2-8 · INP!W59 = salario + comision + aux (solo t_haberes).
                    _smlv = float(datos_op.get("smlv") or _SMLV_DEFAULT)
                    _aux_tr = float(datos_op.get("aux_transporte") or _AUX_TRANSPORTE)
                    _sal_ap = float(cargo_data.get("salario", 0))
                    _com_ap = float(cargo_data.get("comision", 0))
                    costo_unit_ap = calcular_costo_empresa_sena(_sal_ap, _com_ap, _smlv, _aux_tr) or sena_unit_cost

            for pr in fila_aprendiz.get("por_perfil", []):
                indice = pr.get("indice_perfil", 0)
                if indice >= len(perfiles):
                    continue
                perfil_nombre = perfiles[indice].get("nombre", f"perfil{indice+1}")
                if perfil_nombre not in result:
                    result[perfil_nombre] = {}

                if not fila_aprendiz.get("incluido", False):
                    result[perfil_nombre].setdefault(nombre_ap, 0.0)
                    aprendiz_hc_pp[indice] = 0.0
                    continue

                try:
                    personalizado_val = float(pr.get("personalizado") or 0)
                except (TypeError, ValueError):
                    personalizado_val = 0.0

                if personalizado_val > 0:
                    aprendiz_q_i = personalizado_val
                else:
                    try:
                        ratio = float(str(pr.get("ratio", "0")).strip() or "0")
                    except (TypeError, ValueError):
                        ratio = 0.0
                    cargos_add_i = sum(
                        float(c.get("cantidad", 0))
                        for c in (perfiles[indice].get("cargos_adicionales") or [])
                        if (c.get("nombre") or "").strip()
                    )
                    aprendiz_q_i = (regular_hc_pp.get(indice, 0.0) + cargos_add_i) / ratio if ratio > 0 else 0.0
                aprendiz_hc_pp[indice] = aprendiz_q_i

                costo = costo_unit_ap * aprendiz_q_i if costo_unit_ap > 0 else 0.0
                result[perfil_nombre][nombre_ap] = result[perfil_nombre].get(nombre_ap, 0.0) + costo

        # ── Inclusión (por perfil) ────────────────────────────────────────────
        # Excel CCA!E100 = (SUM(E78:E99) + E27+E31+E35) / E127 — incluye Aprendiz SENA
        # Excel V2-8: INP!D60 = INDEX(F45:F67, pos23) = F67 = Esp commission → Inclusión hereda comisión del Esp.
        if fila_inclusion is not None:
            nombre_inc = fila_inclusion.get("position_name") or fila_inclusion.get("position_id", "")
            costo_unit_inc = 0.0
            if fila_inclusion.get("incluido", False):
                cargo_data = self._resolver_cargo(fila_inclusion, detalle_map)
                if cargo_data:
                    # Excel V2-8 · INP!W60 = C60 + D60 + G60: Inclusión usa su propia comisión
                    # de CCA!F66, no la del Especialista. Solo t_haberes (igual que SENA).
                    _smlv = float(datos_op.get("smlv") or _SMLV_DEFAULT)
                    _aux_tr = float(datos_op.get("aux_transporte") or _AUX_TRANSPORTE)
                    _sal_inc = float(cargo_data.get("salario", 0))
                    _com_inc = float(cargo_data.get("comision", 0))
                    costo_unit_inc = calcular_costo_empresa_sena(_sal_inc, _com_inc, _smlv, _aux_tr)

            for pr in fila_inclusion.get("por_perfil", []):
                indice = pr.get("indice_perfil", 0)
                if indice >= len(perfiles):
                    continue
                perfil_nombre = perfiles[indice].get("nombre", f"perfil{indice+1}")
                if perfil_nombre not in result:
                    result[perfil_nombre] = {}

                if not fila_inclusion.get("incluido", False):
                    result[perfil_nombre].setdefault(nombre_inc, 0.0)
                    continue

                try:
                    personalizado_val = float(pr.get("personalizado") or 0)
                except (TypeError, ValueError):
                    personalizado_val = 0.0

                if personalizado_val > 0:
                    inclusion_q_i = personalizado_val
                else:
                    try:
                        ratio = float(str(pr.get("ratio", "0")).strip() or "0")
                    except (TypeError, ValueError):
                        ratio = 0.0
                    cargos_add_i = sum(
                        float(c.get("cantidad", 0))
                        for c in (perfiles[indice].get("cargos_adicionales") or [])
                        if (c.get("nombre") or "").strip()
                    )
                    inclusion_q_i = (
                        regular_hc_pp.get(indice, 0.0) + cargos_add_i + aprendiz_hc_pp.get(indice, 0.0)
                    ) / ratio if ratio > 0 else 0.0

                costo = costo_unit_inc * inclusion_q_i if costo_unit_inc > 0 else 0.0
                result[perfil_nombre][nombre_inc] = result[perfil_nombre].get(nombre_inc, 0.0) + costo

        # ── Especialista de Proyectos (por perfil) ────────────────────────────
        # Excel NL!C66 = costo_empresa × complejidad_factor × 3 × pct_perfil / Panel!C11
        # Si "personalizado" > 0 en por_perfil, se usa ese valor como factor del perfil
        # en lugar de pct_i = fte_i / total_fte.
        if fila_especialista is not None:
            nombre_esp = fila_especialista.get("position_name") or fila_especialista.get("position_id", "")
            costo_unit_esp = 0.0
            comision_esp_pp = 0.0
            if fila_especialista.get("incluido", False) and total_fte > 0:
                cargo_data = self._resolver_cargo(fila_especialista, detalle_map)
                if cargo_data:
                    costo_unit_esp = self._get_costo_empresa(cargo_data)
                    # Excel V2-8 · P&G NL = zona1 (CE) + zona2 (raw commission).
                    # Espeja el aggregate (desglose_por_cargo) para que payroll_base del CTS
                    # sea consistente con nomina_total_mensual y el _scale de Crucero sea correcto.
                    comision_esp_pp = float(cargo_data.get("comision", 0))

            # Construir mapa de personalizado por índice de perfil
            personalizado_pp: Dict[int, float] = {}
            for pr in fila_especialista.get("por_perfil", []):
                idx = pr.get("indice_perfil", 0)
                try:
                    personalizado_pp[idx] = float(pr.get("personalizado") or 0)
                except (TypeError, ValueError):
                    personalizado_pp[idx] = 0.0
            hay_personalizado = any(v > 0 for v in personalizado_pp.values())

            for i, perfil in enumerate(perfiles):
                perfil_nombre = perfil.get("nombre", f"perfil{i+1}")
                if perfil_nombre not in result:
                    result[perfil_nombre] = {}
                if costo_unit_esp <= 0 or total_fte <= 0:
                    result[perfil_nombre].setdefault(nombre_esp, 0.0)
                    continue
                # Mixed personalizado: check per-profile, not a global hay_personalizado flag.
                pval_i = personalizado_pp.get(i, 0.0)
                if pval_i > 0:
                    factor_i = pval_i
                else:
                    fte_i = float(perfil.get("fte", 0))
                    factor_i = fte_i / total_fte
                costo_i = (
                    costo_unit_esp * complejidad_factor * 3.0 * factor_i / duracion_meses
                    + comision_esp_pp * factor_i
                )
                result[perfil_nombre][nombre_esp] = result[perfil_nombre].get(nombre_esp, 0.0) + costo_i

        return result

    def costo_estructura_por_perfil(self) -> Dict[str, float]:
        """Costo cargado total de cargos de estructura por perfil (suma de desglose_por_cargo_por_perfil).

        Usado en CTSCalculator para reemplazar la distribución uniforme de overhead.
        # Excel Nomina Loaded: SUM(C43:C80) por perfil = costo estructura real por perfil
        """
        desglose = self.desglose_por_cargo_por_perfil()
        return {perfil: sum(costos.values()) for perfil, costos in desglose.items()}

    def comisiones_estructura_por_perfil(self) -> Dict[str, float]:
        """Comisiones brutas de cargos de estructura por perfil (sin cargas sociales).

        Calcula com_frac = comision / calcular_costo_empresa(salario, comision) para cada cargo
        y lo aplica al costo ya calculado en desglose_por_cargo_por_perfil.
        Matemáticamente equivalente a iterar con comision × cantidad.
        # Excel CTS I141: salario_variable incluye comisiones de estructura, no solo agentes
        """
        desglose = self.desglose_por_cargo_por_perfil()
        detalle: List[Dict] = self._cadena_a.get("detalle_nomina", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])
        detalle_map = {c["cargo"].strip().lower(): c for c in detalle}

        datos_op = self._req.get("datos_operativos", {})
        result: Dict[str, float] = {perfil: 0.0 for perfil in desglose}

        for fila in ratios_filas:
            cargo_nombre = fila.get("position_name") or fila.get("position_id", "")
            if not cargo_nombre or not fila.get("incluido", False):
                continue
            cargo_data = self._resolver_cargo(fila, detalle_map)
            if not cargo_data:
                continue
            salario = float(cargo_data.get("salario", 0))
            comision = float(cargo_data.get("comision", 0))
            if comision <= 0:
                continue
            nombre_lower = cargo_nombre.strip().lower()
            # SENA e Inclusión: solo t_haberes como costo base (sin parafiscales/prestaciones).
            if "aprendiz sena" in nombre_lower or "inclus" in nombre_lower:
                _smlv = float(datos_op.get("smlv") or _SMLV_DEFAULT)
                _aux_tr = float(datos_op.get("aux_transporte") or _AUX_TRANSPORTE)
                costo_empresa = calcular_costo_empresa_sena(salario, comision, _smlv, _aux_tr)
                if costo_empresa <= 0:
                    continue
                com_frac = comision / costo_empresa
            elif "especialista" in nombre_lower:
                # Especialista: costo_cargo = (CE × complejidad × 3/dur + com) × factor.
                # com_frac debe ser com/(CE×comp×3/dur + com) para que
                # comision_pp = com × factor (sin término cruzado com²/CE × factor).
                costo_empresa = calcular_costo_empresa(salario, comision)
                if costo_empresa <= 0:
                    continue
                _cplx_str = self._cadena_a.get("ratios", {}).get("complejidad") or ""
                if isinstance(_cplx_str, dict):
                    _cplx_str = _cplx_str.get("label") or _cplx_str.get("valor") or ""
                _cplx_f = {"alta": 0.5, "media": 0.5, "baja": 0.20}.get(str(_cplx_str).strip().lower(), 0.20)
                _dur = float(self._req.get("datos_operativos", {}).get("duracion_meses", 1) or 1)
                _unit_per_factor = costo_empresa * _cplx_f * 3.0 / _dur + comision
                if _unit_per_factor <= 0:
                    continue
                com_frac = comision / _unit_per_factor
            else:
                costo_empresa = calcular_costo_empresa(salario, comision)
                if costo_empresa <= 0:
                    continue
                com_frac = comision / costo_empresa
            for perfil, cargos in desglose.items():
                costo_cargo = cargos.get(cargo_nombre, 0.0)
                if costo_cargo > 0:
                    result[perfil] = result.get(perfil, 0.0) + costo_cargo * com_frac

        return result

    def proporcion_nomina_por_grupo(self) -> Dict[str, List[dict]]:
        """Proporción de nómina de estructura agrupada por grupo y por perfil.

        Grupos y mapping definidos en _CARGO_GRUPO_MAP (Excel Graficos AM5:AN28).
        Denominador excluye 'Agente Básico 1' (ya excluido en desglose_por_cargo_por_perfil).
        # Excel Graficos: AH31:AI33 = SUMIF(grupos, AJ_props) por perfil activo
        """
        desglose = self.desglose_por_cargo_por_perfil()
        resultado: Dict[str, List[dict]] = {}

        for perfil_nombre, cargos in desglose.items():
            totales_grupo: Dict[str, float] = {g: 0.0 for g in _GRUPOS_ORDEN}
            total_estructura = 0.0

            for cargo_nombre, nomina in cargos.items():
                grupo = _CARGO_GRUPO_MAP.get(cargo_nombre.strip().lower())
                if grupo and grupo in totales_grupo:
                    totales_grupo[grupo] += nomina
                    total_estructura += nomina

            props = [
                {
                    "nombre": grupo,
                    "valor": round(totales_grupo[grupo] / total_estructura, 4) if total_estructura > 0 else 0.0,
                }
                for grupo in _GRUPOS_ORDEN
            ]
            resultado[perfil_nombre] = props

        return resultado

    def _capacitacion_rotacion(self) -> float:
        """Costo mensual de capacitación por rotación (Excel V2-8: 'Nomina Loaded'!E283-E299).

        Por cada perfil con incluye_capacitacion_rotacion=True Y dias_capacitacion_perfil > 0:
          costo = fte × dias_capacitacion_perfil × tarifa_diaria_capacitacion × pct_rotacion
        Excel V2-8: 'Panel de Control General'!C20 = pct_rotacion; C16 = tarifa_diaria.

        Activación: CCA!E143:T143 → incluye_capacitacion_rotacion por perfil.
        Sin este flag en True el perfil no aporta al costo, aunque tenga días configurados.
        """
        datos_op = self._req.get("datos_operativos", {})
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        tarifa_diaria = float(datos_op.get("tarifa_diaria_capacitacion", 20_000.0))
        if pct_rotacion <= 0 or tarifa_diaria <= 0:
            return 0.0

        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            cap = perfil.get("capacitacion") or {}
            # Excel V2-8: 'Condiciones Cadena A'!E143:T143 — checkbox por perfil
            if not cap.get("incluye_capacitacion_rotacion", False):
                continue
            dias = float(cap.get("dias_capacitacion_perfil") or 0)
            if dias <= 0:
                continue
            fte = float(perfil.get("fte", 0))
            total += fte * dias * tarifa_diaria * pct_rotacion
            # Cargos adicionales comparten el flag y días de capacitación del perfil
            for cargo in perfil.get("cargos_adicionales") or []:
                if not (cargo.get("nombre") or "").strip():
                    continue
                cantidad = float(cargo.get("cantidad", 0.0))
                if cantidad > 0:
                    total += cantidad * dias * tarifa_diaria * pct_rotacion
        return total

    def _capacitacion_inicial(self) -> float:
        """Base mensual de capacitación inicial por perfil activo.

        Por cada perfil con incluye_capacitacion_inicial=True:
          base = fte × dias_capacitacion_perfil × tarifa_diaria_capacitacion
        El motor coloca este valor × duracion_meses como costo total en el mes 1.
        Excel V2-8: 'Nomina Loaded'!C255:BK273 (SUMPRODUCT); 'Visión P&G'!B40 (solo mes inicio).
        """
        datos_op = self._req.get("datos_operativos", {})
        tarifa_diaria = float(datos_op.get("tarifa_diaria_capacitacion", 20_000.0))
        if tarifa_diaria <= 0:
            return 0.0

        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            cap = perfil.get("capacitacion", {})
            if not cap.get("incluye_capacitacion_inicial", False):
                continue
            fte = float(perfil.get("fte", 0))
            dias = float(cap.get("dias_capacitacion_perfil", 0))
            total += fte * dias * tarifa_diaria
            # Cargos adicionales comparten el flag y días de capacitación del perfil
            for cargo in perfil.get("cargos_adicionales") or []:
                if not (cargo.get("nombre") or "").strip():
                    continue
                cantidad = float(cargo.get("cantidad", 0.0))
                if cantidad > 0:
                    total += cantidad * dias * tarifa_diaria
        return total

    def _cargos_adicionales(self) -> float:
        """Costo mensual de cargos adicionales configurados en Cadena A.

        Excel V2-8: 'Condiciones Cadena A'!D25:S35 — hasta 3 cargos adicionales.
        Cada cargo tiene por perfil: nombre (E25/E29/E33), salario (E26/E30/E34),
        cantidad (E27/E31/E35 = FTE directo de ese cargo para el perfil, NO ratio 1:N).

        'Nomina Loaded'!C69 = AM77 × cantidad = calcular_costo_empresa(smlv) × cantidad

        Salario base por defecto = SMLV (fórmula Excel: =IF(nombre<>"", SMLV, 0)).
        """
        datos_op = self._req.get("datos_operativos", {})
        smlv = float(datos_op.get("smlv", _SMLV_DEFAULT))

        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            for cargo in perfil.get("cargos_adicionales") or []:
                nombre = (cargo.get("nombre") or "").strip()
                if not nombre:
                    continue
                cantidad = float(cargo.get("cantidad", 0.0))
                if cantidad <= 0:
                    continue
                salario_base = float(cargo.get("salario_base") or smlv)
                costo_unit = calcular_costo_empresa(salario_base, 0.0, smlv)
                total += costo_unit * cantidad
        return total

    def _examenes_medicos(self) -> float:
        """Costo mensual de exámenes médicos para Cadena A.

        Excel V2-8: 'Nomina Loaded'!C329:C331 — unit cost por ciudad
          = SUMPRODUCT(GN 'Rot, Ausent y Rentabilidad'!B67:F67 × proporcion_ciudad)
        Excel V2-8: 'Nomina Loaded'!C339:C341 — costo por perfil.
        'Visión P&G'!B42 = Exámenes Médicos.

        Los costos unitarios vienen pre-inyectados en datos_operativos por el handler
        desde HR-Med-Seg (InfrastructureParametrizationRepository.get_all_med_seg_costs):
          costo_examen_medico_inicial    (HR-Med-Seg: "exámenes medicos nuevos (iniciales)")
          costo_examen_medico_rotacion   (HR-Med-Seg: "exámenes medicos (rotación)")
          costo_examen_medico_anual      (HR-Med-Seg: "exámenes medicos (anual)")
        Default si no se inyecta: 58,000 (GN valor no-Bogotá).

        Flags (patrón DTO v2, bajo capacitacion{}):
          iniciales → capacitacion.incluye_costo_examenes_ingreso   (CCA!E145)
          rotacion  → capacitacion.incluye_costo_examenes_rotacion  (CCA!E146)
          anual     → capacitacion.incluye_costo_capacitacion_anual (CCA!E147)
        pct_anuales: CCA!E136 = 0.28 (override via datos_operativos.pct_examenes_anuales)
        pct_rotacion: Panel!C20 / duracion_meses: Panel!C11
        # Excel V2-8: 'Condiciones Cadena A'!D144:T147 — flags de exámenes por perfil
        """
        datos_op = self._req.get("datos_operativos", {})
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        duracion_meses = float(datos_op.get("duracion_meses", 1.0))
        if duracion_meses <= 0:
            duracion_meses = 1.0
        pct_anuales_global = float(datos_op.get("pct_examenes_anuales", 0.28))

        # Costos inyectados desde HR-Med-Seg por ciudad (via calculate_handler._inject_med_seg_costs)
        # Excel V2-8 · 'Nomina Loaded'!C329 = SUMPRODUCT(GN!B67:F67 × GN!B66:F66) por ciudad
        cu_ini = float(datos_op.get("costo_examen_medico_inicial") or 58_000.0)
        cu_rot = float(datos_op.get("costo_examen_medico_rotacion") or 58_000.0)
        cu_anu = float(datos_op.get("costo_examen_medico_anual") or 58_000.0)

        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])

        total = 0.0
        for i, perfil in enumerate(perfiles):
            fte_agente = float(perfil.get("fte", 0.0))
            if fte_agente <= 0:
                continue

            # FTE directo de cargos adicionales del perfil (igual que C230 en _estudios_seguridad).
            cargos_add_fte = sum(
                float(cargo.get("cantidad", 0.0))
                for cargo in (perfil.get("cargos_adicionales") or [])
                if (cargo.get("nombre") or "").strip()
            )
            # fte_base afecta los ratios de estructura (mismo patrón que _estudios_seguridad).
            fte_base = fte_agente + cargos_add_fte

            # FTE total para exámenes = agente (fila 97) + estructura operativa del perfil.
            # Excel: NominaLoaded!C339 = C329 × SUMPRODUCT(CCA!E94:S98 × (E77:S77=perfil)) / C11
            # Filas 94-98: Formadores, Monitor, Supervisor, Agente Básico 1, Validador.
            # El agente (fila 97, tipo="Agente") ya está en fte_agente — no sumar de ratios_filas.
            # Los cargos Administrativos (Directors, etc.) NO son filas de examen — excluir.
            # Solo cargos tipo="Operativo" corresponden a estructura de examen (filas 94-96, 98).
            fte_exam = fte_agente
            for fila in ratios_filas:
                if not fila.get("incluido", False):
                    continue
                if fila.get("tipo", "").lower() != "operativo":
                    continue
                for pr in fila.get("por_perfil", []):
                    if pr.get("indice_perfil", -1) != i:
                        continue
                    try:
                        personalizado = float(pr.get("personalizado") or 0)
                    except (TypeError, ValueError):
                        personalizado = 0.0
                    if personalizado > 0:
                        fte_exam += personalizado
                    else:
                        try:
                            ratio = float(str(pr.get("ratio", "0")).strip() or "0")
                        except ValueError:
                            ratio = 0.0
                        if ratio > 0:
                            fte_exam += fte_base / ratio
            fte_exam += cargos_add_fte  # suma directa (simétrico con _estudios_seguridad C230)

            # Backward-compat: sub-objeto legacy examenes_medicos (soporte tests/fixtures)
            exam = perfil.get("examenes_medicos")
            if exam:
                pct_anuales = float(exam.get("pct_examenes_anuales", pct_anuales_global))
                if exam.get("activo_iniciales", False):
                    cu = float(exam.get("costo_unitario_iniciales") or cu_ini)
                    total += cu * fte_exam / duracion_meses
                if exam.get("activo_rotacion", False):
                    cu = float(exam.get("costo_unitario_rotacion") or cu_rot)
                    total += cu * fte_exam * pct_rotacion
                if exam.get("activo_anual", False):
                    cu = float(exam.get("costo_unitario_anual") or cu_anu)
                    total += cu * fte_exam * pct_anuales / 12.0
                continue

            # Patrón DTO v2: flags bajo capacitacion{} (CCA!E145:T147)
            cap = perfil.get("capacitacion") or {}
            # Excel V2-8 · 'Nomina Loaded'!C339 = IF(CCA!E145, C329×(FTE_total)/PCG!C11, 0)
            if cap.get("incluye_costo_examenes_ingreso", False):
                total += cu_ini * fte_exam / duracion_meses
            # Excel V2-8 · 'Nomina Loaded'!C340 = IF(CCA!E146, C330×(FTE_total)×PCG!C20, 0)
            if cap.get("incluye_costo_examenes_rotacion", False):
                total += cu_rot * fte_exam * pct_rotacion
            # Excel V2-8 · 'Nomina Loaded'!C341 = IF(CCA!E147, C331×(FTE_total)×CCA!E136/12, 0)
            if cap.get("incluye_costo_capacitacion_anual", False):
                total += cu_anu * fte_exam * pct_anuales_global / 12.0

        return total

    def _estudios_seguridad(self) -> float:
        """Costo mensual de estudios de seguridad para Cadena A.

        Excel V2-8: 'Nomina Loaded'!C396:C399 (costo por perfil por tipo).
        'Visión P&G'!B43 = Estudios de Seguridad.

        Por cada perfil, cuatro tipos según flags activos en capacitacion{}:
          prelim_iniciales:  costo_prelim_inicial × FTE / duracion_meses   (amortizado)
          prelim_rotacion:   costo_prelim_rotacion × FTE × pct_rotacion
          final_iniciales:   costo_final_inicial × FTE / duracion_meses    (amortizado)
          final_rotacion:    costo_final_rotacion × FTE × pct_rotacion

        Costos unitarios desde datos_operativos (fuente: GN 'Rot, Ausent y Rentabilidad' filas 70-73):
          costo_estudio_prelim_inicial  (default 54,055)
          costo_estudio_prelim_rotacion (default 54,055)
          costo_estudio_final_inicial   (default 144,879)
          costo_estudio_final_rotacion  (default 144,879)

        # Excel V2-8: 'Condiciones Cadena A'!D149:T152 — checkboxes por perfil
        # Excel V2-8: 'Nomina Loaded'!C390:C393 — unit costs (GN rows 70-73)
        # Excel V2-8: 'Panel de Control General'!C11 = duracion_meses, C20 = pct_rotacion
        """
        datos_op = self._req.get("datos_operativos", {})
        duracion_meses = float(datos_op.get("duracion_meses", 1.0))
        if duracion_meses <= 0:
            duracion_meses = 1.0
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))

        # Costos inyectados desde HR-Med-Seg por ciudad (via calculate_handler._inject_med_seg_costs)
        # Excel V2-8 · 'Nomina Loaded'!C390 = SUMPRODUCT(GN!B70:F70 × GN!B66:F66) por ciudad
        cu_prelim_ini = float(datos_op.get("costo_estudio_prelim_inicial") or 54_055.0)
        cu_prelim_rot = float(datos_op.get("costo_estudio_prelim_rotacion") or 54_055.0)
        cu_final_ini = float(datos_op.get("costo_estudio_final_inicial") or 144_879.0)
        cu_final_rot = float(datos_op.get("costo_estudio_final_rotacion") or 144_879.0)

        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])

        total = 0.0
        for i, perfil in enumerate(perfiles):
            cap = perfil.get("capacitacion") or {}
            fte_agente = float(perfil.get("fte", 0.0))
            if fte_agente <= 0:
                continue

            # C230: FTE directo de cargos adicionales (CCA!E27/E31/E35 — cantidad, no ratio 1:N).
            # Excel V2-8 · 'Nomina Loaded'!C230 = SUMPRODUCT(CCA!E25:S35 × (D="Ratio") × (E8:S8=perfil))
            cargos_add_fte = sum(
                float(cargo.get("cantidad", 0.0))
                for cargo in (perfil.get("cargos_adicionales") or [])
                if (cargo.get("nombre") or "").strip()
            )

            # Base FTE para numerador de estructura = agente + cargos adicionales.
            # Excel V2-8: CCA!E94=(E$9+E$27+E$31+E$35)/ratio; fila 97 usa solo E9 (sin cargos_adic).
            fte_base = fte_agente + cargos_add_fte

            # FTE total estudios = agente (fila 97) + estructura operativa + C230.
            # Excel V2-8 · 'Nomina Loaded'!C396 = C390×(SUMPRODUCT(CCA!E94:S98×mask)+C230)/C11
            # SUMPRODUCT incluye: Formadores(94)+Monitor(95)+Supervisor(96)+Agente(97)+Validador(98).
            # Agente (fila 97) ya está en fte_agente. Operativo estructura usa fte_base/ratio.
            # Administrativo (Directors, etc.) NO son filas de estudios — excluir.
            # Agente Básico 1 (tipo="Agente") ya en fte_agente — excluir para evitar doble conteo.
            fte_exam = fte_agente
            for fila in ratios_filas:
                if not fila.get("incluido", False):
                    continue
                if fila.get("tipo", "").lower() != "operativo":
                    continue
                for pr in fila.get("por_perfil", []):
                    if pr.get("indice_perfil", -1) != i:
                        continue
                    try:
                        personalizado = float(pr.get("personalizado") or 0)
                    except (TypeError, ValueError):
                        personalizado = 0.0
                    if personalizado > 0:
                        fte_exam += personalizado
                    else:
                        try:
                            ratio = float(str(pr.get("ratio", "0")).strip() or "0")
                        except ValueError:
                            ratio = 0.0
                        if ratio > 0:
                            fte_exam += fte_base / ratio
            fte_exam += cargos_add_fte  # C230: suma directa de cargos adicionales

            # Excel V2-8 · 'Nomina Loaded'!C396 formula: IF(CCA!E149, C390×fte_exam/PCG!C11, 0)
            if cap.get("incluye_estudio_seguridad_ingreso", False):
                total += cu_prelim_ini * fte_exam / duracion_meses
            # Excel V2-8 · 'Nomina Loaded'!C397 formula: IF(CCA!E150, C391×fte_exam×PCG!C20, 0)
            if cap.get("incluye_estudio_seguridad_rotacion", False):
                total += cu_prelim_rot * fte_exam * pct_rotacion
            # Excel V2-8 · 'Nomina Loaded'!C398 formula: IF(CCA!E151, C392×fte_exam/PCG!C11, 0)
            if cap.get("incluye_estudio_seguridad_final_ingreso", False):
                total += cu_final_ini * fte_exam / duracion_meses
            # Excel V2-8 · 'Nomina Loaded'!C399 formula: IF(CCA!E152, C393×fte_exam×PCG!C20, 0)
            if cap.get("incluye_estudio_seguridad_final_rotacion", False):
                total += cu_final_rot * fte_exam * pct_rotacion
        return total

    def costos_nominalizados_por_perfil(self) -> Dict[str, Dict[str, float]]:
        """Costos de cap_inicial, cap_rotacion, examenes_medicos y estudios_seguridad por perfil.

        Extrae los mismos valores que _capacitacion_inicial/_rotacion/_examenes_medicos/_estudios_seguridad
        pero devuelve un dict {perfil_nombre: {campo: valor}} para uso en CTSCalculator.
        # Excel V2-8: 'Nomina Loaded' filas 255-273 (cap ini), 283-299 (cap rot), 329-341 (exam), 390-399 (seg)
        """
        perfiles: List[Dict] = self._cadena_a.get("perfiles", [])
        ratios_filas: List[Dict] = self._cadena_a.get("ratios", {}).get("filas", [])
        datos_op = self._req.get("datos_operativos", {})

        tarifa_diaria = float(datos_op.get("tarifa_diaria_capacitacion", 20_000.0))
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        duracion_meses = float(datos_op.get("duracion_meses", 1.0)) or 1.0
        pct_anuales_global = float(datos_op.get("pct_examenes_anuales", 0.28))
        smlv = float(datos_op.get("smlv", _SMLV_DEFAULT))

        cu_exam_ini = float(datos_op.get("costo_examen_medico_inicial") or 58_000.0)
        cu_exam_rot = float(datos_op.get("costo_examen_medico_rotacion") or 58_000.0)
        cu_exam_anu = float(datos_op.get("costo_examen_medico_anual") or 58_000.0)
        cu_prelim_ini = float(datos_op.get("costo_estudio_prelim_inicial") or 54_055.0)
        cu_prelim_rot = float(datos_op.get("costo_estudio_prelim_rotacion") or 54_055.0)
        cu_final_ini = float(datos_op.get("costo_estudio_final_inicial") or 144_879.0)
        cu_final_rot = float(datos_op.get("costo_estudio_final_rotacion") or 144_879.0)

        result: Dict[str, Dict[str, float]] = {}
        for i, perfil in enumerate(perfiles):
            nombre = perfil.get("nombre", f"perfil{i+1}")
            cap = perfil.get("capacitacion") or {}
            fte = float(perfil.get("fte", 0.0))
            if fte <= 0:
                result[nombre] = {"capacitacion_inicial": 0.0, "capacitacion_rotacion": 0.0,
                                  "examenes_medicos": 0.0, "estudios_seguridad": 0.0}
                continue

            # Cargos adicionales FTE del perfil — usado en cap_ini, cap_rot, fte_exam y fte_estudio
            cargos_add_fte = sum(
                float(c.get("cantidad", 0.0))
                for c in (perfil.get("cargos_adicionales") or [])
                if (c.get("nombre") or "").strip()
            )
            fte_total = fte + cargos_add_fte

            # Capacitación inicial — amortizada mensualmente para vista CTS
            # Excel NL C255:BK273 muestra costo total; CTS muestra total / duracion_meses
            cap_ini = 0.0
            if tarifa_diaria > 0 and cap.get("incluye_capacitacion_inicial", False):
                dias = float(cap.get("dias_capacitacion_perfil", 0))
                cap_ini = fte_total * dias * tarifa_diaria / duracion_meses

            # Capacitación rotación
            cap_rot = 0.0
            if tarifa_diaria > 0 and cap.get("incluye_capacitacion_rotacion", False):
                dias = float(cap.get("dias_capacitacion_perfil") or 0)
                cap_rot = fte_total * dias * tarifa_diaria * pct_rotacion

            # FTE examinable = agente + cargos_adicionales + operativos de estructura del perfil
            fte_exam = fte_total
            for fila in ratios_filas:
                if not fila.get("incluido", False):
                    continue
                if fila.get("tipo", "").lower() != "operativo":
                    continue
                for pr in fila.get("por_perfil", []):
                    if pr.get("indice_perfil", -1) != i:
                        continue
                    try:
                        personalizado = float(pr.get("personalizado") or 0)
                    except (TypeError, ValueError):
                        personalizado = 0.0
                    if personalizado > 0:
                        fte_exam += personalizado
                    else:
                        try:
                            ratio = float(str(pr.get("ratio", "0")).strip() or "0")
                        except ValueError:
                            ratio = 0.0
                        if ratio > 0:
                            fte_exam += fte / ratio

            # Exámenes médicos
            exams = 0.0
            exam_legacy = perfil.get("examenes_medicos")
            if exam_legacy:
                pct_an = float(exam_legacy.get("pct_examenes_anuales", pct_anuales_global))
                if exam_legacy.get("activo_iniciales", False):
                    cu = float(exam_legacy.get("costo_unitario_iniciales") or cu_exam_ini)
                    exams += cu * fte_exam / duracion_meses
                if exam_legacy.get("activo_rotacion", False):
                    cu = float(exam_legacy.get("costo_unitario_rotacion") or cu_exam_rot)
                    exams += cu * fte_exam * pct_rotacion
                if exam_legacy.get("activo_anual", False):
                    cu = float(exam_legacy.get("costo_unitario_anual") or cu_exam_anu)
                    exams += cu * fte_exam * pct_an / 12.0
            else:
                if cap.get("incluye_costo_examenes_ingreso", False):
                    exams += cu_exam_ini * fte_exam / duracion_meses
                if cap.get("incluye_costo_examenes_rotacion", False):
                    exams += cu_exam_rot * fte_exam * pct_rotacion
                if cap.get("incluye_costo_capacitacion_anual", False):
                    exams += cu_exam_anu * fte_exam * pct_anuales_global / 12.0

            # Estudios de seguridad — usa fte_total (ya incluye cargos_adicionales)
            fte_estudio = fte
            for fila in ratios_filas:
                if not fila.get("incluido", False):
                    continue
                if fila.get("tipo", "").lower() != "operativo":
                    continue
                for pr in fila.get("por_perfil", []):
                    if pr.get("indice_perfil", -1) != i:
                        continue
                    try:
                        personalizado = float(pr.get("personalizado") or 0)
                    except (TypeError, ValueError):
                        personalizado = 0.0
                    if personalizado > 0:
                        fte_estudio += personalizado
                    else:
                        try:
                            ratio = float(str(pr.get("ratio", "0")).strip() or "0")
                        except ValueError:
                            ratio = 0.0
                        if ratio > 0:
                            fte_estudio += fte_total / ratio
            fte_estudio += cargos_add_fte

            seg = 0.0
            if cap.get("incluye_estudio_seguridad_ingreso", False):
                seg += cu_prelim_ini * fte_estudio / duracion_meses
            if cap.get("incluye_estudio_seguridad_rotacion", False):
                seg += cu_prelim_rot * fte_estudio * pct_rotacion
            if cap.get("incluye_estudio_seguridad_final_ingreso", False):
                seg += cu_final_ini * fte_estudio / duracion_meses
            if cap.get("incluye_estudio_seguridad_final_rotacion", False):
                seg += cu_final_rot * fte_estudio * pct_rotacion

            result[nombre] = {
                "capacitacion_inicial": cap_ini,
                "capacitacion_rotacion": cap_rot,
                "examenes_medicos": exams,
                "estudios_seguridad": seg,
            }
        return result

    @staticmethod
    def _get_costo_empresa(
        cargo_data: Dict, cargo_nombre: str = "", sena_override: float = 0.0
    ) -> float:
        """Retorna costo_empresa: override > fórmula SENA > fórmula estándar.

        SENA/Inclusión: pensión=0, ARL=0, salud=0, dotaciones=0.
        Excel V2-8: Inputs de Nomina row 59/60 — I=J=K=L=V=0.
        sena_override: valor global desde datos_operativos.costo_empresa_sena (W59 Excel).
        """
        override = cargo_data.get("costo_empresa")
        if override is not None:
            try:
                v = float(override)
                if v > 0:
                    return v
            except (TypeError, ValueError):
                pass
        salario = float(cargo_data.get("salario", 0))
        comision = float(cargo_data.get("comision", 0))
        nombre_check = (cargo_data.get("cargo") or cargo_nombre or "").lower()
        if "aprendiz sena" in nombre_check or "inclus" in nombre_check:
            if sena_override > 0:
                return sena_override
            return calcular_costo_empresa_sena(salario)
        return calcular_costo_empresa(salario, comision)

    @staticmethod
    def _get_ratio_global(fila: Dict) -> float:
        """Retorna el primer ratio no-cero de por_perfil (asume ratio uniforme entre perfiles)."""
        for pr in fila.get("por_perfil", []):
            try:
                r = float(str(pr.get("ratio", "0")).strip() or "0")
                if r > 0:
                    return r
            except (TypeError, ValueError):
                pass
        return 0.0

    @staticmethod
    def _resolver_cargo(fila: Dict, detalle_map: Dict) -> Dict:
        """Busca datos salariales del cargo en detalle_nomina (por position_id o position_name)."""
        cargo = detalle_map.get(fila.get("position_id", "").strip().lower())
        if not cargo:
            cargo = detalle_map.get(fila.get("position_name", "").strip().lower())
        return cargo or {}

    @staticmethod
    def _calcular_cantidad(
        fila: Dict,
        perfiles: List[Dict],
        *,
        pct_rotacion: float = 0.0,
        is_rotation: bool = False,
    ) -> float:
        """Distribución fraccionaria SIN ceil: fte_perfil / ratio (continua, no entera).

        Excel V2-8: Condiciones Cadena A E78 = (fte_total / ratio_cargo).
        Si por_perfil[i].personalizado > 0, se usa ese valor directamente (equivale
        a editar manualmente la celda CCA!E91 en el Excel — el valor ya representa el
        ratio CCA completo, sin necesidad de aplicar pct_rotacion de nuevo).
        Si personalizado == 0 e is_rotation=True, aplica pct_rotacion al resultado
        automático de ese perfil.
        Esto permite mixes parciales: un perfil con override, otro con cálculo auto.
        """
        total = 0.0
        for pr in fila.get("por_perfil", []):
            try:
                personalizado_val = float(pr.get("personalizado") or 0)
            except (TypeError, ValueError):
                personalizado_val = 0.0
            if personalizado_val > 0:
                # Override manual: no aplicar pct_rotacion (ya incluido implícitamente)
                total += personalizado_val
                continue

            # Cálculo estándar: fte / ratio
            indice = pr.get("indice_perfil", 0)
            try:
                ratio_val = float(str(pr.get("ratio", "0")).strip() or "0")
            except ValueError:
                ratio_val = 0.0
            if ratio_val > 0 and indice < len(perfiles):
                q = float(perfiles[indice].get("fte", 0)) / ratio_val
                if is_rotation:
                    q *= pct_rotacion
                total += q
        return total
