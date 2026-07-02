"""Salary, contributions and benefits methods.

Mixin for PayrollParametrizationRepository — FASE Z.2.
"""
from __future__ import annotations
import logging
import unicodedata
from typing import Any, Dict, Optional
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.shared.exceptions import ParametrizationError, ParametrizationNotFoundError, DomainError
logger = logging.getLogger(__name__)


class PayrollSalaryMixin:
    """Mixin: Salary, contributions and benefits methods."""

    def get_salary_for_role(self, rol: str, tipo: str = "Empleado") -> float:
        """Get salary for a cargo. Fuente: HR-Nomina (columna Cargo).

        Args:
            rol: Nombre del cargo (e.g., "Director de cuentas").
            tipo: Mantenido por compatibilidad de firma; ya no existe en HR-Nomina.

        Returns:
            Salary amount.

        Raises:
            RoleNotFoundError: if cargo not found.
        """
        self._ensure_hr_loaded()

        nomina = self._hr_data.get("nomina", [])
        if not nomina:
            raise ParametrizationError("HR-Nomina sheet is empty", module="hr")

        rol_norm = self._normalize(rol)
        for row in nomina:
            if self._normalize(row.get("cargo", "")) == rol_norm:
                salario = row.get("salario")
                if salario is not None:
                    logger.debug("[PARAMETRIZATION] Salary for %s: %s", rol, salario)
                    return float(salario)

        raise RoleNotFoundError(f"Cargo '{rol}' not found in HR-Nomina")

    @staticmethod

    def _normalize(text: str) -> str:
        """Normalize text for fuzzy matching:
        - Strip diacritical marks (tildes, accents)
        - Remove special characters (%, parentheses)
        - Lowercase and collapse extra spaces
        """
        import re
        # Strip accents via NFD decomposition
        nfd = unicodedata.normalize("NFD", text)
        without_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        # Remove special characters: parentheses and %
        without_special = without_accents.replace("(", "").replace(")", "").replace("%", "")
        # Collapse whitespace
        return re.sub(r"\s+", " ", without_special).strip().lower()


    def get_contributions(self, ssparafiscales: str) -> Dict[str, float]:
        """Get social security/parafiscal contribution rates.

        Args:
            ssparafiscales: Contribution type (e.g., "Salud", "Pensión").

        Returns:
            Dict with 'proporcion' rate.

        Raises:
            ContributionNotFoundError: if type not found.
        """
        self._ensure_hr_loaded()

        seg_social = self._hr_data.get("seg_social", [])
        if not seg_social:
            raise ParametrizationError("HR-SegSocial sheet is empty", module="hr")

        for row in seg_social:
            if row.get("ssparafiscales") == ssparafiscales:
                proporcion = float(row.get("proporcion", 0))
                logger.debug(f"[PARAMETRIZATION] Contribution {ssparafiscales}: {proporcion}")
                return {"proporcion": proporcion}

        raise ContributionNotFoundError(f"Contribution '{ssparafiscales}' not found in HR-SegSocial")


    def get_benefits(self, prestaciones: str) -> float:
        """Get benefit rate.

        Args:
            prestaciones: Benefit type (e.g., "Prima", "Cesantías").

        Returns:
            Benefit rate as decimal (e.g., 0.0833 for 8.33%).

        Raises:
            BenefitNotFoundError: if benefit not found.
        """
        self._ensure_hr_loaded()

        prestaciones_data = self._hr_data.get("prestaciones", [])
        if not prestaciones_data:
            raise ParametrizationError("HR-Prestaciones sheet is empty", module="hr")

        for row in prestaciones_data:
            if row.get("prestaciones") == prestaciones:
                valor = float(row.get("valor", 0))
                logger.debug(f"[PARAMETRIZATION] Benefit {prestaciones}: {valor}")
                return valor

        raise BenefitNotFoundError(f"Benefit '{prestaciones}' not found in HR-Prestaciones")


    def get_base_salary_data(self) -> Dict[str, float]:
        """Return salary base constants from HR-Salarios sheet.

        Returns dict with keys:
            salario_minimo, auxilio_transporte, dotaciones_mensual, pct_cumplimiento_variable,
            factor_alto_salario_smmlv, factor_corrector_alto_salario

        Handles:
        - Both "Dotaciones (mensual)" and "Dotaciones (annual)" formats
        - Normalized servicio names (case-insensitive, accent-insensitive)
        - Converts annual dotations to monthly by dividing by 12
        """
        self._ensure_hr_loaded()
        salarios = self._hr_data.get("salariobasico", [])

        # Primary mapping: exact matches for backward compatibility
        mapping = {
            "Salario Mínimo":                        "salario_minimo",
            "Auxilio Transporte":                    "auxilio_transporte",
            "Dotaciones (mensual)":                  "dotaciones_mensual",
            "%Cumplimiento Variable":                "pct_cumplimiento_variable",
            "Factor Alto Salario (SMMLV)":           "factor_alto_salario_smmlv",
            "Factor Corrector Alto Salario":         "factor_corrector_alto_salario",
        }

        # Normalized mapping for fuzzy matching
        normalized_mapping = {
            self._normalize(k): v for k, v in mapping.items()
        }

        result: Dict[str, float] = {}
        dotaciones_annual = None

        for row in salarios:
            servicio = row.get("servicio", "").strip()
            valor = row.get("valor")

            if valor is None:
                continue

            # Try exact mapping first
            key = mapping.get(servicio)
            if key:
                result[key] = float(valor)
                continue

            # Try normalized mapping
            servicio_norm = self._normalize(servicio)
            key = normalized_mapping.get(servicio_norm)
            if key:
                result[key] = float(valor)
                continue

            # Special case: Dotaciones (annual) → divide by 12
            if "dotaciones" in servicio_norm and "annual" in servicio_norm:
                dotaciones_annual = float(valor)

        # Apply annual dotations conversion if monthly not already set
        if "dotaciones_mensual" not in result and dotaciones_annual is not None:
            result["dotaciones_mensual"] = dotaciones_annual / 12.0

        return result


    def get_all_contributions(self) -> Dict[str, float]:
        """Return all SS/parafiscal contribution rates from HR-SegSocial.

        Returns dict mapping ssparafiscales name → proporcion.
        """
        self._ensure_hr_loaded()
        return {
            row["ssparafiscales"]: float(row.get("proporcion", 0))
            for row in self._hr_data.get("seg_social", [])
            if row.get("ssparafiscales")
        }


    def get_all_benefits(self) -> Dict[str, float]:
        """Return all benefit rates from HR-Prestaciones.

        Returns dict mapping prestacion name → valor.
        """
        self._ensure_hr_loaded()
        return {
            row["prestaciones"]: float(row.get("valor", 0))
            for row in self._hr_data.get("prestaciones", [])
            if row.get("prestaciones")
        }

    # -----------------------------------------------------------------------
    # Rotación / Ausentismo (HR-RotacionAusentismo)
    # -----------------------------------------------------------------------


    def get_costo_operativo(self, clave: str) -> float:
        """Retorna un costo/parámetro operativo del motor por su clave.

        Fuente: HR-costos_operativos (sección en storage JSON).

        Claves disponibles:
          tarifa_dia_cap, opex_ti_por_estacion,
          capex_recurrente_por_estacion, capex_inicial_por_estacion,
          pct_aumento_tecnologico_anual, mes_inicio_ajuste_anual

        Raises:
            ParametrizationError: si la sección o clave no existe.
        """
        self._ensure_hr_loaded()
        tabla = self._hr_data.get("costos_operativos")
        if not tabla:
            raise ParametrizationError(
                "HR-costos_operativos section missing. "
                "Add 'costos_operativos' key to active HR parametrization JSON.",
                module="hr",
            )
        for row in tabla:
            if row.get("clave") == clave:
                val = row.get("valor")
                if val is None:
                    raise ParametrizationError(
                        f"Valor missing for costo_operativo '{clave}' in HR",
                        module="hr",
                    )
                v = float(val)
                logger.info(
                    "[PARAM_SOURCE] parameter=%s source=HR-costos_operativos value=%s", clave, v,
                )
                return v
        raise ParametrizationError(
            f"Costo operativo '{clave}' not found in HR-costos_operativos. "
            f"Available: {[r.get('clave') for r in tabla]}",
            module="hr",
        )

    # -----------------------------------------------------------------------
    # Reglas de Staff (HR-reglas_staff)
    # -----------------------------------------------------------------------



__all__ = ["PayrollSalaryMixin"]
