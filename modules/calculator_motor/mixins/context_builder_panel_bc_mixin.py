from __future__ import annotations
"""Private builder methods for SimulationContextBuilder.

Single mixin containing all private _construir_* and _calcular_* methods.
Extracted FASE Z.4.3 — behaviour unchanged; self.* resolves via Python MRO.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexa_engine.modules.calculator_motor.constants.global_constants import MES_INICIO_AJUSTE_ANUAL
from nexa_engine.modules.shared.models import (
    CanalCadenaB, CanalCadenaC, CadenasActivas, DispositivoSM, EscenarioComercial,
    Indexacion, ItemOpexConsumoB, MiembroEquipo, PanelDeControl, ParametrosCadenaB,
    ParametrosCadenaC, ParametrosCalculo, ParametrosNomina, ParametrosNoPayroll,
    PerfilCadenaA, PolizaContractual, PricingRequest, mes_inicio_contrato,
)
from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService
from nexa_engine.modules.cadena_a.services.special_roles_calculator import (
    CargoClassifier, EspecialistaCalculator, SENACalculator, InclusionCalculator,
    SalarioFijoCalculator,
)
from nexa_engine.modules.calculator_motor.dto.user_inputs import UserInput
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.calculator_motor.models.data_provenance import DataProvenance, DataSource, ProvenanceEntry
from nexa_engine.modules.calculator_motor.dto.normalized_input import NormalizationLog

_logger = logging.getLogger("nexa_engine.context_builder")



class ContextBuilderPanelBCMixin:
    """Mixin: ContextBuilderPanelBCMixin."""

    def _construir_parametros_nomina(self, panel, ciudad: str) -> ParametrosNomina:
        """
        Deriva los parámetros de nómina del contrato.

        El factor de indexación base se calcula a partir del componente
        elegido por el usuario y el año de inicio del contrato.

        Convención (alineada con Excel V2-4 simulator):
        - factor_base = 1.0 → el año de inicio del contrato es la referencia,
          los salarios storage YA están expresados en valores del año de inicio.
        - pct_aumento = factor(anio+1) / factor(anio) - 1 → crecimiento anual
          aplicado a partir del mes_aplicacion_aumento (típicamente mes 13).

        Esto significa que para contratos multi-año, el ajuste anual se aplica
        como pct_aumento desde el mes 13 en adelante (consistente con Excel V2-4
        que muestra Aumento Acumulado = 1 en el año de inicio).
        """
        comp          = panel.componente_indexacion_humano
        anio_base     = self._anio_inicio(panel.fecha_inicio)
        factor_anio   = self._prov.get_factor_indexacion(comp, anio_base)
        factor_sig    = self._prov.get_factor_indexacion(comp, anio_base + 1)
        # Crecimiento ANUAL relativo (mes 13+):
        pct_aumento   = (factor_sig / factor_anio - 1.0) if factor_anio > 0 else 0.0
        # El factor BASE en mes 1 es 1.0 (año inicio = referencia).
        # El backend multiplicaba antes por factor_anio absoluto (acumulado desde 2025),
        # pero Excel V2-4 trata el año inicio como base 1.0 sin acumulación previa.
        factor_base = 1.0

        return ParametrosNomina(
            mes_inicio             = 1,
            mes_fin                = panel.meses_contrato,
            pct_aumento_salarial   = pct_aumento,
            # WAVE 3 (W3-2): Excel V2-7 Panel!L9 → panel.mes_ajuste_indexacion.
            # Legacy `panel.indexacion_mes_aplicacion` mantiene precedencia para no
            # romper payloads existentes; si no está, se usa el nuevo campo V2-7;
            # último recurso es la constante MES_INICIO_AJUSTE_ANUAL (=1).
            # `indexacion_mes_aplicacion` (legacy) ya es MES DEL CONTRATO (ej: 13).
            # `mes_ajuste_indexacion` (Panel!L9, NUEVO) es MES DEL CALENDARIO (ej: 6=junio)
            # y debe convertirse a contrato vía _calendario_a_contrato.
            mes_aplicacion_aumento = (
                panel.indexacion_mes_aplicacion
                if panel.indexacion_mes_aplicacion is not None
                else self._calendario_a_contrato(
                    panel.fecha_inicio,
                    panel.mes_ajuste_indexacion
                    if getattr(panel, "mes_ajuste_indexacion", None) is not None
                    else MES_INICIO_AJUSTE_ANUAL,
                )
            ),
            # REFACTOR costos_operativos: tarifa_dia_cap desde input usuario
            tarifa_dia_cap         = panel.tarifa_diaria_capacitacion,
            costo_examen_medico    = self._prov.get_examen_medico(ciudad),
            costo_estudio_seg      = 0.0,
            factor_indexacion_base = factor_base,
            meses_contrato         = panel.meses_contrato,
            tarifa_crucero         = float(getattr(panel, "tarifa_crucero", 0.0) or 0.0),
        )

    # ──────────────────────────────────────────────────────────────
    # Parámetros No Payroll
    # ──────────────────────────────────────────────────────────────

    def _construir_no_payroll(
        self,
        panel,
        sede: str,
        perfiles_a: List[PerfilCadenaAInput],  # REFACTOR: nuevo parámetro
    ) -> ParametrosNoPayroll:
        """
        Construye los parámetros de infraestructura para la sede del deal.

        REFACTOR costos_operativos: OPEX TI y CAPEX se calculan dinámicamente
        desde el input del usuario, no desde parametrización.
        """
        costos = self._prov.get_costo_no_payroll(sede)

        # REFACTOR: Calcular dinámicamente
        opex_ti = self._calcular_opex_ti_total(perfiles_a)
        # Excel V2-7: factor de diferimiento = (1 + tasa de interés mensual = Panel!L10).
        factor_capex = 1.0 + float(getattr(panel, 'tasa_mensual_financ', 0.0) or 0.0)
        inversiones_amortizables = self._calcular_inversiones_amortizables(
            perfiles_a, factor_capex, int(getattr(panel, 'meses_contrato', 1) or 1)
        )

        return ParametrosNoPayroll(
            opex_ti_por_estacion       = opex_ti,
            capex_por_estacion         = 0.0,
            inversiones_amortizables   = inversiones_amortizables,
            arriendo_por_estacion      = costos.get("arriendo", 0.0),
            energia_por_estacion       = costos.get("energia", 0.0),
            vigilancia_por_estacion    = costos.get("vigilancia", 0.0),
            aseo_por_estacion          = costos.get("aseo", 0.0),
            otros_fijos_por_estacion   = (costos.get("agua", 0.0)
                                          + costos.get("gas", 0.0)
                                          + costos.get("mantenimiento", 0.0)),
            capex_inicial_por_estacion = 0.0,
        )

    # ──────────────────────────────────────────────────────────────
    # Cadena B
    # ──────────────────────────────────────────────────────────────

    def _construir_cadena_b(self, cadena_b, panel) -> ParametrosCadenaB:
        """
        Construye los parámetros de la plataforma digital (Cadena B).

        Mapeo de costos:
          - opex_consumo_variable → non-HITL items added to channel opex_fijo; HITL items → costo_personal_hitl
          - dispositivos_sm      → opex_herramientas_sm (costo mensual, sin amortización)
          - equipo_sm salarios   → costo_personal_sm (nómina cargada SM × indexación)
          - inversion_plataforma → inversion_mensual (sin dispositivos)
        """
        items_hitl = [i for i in cadena_b.opex_consumo_variable if i.producto == "HITL"]
        items_canal = [i for i in cadena_b.opex_consumo_variable if i.producto != "HITL"]

        opex_consumo_por_canal = self._agregar_opex_consumo_por_canal(items_canal)
        costo_hitl_consumo = sum(i.valor_unitario * i.cantidad for i in items_hitl)

        canales = [
            CanalCadenaB(
                nombre            = c.nombre,
                modalidad         = c.modalidad,
                producto          = c.producto,
                tarifa_unitaria   = c.tarifa_unitaria,
                volumen_mensual   = c.volumen_mensual if c.activo else 0.0,
                opex_fijo         = c.opex_fijo + opex_consumo_por_canal.get(
                    (c.modalidad, c.producto), 0.0),
                pct_escalamiento  = c.pct_escalamiento,
                costo_escalamiento= c.costo_escalamiento,
                vol_escalamiento  = c.vol_escalamiento if c.activo else 0.0,
            )
            for c in cadena_b.canales
        ]

        opex_consumo = [
            ItemOpexConsumoB(
                nombre         = i.nombre,
                producto       = i.producto,
                modalidad      = i.modalidad,
                canal          = i.canal,
                valor_unitario = i.valor_unitario,
                cantidad       = i.cantidad,
                tipo_cobro     = i.tipo_cobro,
            )
            for i in cadena_b.opex_consumo_variable
        ]

        equipo_sm = [
            MiembroEquipo(
                rol             = m.rol,
                activo          = m.activo,
                pct_dedicacion  = m.pct_dedicacion,
                fte_equivalente = m.pct_dedicacion if m.activo else 0.0,
            )
            for m in cadena_b.equipo_sm
        ]

        dispositivos = [
            DispositivoSM(
                tipo               = d.tipo,
                costo_unitario     = d.costo_unitario,
                cantidad           = d.cantidad,
                meses_amortizacion = d.meses_amortizacion,
            )
            for d in cadena_b.dispositivos_sm
        ]

        # Convención Excel V2-4 (Tasas, TRM, Polizas!B8 = 1.0):
        # El factor base de indexación es 1.0 para el año de inicio del contrato.
        # Los salarios SM ya están en moneda del año de inicio.
        # El crecimiento anual se aplica desde mes_aplicacion_aumento (típicamente mes 13).
        factor_idx = 1.0
        # FTE base del equipo S&M (Excel V2-4 "Condiciones Cadena B" celda B79).
        # Multiplica la dedicación de cada rol activado para reflejar el tamaño real
        # del equipo dedicado a la operación.
        fte_equipo_sm = cadena_b.fte_equipo_sm
        costo_personal_sm = sum(
            self._nomina_service.calcular_sm(self._prov.get_salario_rol(m.rol))
            * m.pct_dedicacion
            * fte_equipo_sm
            for m in cadena_b.equipo_sm if m.activo
        ) * factor_idx
        # Costo mensual de dispositivos SM.
        # amortizar=True (default): costo repartido en meses_amortizacion.
        # amortizar=False (modo Excel V2-4 sin amortización): costo completo mensual.
        amortizar = cadena_b.amortizar_dispositivos_sm
        opex_dispositivos_sm = sum(
            (d.costo_unitario * d.cantidad / d.meses_amortizacion)
            if (amortizar and d.meses_amortizacion > 0)
            else (d.costo_unitario * d.cantidad)
            for d in cadena_b.dispositivos_sm
        )

        comp        = panel.componente_indexacion_humano
        anio_base   = self._anio_inicio(panel.fecha_inicio)
        factor_base = self._prov.get_factor_indexacion(comp, anio_base)
        factor_sig  = self._prov.get_factor_indexacion(comp, anio_base + 1)
        pct_aumento_personal = (factor_sig / factor_base - 1.0) if factor_base > 0 else 0.0

        return ParametrosCadenaB(
            canales               = canales,
            opex_consumo_variable = opex_consumo,
            equipo_sm             = equipo_sm,
            dispositivos_sm       = dispositivos,
            costo_personal_sm     = costo_personal_sm,
            opex_herramientas_sm  = opex_dispositivos_sm,
            costo_personal_hitl   = costo_hitl_consumo,
            opex_herramientas_hitl= 0.0,
            inversion_mensual     = cadena_b.inversion_plataforma,
            pct_aumento_personal      = pct_aumento_personal,
            # Legacy indexacion_mes_aplicacion = contract month; mes_ajuste = calendar → convert.
            mes_aplicacion_aumento    = (
                panel.indexacion_mes_aplicacion
                if panel.indexacion_mes_aplicacion is not None
                else self._calendario_a_contrato(
                    panel.fecha_inicio,
                    panel.mes_ajuste_indexacion
                    if getattr(panel, "mes_ajuste_indexacion", None) is not None
                    else MES_INICIO_AJUSTE_ANUAL,
                )
            ),
        )

    @staticmethod
    def _agregar_opex_consumo_por_canal(
        items,
    ) -> dict:
        """
        Agrupa los items de OPEX consumo variable por (modalidad, canal)
        y suma valor_unitario × cantidad para cada grupo.

        En el modelo de negocio, estos items (token IA, minutos WhatsApp, etc.)
        se clasifican como OPEX fijo del canal correspondiente.
        """
        resultado: dict = {}
        for i in items:
            clave = (i.modalidad, i.canal)
            resultado[clave] = resultado.get(clave, 0.0) + i.valor_unitario * i.cantidad
        return resultado

    # ──────────────────────────────────────────────────────────────
    # Cadena C
    # ──────────────────────────────────────────────────────────────

    def _construir_cadena_c(self, cadena_c, panel) -> ParametrosCadenaC:
        """Construye los parámetros de integración IA (Cadena C)."""
        canales = [
            CanalCadenaC(
                nombre             = c.nombre,
                modalidad          = c.modalidad,
                tarifa_proveedor   = c.tarifa_unitaria,
                volumen_mensual    = c.volumen_mensual if c.activo else 0.0,
                opex_fijo_integ    = c.opex_fijo_integ,
                opex_var_integ     = c.opex_var_integ,
                pct_escalamiento   = c.pct_escalamiento,
                costo_escalamiento = c.costo_escalamiento,
            )
            for c in cadena_c.canales
        ]

        equipo_transversal = [
            MiembroEquipo(
                rol             = m.rol,
                activo          = m.activo,
                pct_dedicacion  = m.pct_dedicacion,
                fte_equivalente = m.pct_dedicacion if m.activo else 0.0,
            )
            for m in cadena_c.equipo_transversal
        ]

        # equipo_integ: use salario_cargado from input when provided; fallback to parametrization.
        # Excel V2-8 · 'Costo Cadena C' equipo row: salario_cargado per FTE from v27 fixture = 4,284,360.05
        costo_equipo_integ = sum(
            (m.salario_cargado if m.salario_cargado is not None else self._prov.get_salario_rol(m.rol))
            * m.pct_dedicacion
            for m in cadena_c.equipo_transversal if m.activo
        )
        # Excel V2-8 · 'Costo Cadena C' equipo row: tools/equipment = Σ(precio × cantidad_atribuible)
        # from recurso_humano_transversal.opex (computers, licenses, workspace) = 1,159,602.60/mo
        opex_herramientas_integ = cadena_c.opex_herramientas_transversal

        # HITL: compute from equipo_hitl ratios and salario_cargado per role.
        # Vision P&G costo_c (row 55) excludes HITL; it is included in the financial
        # cost base (ICA/GMF) via costos_totales_c. See ResultadoCadenaC.total_pyg vs .total.
        vol_total_c = sum(
            c.volumen_mensual for c in cadena_c.canales if c.activo
        ) if cadena_c.canales else 0.0
        if vol_total_c > 0 and cadena_c.equipo_hitl:
            total_personas_hitl = sum(
                vol_total_c / m.ratio
                for m in cadena_c.equipo_hitl if m.activado and m.ratio > 0
            )
            costo_personal_hitl = sum(
                (vol_total_c / m.ratio) * m.salario_cargado
                for m in cadena_c.equipo_hitl if m.activado and m.ratio > 0
            )
            opex_herramientas_hitl = total_personas_hitl * cadena_c.opex_dispositivos_por_persona
        else:
            costo_personal_hitl = 0.0
            opex_herramientas_hitl = 0.0

        # Excel V2-8 · 'Tasas, TRM, Polizas'!C15:G15 ('20% SMMLV 80% IPC' cumulative) = 1.0 for ALL years 2025-2030
        # → effective annual technology increase rate = 0%: tarifa proveedor, OPEX, equipo are contractually flat
        pct_aumento_tecnologico = 0.0

        return ParametrosCadenaC(
            canales                 = canales,
            equipo_transversal      = equipo_transversal,
            costo_equipo_integ      = costo_equipo_integ,
            opex_herramientas_integ = opex_herramientas_integ,
            costo_personal_hitl     = costo_personal_hitl,
            opex_herramientas_hitl  = opex_herramientas_hitl,
            inversion_anual         = cadena_c.inversion_anual,
            pct_aumento_tecnologico = pct_aumento_tecnologico,
            tasa_interes_mensual    = float(
                panel.tasa_mensual_financ if getattr(panel, "tasa_mensual_financ", None) is not None
                else getattr(panel, "tasa_interes_mensual", None) or 0.0
            ),
            # Legacy indexacion_mes_aplicacion = contract month; mes_ajuste = calendar → convert.
            mes_aplicacion_aumento  = (
                panel.indexacion_mes_aplicacion
                if panel.indexacion_mes_aplicacion is not None
                else self._calendario_a_contrato(
                    panel.fecha_inicio,
                    panel.mes_ajuste_indexacion
                    if getattr(panel, "mes_ajuste_indexacion", None) is not None
                    else MES_INICIO_AJUSTE_ANUAL,
                )
            ),
        )

    # ──────────────────────────────────────────────────────────────
    # Parámetros de cálculo (rotación, examen anual)
    # ──────────────────────────────────────────────────────────────

    def _construir_parametros_calculo(self, panel, linea: str) -> ParametrosCalculo:
        """
        Construye los parámetros de cálculo operativo del deal.

        La rotación se toma del override del usuario si fue proporcionada;
        en caso contrario se usa el valor maestro por línea de negocio.
        """
        pct_rotacion = (panel.pct_rotacion
                        if panel.pct_rotacion is not None
                        else self._prov.get_pct_rotacion(linea))
        pct_examen_anual_val = getattr(panel, "pct_examen_anual", None)
        if pct_examen_anual_val is None:
            pct_examen_anual_val = self._prov.get_pct_examen_anual(linea)
        return ParametrosCalculo(
            pct_rotacion               = pct_rotacion,
            pct_examen_anual           = pct_examen_anual_val,
            pct_cumplimiento_variable  = self._prov.get_nomina_laboral_params()["pct_cumplimiento_variable"],
        )

    # ──────────────────────────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_rol(rol: str) -> str:
        """Normaliza nombre de rol para búsqueda flexible en diccionarios de ratios.
        
        Aplica las mismas reglas de normalización que PayrollParametrizationRepository._normalize():
        - Quita acentos (NFD decomposition)
        - Quita caracteres especiales (%, paréntesis)
        - Lowercase y collapsa espacios
        
        Esto permite que "Director de Performance" se encuentre como "director de performance".
        """
        import re
        import unicodedata
        nfd = unicodedata.normalize("NFD", rol)
        without_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        without_special = without_accents.replace("(", "").replace(")", "").replace("%", "")
        return re.sub(r"\s+", " ", without_special).strip().lower()

    def _get_salario_rol_safe(self, rol: str, contexto: str = "") -> float:
        """Get salary for a role with improved error handling and logging.
        
        Args:
            rol: Role name
            contexto: Description of context (e.g., "soporte para cadena_a")
            
        Returns:
            Salary amount
            
        Raises:
            DomainError with descriptive message if role not found
        """
        from nexa_engine.modules.shared.exceptions import DomainError, NotFoundError
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            return self._prov.get_salario_rol(rol)
        except (NotFoundError, KeyError) as e:
            msg = (
                f"Rol '{rol}' no encontrado en HR-Nomina. "
                f"Contexto: {contexto}. "
                f"Error: {str(e)}"
            )
            logger.error(f"[DOMAIN_ERROR] {msg}")
            raise DomainError(msg) from e
        except Exception as e:
            msg = (
                f"Error al buscar salario para rol '{rol}'. "
                f"Contexto: {contexto}. "
                f"Error: {str(e)}"
            )
            logger.error(f"[DOMAIN_ERROR] {msg}")
            raise DomainError(msg) from e

    @staticmethod
    def _calendario_a_contrato(fecha_inicio: str, mes_calendario: int) -> int:
        """Convierte un mes del calendario (1-12) al mes del contrato donde se aplica.

        Excel V2-7 interpreta Panel!L9 (mes_ajuste) como MES DEL AÑO: IF(MONTH>=L9,
        factor[YEAR], factor[YEAR-1]). El ajuste solo aplica la primera vez que el
        calendario alcanza ese mes DESPUÉS del inicio del contrato.

        Ejemplo: deal empieza junio (mes 6), ajuste en junio (L9=6):
          → Primera junio después del inicio = junio del año siguiente = contract month 13.
        Ejemplo: deal empieza marzo (mes 3), ajuste en junio (L9=6):
          → Primera junio = mes 4 del contrato.

        Returns:
            Mes del contrato (≥1) donde se aplica el primer ajuste.
        """
        start_month = mes_inicio_contrato(fecha_inicio)
        if mes_calendario > start_month:
            return mes_calendario - start_month + 1
        else:
            return 12 - start_month + mes_calendario + 1

    @staticmethod
    def _anio_inicio(fecha_inicio: str) -> int:
        """Extrae el año de la fecha de inicio del contrato (formato YYYY-MM-DD).

        FASE 1 — H1: No se permite fallback silencioso. Una fecha_inicio inválida
        es un error de entrada que debe detectarse explícitamente.
        """
        try:
            year = int(fecha_inicio[:4])
            if year < 2000 or year > 2100:
                raise ValueError(f"Año fuera de rango: {year}")
            return year
        except (ValueError, IndexError, TypeError) as e:
            raise ValueError(
                f"fecha_inicio inválida: '{fecha_inicio}'. "
                f"Se requiere formato YYYY-MM-DD con año entre 2000 y 2100. "
                f"Error: {e}"
            ) from e

__all__ = ["ContextBuilderPanelBCMixin"]
