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





class ContextBuilderPerfilesLightMixin:
    """Mixin: ContextBuilderPerfilesLightMixin."""

    def _construir_perfiles_a(self, cadena_a, linea: str,
                               meses_contrato: int, pct_rotacion: float,
                               complejidad_especialista: str = "ALTA",
                               factor_capex: float = 1.0):
        """
        Construye la lista completa de perfiles de Cadena A.

        Incluye tanto los perfiles base (agentes definidos por el usuario)
        como los perfiles de staff de soporte generados automáticamente
        a partir de los ratios maestros y las reglas de roles.
        """
        ratios = self._prov.get_ratios_staff(linea)
        staff_config = getattr(cadena_a, "staff_config", [])
        # Remove inactive staff roles from ratios so fte_examenes excludes them
        # (mirrors Excel Condiciones Cadena A: rows with activo=False → FTE = 0 → excluded).
        if staff_config:
            ratios_examenes = dict(ratios)
            for sc in staff_config:
                if not sc.activo:
                    rol_n = self._normalize_rol(sc.nombre)
                    ratios_examenes.pop(rol_n, None)
        else:
            ratios_examenes = ratios
        perfiles_base    = [self._construir_perfil_a(p, ratios_examenes, factor_capex=factor_capex,
                                                      meses_contrato=meses_contrato)
                            for p in cadena_a.perfiles]
        # EXCEL V2-8 CCA!C79/C80/C87: aggregate roles_excluidos_deal from all agent profiles.
        # roles_operativos[].incluye_en_deal=False propagated from request via PerfilCadenaAInput.
        roles_excluidos_deal: frozenset = frozenset().union(
            *(getattr(p, "roles_excluidos_deal", frozenset()) for p in cadena_a.perfiles)
        )
        perfiles_soporte = self._construir_perfiles_soporte(
            perfiles_base, linea, meses_contrato, pct_rotacion,
            complejidad_especialista=complejidad_especialista,
            staff_config=staff_config,
            detalles_recursos_humanos=getattr(cadena_a, "detalles_recursos_humanos", []),
            roles_excluidos_deal=roles_excluidos_deal)

        # Clasificar cargo_tipo en todos los perfiles desde HR-clasificacion_cargos.
        # El CargoClassifier normaliza claves (case/accent-insensitive) para cubrir
        # tanto los nombres originales (base) como los normalizados (soporte de ratios).
        try:
            clasificacion_cargos = self._prov.get_clasificacion_cargos()
        except Exception:
            clasificacion_cargos = {}
        classifier = CargoClassifier(clasificacion_cargos)
        for perfil, inp in zip(perfiles_base, cadena_a.perfiles):
            perfil.cargo_tipo = classifier.clasificar(inp.rol).value
        _pfx = "Soporte — "
        for perfil in perfiles_soporte:
            rol = perfil.nombre[len(_pfx):] if perfil.nombre.startswith(_pfx) else perfil.nombre
            perfil.cargo_tipo = classifier.clasificar(rol).value

        return perfiles_base + perfiles_soporte

    def _construir_perfil_a(self, p, ratios: dict = None, factor_capex: float = 1.0,
                            meses_contrato: int = 1) -> PerfilCadenaA:
        """
        Construye un perfil de agente base resolviendo salario y FTE de exámenes.

        El salario base se toma del override del usuario si fue especificado;
        en caso contrario se busca en la tabla de salarios por rol.

        El FTE efectivo para exámenes incluye la fracción proporcional de
        supervisores, formadores y monitores asignados a este perfil, dado
        que esos roles también requieren examen médico de ingreso.
        """
        salario_base    = (p.salario_base
                           if p.salario_base is not None
                           else self._prov.get_salario_rol(p.rol))
        # WAVE 3 (W3-4): respetar HR-Nomina costo_empresa_override (Excel V2-7).
        override_cargado = None
        try:
            override_cargado = self._prov.get_costo_empresa_override(p.rol)
        except Exception:
            override_cargado = None
        if override_cargado is not None:
            salario_cargado_total = override_cargado
        else:
            salario_cargado_total = self._nomina_service.calcular(salario_base, p.comision_pct)

        fte_examenes = self._calcular_fte_examenes(p, ratios)
        opex_fijo_mensual = self._calcular_opex_fijo_mensual_perfil(p)
        inversiones_amortizables = self._calcular_inversiones_amortizables_perfil(p, factor_capex, meses_contrato)

        return PerfilCadenaA(
            nombre            = p.nombre,
            modalidad         = p.modalidad,
            canal             = p.canal,
            fte               = p.fte,
            cargos_adicionales = getattr(p, "cargos_adicionales", 0.0),  # EXCEL V2-8 CCA!E26/F26/G26
            fte_soporte_overrides = dict(getattr(p, "fte_soporte_overrides", {}) or {}),  # EXCEL V2-8 CCA!E95
            pct_presencia     = p.pct_presencia,
            salario_base      = salario_base,
            salario_cargado   = salario_cargado_total,
            comision_pct      = p.comision_pct,
            dias_cap_inicial  = p.dias_cap_inicial,
            dias_cap_rotacion = p.dias_cap_rotacion,
            tmo_segundos      = p.tmo_segundos,
            incluye_examenes  = p.incluye_examenes,
            incluye_seguridad = p.incluye_seguridad,
            incluye_crucero   = getattr(p, "incluye_crucero", False),
            es_soporte                  = False,
            fte_examenes                = fte_examenes,
            modelo_cobro                = p.modelo_cobro,
            pct_fijo                    = p.pct_fijo,
            no_payroll_mensual          = p.no_payroll_mensual,
            inversiones_mensual         = p.inversiones_mensual,
            inversiones_mensual_recurrente = p.inversiones_mensual_recurrente,
            costos_fijos_mensual        = p.costos_fijos_mensual,
            cadena_b_mensual            = p.cadena_b_mensual,
            costos_financieros_mensual  = p.costos_financieros_mensual,
            vol_cadena_a_mensual        = p.vol_cadena_a_mensual,
            opex_fijo_mensual           = opex_fijo_mensual,
            inversiones_amortizables    = inversiones_amortizables,
        )

    def _calcular_fte_examenes(self, perfil, ratios: dict) -> float:
        """
        Calcula el FTE efectivo para el costo de exámenes médicos de un perfil.

        El FTE de exámenes es mayor que el FTE del perfil base porque incluye
        la fracción de roles operacionales que son contratados junto con ese
        bloque de agentes y también deben examinarse al ingresar.

        Roles incluidos (consistente con Excel V2-4 'Condiciones Cadena A' W41:W45):
        - Formadores
        - Monitor de Calidad
        - Supervisor
        - Validador

        Returns:
            FTE efectivo de exámenes, o 0.0 si el perfil no aplica exámenes
            o no hay ratios disponibles.
        """
        if not perfil.incluye_examenes or not ratios:
            return 0.0

        # Roles que se examinan junto con el agente base (Excel V2-4 W41:W45):
        roles_examenes = ["Formadores", "Monitor de Calidad", "Supervisor", "Validador"]
        extra = sum(
            perfil.fte / ratios.get(self._normalize_rol(rol), 1)
            for rol in roles_examenes
            if ratios.get(self._normalize_rol(rol), 0) > 0
        )
        return perfil.fte + extra


__all__ = ["ContextBuilderPerfilesLightMixin"]
