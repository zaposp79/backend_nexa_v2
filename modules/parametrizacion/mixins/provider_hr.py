"""HR (payroll, rotacion, ausentismo) getter methods for ParametrizationProvider.

Mixin for ParametrizationProvider — extracted FASE Z.2.
Behavior unchanged; self references resolve via Python MRO.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from nexa_engine.modules.shared.exceptions import ParametrizationError
from nexa_engine.modules.parametrizacion.shared.helpers.canonicalization import (
    canonical_channel, canonical_complejidad, canonical_modalidad,
    canonical_role, canonical_service,
)
logger = logging.getLogger(__name__)


class ProviderHrMixin:
    """Mixin: HR (payroll, rotacion, ausentismo) getter methods for ParametrizationProvider."""

    def get_salario_rol(self, rol: str) -> float:
        """Salario base para un rol. Fuente: HR-Nomina.

        Args:
            rol: Nombre del rol (ej. "Director de cuentas").

        Returns:
            Salario base como float.

        Raises:
            ParametrizationError: si el rol no existe en HR-Nomina.
        """
        value = self._payroll.get_salary_for_role(rol)
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_salario_rol rol=%s value=%s source=HR-Nomina",
            rol, value,
        )
        return value


    def get_comision_pct_rol(self, rol: str) -> float:
        """% Comisión recibido para un rol. Fuente: HR-Nomina col 'ComisionPct'.

        Excel V2-4 asigna comisión a algunos roles de soporte (e.g. Director cuentas 5%,
        GTR 10%) además del Agente Básico. Estas comisiones se suman al payroll total.

        Args:
            rol: Nombre del rol.

        Returns:
            % de comisión como decimal (e.g. 0.05 = 5%). 0.0 si el rol no tiene comisión.
        """
        # Acceder al HR data via _payroll repository
        self._payroll._ensure_hr_loaded()
        nomina = self._payroll._hr_data.get("nomina", [])
        rol_norm = rol.strip().lower()
        for row in nomina:
            row_rol = str(row.get("rol", "")).strip().lower()
            if row_rol == rol_norm:
                pct = float(row.get("comision_pct", 0.0) or 0.0)
                logger.debug(
                    "[REPOSITORY] operation=get_comision_pct_rol rol=%s value=%s source=HR-Nomina",
                    rol, pct,
                )
                return pct
        return 0.0


    def get_examen_medico(self, ciudad: str) -> float:
        """Costo del examen médico de ingreso para una ciudad. Fuente: HR-Med-Seg.

        Args:
            ciudad: Nombre de la ciudad.

        Returns:
            Costo en COP.

        Raises:
            ParametrizationError: si la ciudad no existe en HR-Med-Seg.
        """
        value = self._infrastructure.get_medical_exam_cost(ciudad)
        logger.debug(
            "[REPOSITORY] repository=InfrastructureParametrizationRepository "
            "operation=get_examen_medico ciudad=%s value=%s source=HR-Med-Seg",
            ciudad, value,
        )
        return value


    def get_nomina_laboral_params(self) -> Dict[str, Any]:
        """Parámetros completos de nómina laboral para NominaCargadaService.

        Fuente: HR-Salarios + HR-SegSocial + HR-Prestaciones + OP-Config.

        Returns dict con:
            salario_minimo, auxilio_transporte, dotaciones_mensual,
            pct_cumplimiento_variable,
            factor_alto_salario_smmlv, factor_corrector_alto_salario,
            aportes_patronales (dict), prestaciones (dict).

        Raises:
            ParametrizationError: si cualquier clave requerida falta en HR o OP.
        """
        base    = self._payroll.get_base_salary_data()
        aportes = self._payroll.get_all_contributions()
        prests  = self._payroll.get_all_benefits()
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_nomina_laboral_params source=HR"
        )
        try:
            return {
                "salario_minimo":            base["salario_minimo"],
                "auxilio_transporte":        base["auxilio_transporte"],
                "dotaciones_mensual":        base["dotaciones_mensual"],
                "pct_cumplimiento_variable": base["pct_cumplimiento_variable"],
                # Umbrales de alto salario — fuente: HR (Ley 1819 de 2016)
                "factor_alto_salario_smmlv":     base.get("factor_alto_salario_smmlv", 10.0),
                "factor_corrector_alto_salario": base.get("factor_corrector_alto_salario", 0.70),
                "aportes_patronales": {
                    "salud":       aportes["Salud"],
                    "pension":     aportes["Fondo de pensión"],
                    "arl_staff":   aportes["ARL"],
                    "arl_agentes": aportes["ARL"],
                    "caja":        aportes["Caja"],
                    "icbf_sena":   aportes["ICBF + Sena"],
                },
                "prestaciones": {
                    "cesantias":        prests["Cesantías"],
                    "primas":           prests["Primas"],
                    "interes_cesantia": prests["Interes a la cesantía"],
                    "vacaciones":       prests["Vacaciones"],
                },
            }
        except KeyError as ke:
            raise ParametrizationError(
                f"HR parametrization missing required key: {ke}. "
                f"Available aportes: {list(aportes.keys())}, "
                f"prestaciones: {list(prests.keys())}, "
                f"salarios: {list(base.keys())}",
                module="hr",
            ) from ke

    # ──────────────────────────────────────────────────────────────────────────
    # Rotación / Ausentismo  (HR-rotacion_ausentismo)
    # ──────────────────────────────────────────────────────────────────────────


    def _resolve_linea(self, linea: str) -> str:
        """WAVE 5: canonicalize a line-of-business name semantically.

        Resolves case-insensitive, accent-insensitive, and alias-aware variants
        (e.g. "SAC" → "Sac", "S.A.C" → "Sac", "Backoffice" → "Captura de Datos").
        See ``nexa_engine.modules.shared.canonicalization`` for the alias tables.

        The canonical form is what the storage JSON contains; calculators may
        still pass the user-provided form and this layer will translate.
        """
        return canonical_service(linea)


    def _resolve_role(self, rol: str) -> str:
        """WAVE 5: canonicalize an HR role name (Supervisor, GTR, ...)."""
        return canonical_role(rol)


    def get_pct_rotacion(self, linea: str) -> float:
        """Porcentaje de rotación mensual para una línea de negocio.

        Fuente primaria: HR-rotacion_ausentismo.
        Fallback (new productiva schema): OP-Costo global 'Porcentaje de Rotación'.

        Args:
            linea: Línea de negocio (ej. 'Cobranzas', 'SAC').

        Returns:
            Tasa mensual como decimal (ej. 0.09 = 9%).

        Raises:
            ParametrizationError: si no existe en HR ni en OP-Costo.
        """
        canon = self._resolve_linea(linea)
        try:
            try:
                value = self._payroll.get_pct_rotacion(canon)
            except ParametrizationError:
                if canon != linea:
                    value = self._payroll.get_pct_rotacion(linea)
                else:
                    raise
        except ParametrizationError:
            fallback = self._financial.get_global_pct_rotacion()
            if fallback is not None:
                logger.warning(
                    "[REPOSITORY] get_pct_rotacion linea=%s — HR-AutRot missing, "
                    "using OP-Costo global fallback=%.4f",
                    linea, fallback,
                )
                return fallback
            raise
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_pct_rotacion linea=%s canon=%s value=%s source=HR-rotacion_ausentismo",
            linea, canon, value,
        )
        return value


    def get_pct_ausentismo(self, linea: str) -> float:
        """Porcentaje de ausentismo para una línea de negocio.

        Fuente primaria: HR-rotacion_ausentismo.
        Fallback (new productiva schema): OP-Costo global 'Porcentaje de Ausentismo'.

        Raises:
            ParametrizationError: si no existe en HR ni en OP-Costo.
        """
        canon = self._resolve_linea(linea)
        try:
            try:
                value = self._payroll.get_pct_ausentismo(canon)
            except ParametrizationError:
                if canon != linea:
                    value = self._payroll.get_pct_ausentismo(linea)
                else:
                    raise
        except ParametrizationError:
            fallback = self._financial.get_global_pct_ausentismo()
            if fallback is not None:
                logger.warning(
                    "[REPOSITORY] get_pct_ausentismo linea=%s — HR-AutRot missing, "
                    "using OP-Costo global fallback=%.4f",
                    linea, fallback,
                )
                return fallback
            raise
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_pct_ausentismo linea=%s canon=%s value=%s source=HR-rotacion_ausentismo",
            linea, canon, value,
        )
        return value


    def get_pct_examen_anual(self, linea: str) -> float:
        """Porcentaje de exámenes médicos anuales para una línea de negocio.

        Fuente primaria: HR-rotacion_ausentismo.
        Fallback (new productiva schema sin HR-AutRot): 1.0 (100% de agentes).

        Raises:
            ParametrizationError: si no existe en HR y el fallback no aplica.
        """
        canon = self._resolve_linea(linea)
        try:
            try:
                value = self._payroll.get_pct_examen_anual(canon)
            except ParametrizationError:
                if canon != linea:
                    value = self._payroll.get_pct_examen_anual(linea)
                else:
                    raise
        except ParametrizationError:
            fallback = self._financial.get_global_pct_examen_anual()
            logger.warning(
                "[REPOSITORY] get_pct_examen_anual linea=%s — HR-AutRot missing, "
                "using default fallback=%.4f",
                linea, fallback,
            )
            return fallback
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_pct_examen_anual linea=%s canon=%s value=%s source=HR-rotacion_ausentismo",
            linea, canon, value,
        )
        return value

    # ──────────────────────────────────────────────────────────────────────────
    # Costos operativos  (HR-costos_operativos)
    # ──────────────────────────────────────────────────────────────────────────


    def get_reglas_staff(self) -> Dict[str, Any]:
        """Reglas de categorización de roles de soporte.

        Fuente: HR-reglas_staff.

        Returns:
            Dict con claves: rol_jefe_comercial, rol_aprendiz_sena, rol_inclusion,
            roles_excluidos_ratios, roles_especiales, y opcionalmente
            roles_rotacion, roles_inicial.

        Raises:
            ParametrizationError: si la sección no existe en HR.
        """
        value = self._payroll.get_reglas_staff()
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_reglas_staff source=HR-reglas_staff"
        )
        return value


    def get_ratios_staff(self, linea: str) -> Dict[str, float]:
        """Ratios de staff (cargo → agentes_por_cargo) para una línea de negocio.

        Fuente: HR-Ratios.

        Args:
            linea: Línea de negocio.

        Returns:
            Dict {cargo: agentes_por_cargo}.

        Raises:
            ParametrizationError: si HR-Ratios está vacío.
        """
        canon = canonical_service(linea)
        try:
            value = self._payroll.get_ratios_staff(canon)
        except ParametrizationError:
            if canon != linea:
                value = self._payroll.get_ratios_staff(linea)
            else:
                raise
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_ratios_staff linea=%s canon=%s roles=%d source=HR-Ratios",
            linea, canon, len(value),
        )
        return value


    def get_complejidad_especialista(self) -> dict:
        """Retorna mapa de complejidad → multiplicador para Especialista de Proyectos.

        Fuente: HR-complejidad_especialista en parametrización activa.

        Returns:
            {"BAJA": 0.20, "MEDIA": 0.50, "ALTA": 0.50}

        Raises:
            ParametrizationError: si la clave no existe en HR.
        """
        self._payroll._ensure_hr_loaded()
        data = self._payroll._hr_data.get("complejidad_especialista")
        if data is None:
            raise ParametrizationError(
                "HR parametrization missing 'complejidad_especialista'. "
                "Verifique storage/parametrization/hr/*.json",
                module="hr",
            )
        logger.debug(
            "[PARAMETRIZATION] operation=get_complejidad_especialista "
            "source=HR-complejidad_especialista"
        )
        return data


    def get_clasificacion_cargos(self) -> dict:
        """Retorna mapa de rol → tipo de cargo para CargoClassifier.

        Fuente: HR-clasificacion_cargos en parametrización activa.

        Returns:
            {"Validador": "VALIDADOR", "Supervisor": "OPERATIVO", ...}

        Raises:
            ParametrizationError: si la clave no existe en HR.
        """
        self._payroll._ensure_hr_loaded()
        data = self._payroll._hr_data.get("clasificacion_cargos")
        if data is None:
            raise ParametrizationError(
                "HR parametrization missing 'clasificacion_cargos'. "
                "Verifique storage/parametrization/hr/*.json",
                module="hr",
            )
        logger.debug(
            "[PARAMETRIZATION] operation=get_clasificacion_cargos "
            "source=HR-clasificacion_cargos roles=%d",
            len(data),
        )
        return data

    def get_smmlv(self) -> float:
        """SMMLV vigente — fuente canónica: HR-Salarios → 'Salario Mínimo'.

        No usar business_rules.constantes_regulatorias.smmlv (LEGACY_NON_CANONICAL).
        """
        params = self.get_nomina_laboral_params()
        return float(params["salario_minimo"])

    # ──────────────────────────────────────────────────────────────────────────
    # WAVE 2 — Excel V2-7 defaults (op.v2_7_defaults)
    # ──────────────────────────────────────────────────────────────────────────



__all__ = ["ProviderHrMixin"]
