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
    # Recursos humanos (6 cargos)
    "lider de entrenamiento":                         "Recursos humanos",
    "formadores":                                     "Recursos humanos",
    "analista prof. de selección":                    "Recursos humanos",
    "analista 1 de reclutamiento":                    "Recursos humanos",
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
        nomina_loaded = self._nomina_agentes() + self._nomina_estructura()
        salario_variable = self._nomina_comisiones_brutas()
        return {
            "nomina_loaded": nomina_loaded,
            "crucero_total": self._crucero(),
            "capacitacion_rotacion": self._capacitacion_rotacion(),
            "capacitacion_inicial": self._capacitacion_inicial(),
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

        for fila in ratios_filas:
            cargo_nombre = fila.get("position_name") or fila.get("position_id", "")
            if not cargo_nombre:
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

                if costo_unit <= 0:
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

                result[perfil_nombre][cargo_nombre] = (
                    result[perfil_nombre].get(cargo_nombre, 0.0) + costo_unit * cantidad
                )

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

        Por cada perfil con dias_capacitacion_perfil > 0:
          costo = fte × dias_capacitacion_perfil × tarifa_diaria_capacitacion × pct_rotacion
        Excel V2-8: 'Panel de Control General'!C20 = pct_rotacion; C16 = tarifa_diaria.

        Activación: `incluye_capacitacion_rotacion` explícito (extra field) o bien
        `dias_capacitacion_perfil > 0` como indicador implícito (patrón DTO v2).
        # Excel V2-8: 'Condiciones Cadena A'!D58 — días de capacitación por perfil
        """
        datos_op = self._req.get("datos_operativos", {})
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        tarifa_diaria = float(datos_op.get("tarifa_diaria_capacitacion", 20_000.0))
        if pct_rotacion <= 0 or tarifa_diaria <= 0:
            return 0.0

        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            cap = perfil.get("capacitacion") or {}
            dias = float(cap.get("dias_capacitacion_perfil") or 0)
            # Activado si hay flag explícito O si hay días configurados
            activo = cap.get("incluye_capacitacion_rotacion") if "incluye_capacitacion_rotacion" in cap else dias > 0
            if not activo:
                continue
            fte = float(perfil.get("fte", 0))
            total += fte * dias * tarifa_diaria * pct_rotacion
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
        return total

    # Excel V2-8 · 'Rot, Ausent y Rentabilidad'!B67:F67 — costo examen médico por ciudad
    # SUMPRODUCT(costos × proporcion_ciudad): Bogotá=60800, resto=58000
    # Fuente: GN parametrización, misma lógica que HR-Med-Seg (get_medical_exam_cost)
    _COSTO_EXAMEN_POR_CIUDAD: Dict[str, float] = {
        "bogota":       60_800.0,
        "bogotá":       60_800.0,
    }
    _COSTO_EXAMEN_DEFAULT = 58_000.0  # Cali, Medellín, Bucaramanga, Barranquilla, etc.

    @classmethod
    def _costo_examen_ciudad(cls, ciudad: str) -> float:
        """Devuelve costo unitario de examen médico según ciudad (GN rows 67-69)."""
        return cls._COSTO_EXAMEN_POR_CIUDAD.get(
            (ciudad or "").strip().lower(),
            cls._COSTO_EXAMEN_DEFAULT,
        )

    def _examenes_medicos(self) -> float:
        """Costo mensual de exámenes médicos para Cadena A.

        Excel V2-8: 'Nomina Loaded'!C329:C331 — unit cost por ciudad (SUMPRODUCT GN rows 67-69).
        Excel V2-8: 'Nomina Loaded'!C339:C341 — costo por perfil.
        'Visión P&G'!B42 = Exámenes Médicos.

        Los tres tipos tienen el mismo costo unitario (varía por ciudad, no por tipo):
          iniciales: unit_cost × FTE / duracion_meses   (amortizado — Excel C339)
          rotacion:  unit_cost × FTE × pct_rotacion     (Excel C340)
          anual:     unit_cost × FTE × pct_anuales / 12 (Excel C341)

        Flags (patrón DTO v2, bajo capacitacion{}):
          iniciales → capacitacion.incluye_costo_examenes_ingreso   (CCA!E145)
          rotacion  → capacitacion.incluye_costo_examenes_rotacion  (CCA!E146)
          anual     → capacitacion.incluye_costo_capacitacion_anual (CCA!E147)
        Backward-compat: si existe perfil.examenes_medicos (sub-objeto legacy), se usa directo.

        Costo unitario: GN 'Rot, Ausent y Rentabilidad' filas 67-69 × proporcion_ciudad.
          Bogotá=60800 / resto=58000 (override via datos_operativos.costo_examen_medico)
        pct_anuales: CCA!E136 = 0.28 (override via datos_operativos.pct_examenes_anuales)
        pct_rotacion: Panel!C20 (datos_operativos.pct_rotacion)
        duracion_meses: Panel!C11 (datos_operativos.duracion_meses)
        # Excel V2-8: 'Condiciones Cadena A'!D144:T147 — flags de exámenes por perfil
        """
        datos_op = self._req.get("datos_operativos", {})
        pct_rotacion = float(datos_op.get("pct_rotacion", 0.0))
        duracion_meses = float(datos_op.get("duracion_meses", 1.0))
        if duracion_meses <= 0:
            duracion_meses = 1.0
        pct_anuales_global = float(datos_op.get("pct_examenes_anuales", 0.28))

        # Costo unitario desde GN (mismo para los 3 tipos), selección por ciudad
        # Excel V2-8 · 'Nomina Loaded'!C329 = SUMPRODUCT(GN!B67:F67 × GN!B66:F66)
        ciudad = str(datos_op.get("ciudad") or "")
        cu_ciudad = self._costo_examen_ciudad(ciudad)
        # Permite override explícito por tipo si es necesario (compatibilidad futura)
        cu_ini = float(datos_op.get("costo_examen_medico_inicial") or cu_ciudad)
        cu_rot = float(datos_op.get("costo_examen_medico_rotacion") or cu_ciudad)
        cu_anu = float(datos_op.get("costo_examen_medico_anual") or cu_ciudad)

        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            fte = float(perfil.get("fte", 0.0))
            if fte <= 0:
                continue

            # Backward-compat: sub-objeto legacy examenes_medicos (soporte tests/fixtures)
            exam = perfil.get("examenes_medicos")
            if exam:
                pct_anuales = float(exam.get("pct_examenes_anuales", pct_anuales_global))
                if exam.get("activo_iniciales", False):
                    cu = float(exam.get("costo_unitario_iniciales") or cu_ini)
                    total += cu * fte / duracion_meses
                if exam.get("activo_rotacion", False):
                    cu = float(exam.get("costo_unitario_rotacion") or cu_rot)
                    total += cu * fte * pct_rotacion
                if exam.get("activo_anual", False):
                    cu = float(exam.get("costo_unitario_anual") or cu_anu)
                    total += cu * fte * pct_anuales / 12.0
                continue

            # Patrón DTO v2: flags bajo capacitacion{} (CCA!E145:T147)
            cap = perfil.get("capacitacion") or {}
            # Excel V2-8 · 'Nomina Loaded'!C339 = IF(CCA!E145, C329×(FTE)/PCG!C11, 0)
            if cap.get("incluye_costo_examenes_ingreso", False):
                total += cu_ini * fte / duracion_meses
            # Excel V2-8 · 'Nomina Loaded'!C340 = IF(CCA!E146, C330×(FTE)×PCG!C20, 0)
            if cap.get("incluye_costo_examenes_rotacion", False):
                total += cu_rot * fte * pct_rotacion
            # Excel V2-8 · 'Nomina Loaded'!C341 = IF(CCA!E147, C331×(FTE)×CCA!E136/12, 0)
            if cap.get("incluye_costo_capacitacion_anual", False):
                total += cu_anu * fte * pct_anuales_global / 12.0

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

        # Excel V2-8 · 'Rot, Ausent y Rentabilidad'!B70:B73 — unit costs de GN
        cu_prelim_ini = float(datos_op.get("costo_estudio_prelim_inicial", 54_055.0))
        cu_prelim_rot = float(datos_op.get("costo_estudio_prelim_rotacion", 54_055.0))
        cu_final_ini = float(datos_op.get("costo_estudio_final_inicial", 144_879.0))
        cu_final_rot = float(datos_op.get("costo_estudio_final_rotacion", 144_879.0))

        total = 0.0
        for perfil in self._cadena_a.get("perfiles", []):
            cap = perfil.get("capacitacion") or {}
            fte = float(perfil.get("fte", 0.0))
            if fte <= 0:
                continue
            # Excel V2-8 · 'Nomina Loaded'!C396 formula: IF(CCA!E149, C390×(FTE)/PCG!C11, 0)
            if cap.get("incluye_estudio_seguridad_ingreso", False):
                total += cu_prelim_ini * fte / duracion_meses
            # Excel V2-8 · 'Nomina Loaded'!C397 formula: IF(CCA!E150, C391×FTE×PCG!C20, 0)
            if cap.get("incluye_estudio_seguridad_rotacion", False):
                total += cu_prelim_rot * fte * pct_rotacion
            # Excel V2-8 · 'Nomina Loaded'!C398 formula: IF(CCA!E151, C392×(FTE)/PCG!C11, 0)
            if cap.get("incluye_estudio_seguridad_final_ingreso", False):
                total += cu_final_ini * fte / duracion_meses
            # Excel V2-8 · 'Nomina Loaded'!C399 formula: IF(CCA!E152, C393×FTE×PCG!C20, 0)
            if cap.get("incluye_estudio_seguridad_final_rotacion", False):
                total += cu_final_rot * fte * pct_rotacion
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
