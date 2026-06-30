"""Staff ratios and rules methods.

Mixin for PayrollParametrizationRepository — FASE Z.2.
"""

from __future__ import annotations
import logging
import re
import json
from typing import Any, Dict, Optional
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.shared.exceptions import (
    ParametrizationError,
    ParametrizationNotFoundError,
    DomainError,
)

logger = logging.getLogger(__name__)


class PayrollStaffingMixin:
    """Mixin: Staff ratios and rules methods."""

    def get_reglas_staff(self) -> Dict[str, Any]:
        """Reglas de categorización de roles de soporte.

        Fuente: HR-reglas_staff (sección en storage JSON) O construida automáticamente
        desde HR-Ratios si reglas_staff no existe.

        Si no encuentra reglas_staff explícitas en el JSON, construye reglas por defecto:
        - rol_jefe_comercial: "Director de cuentas"
        - rol_aprendiz_sena: "Aprendiz SENA"
        - rol_inclusion: "Inclusión"
        - roles_especiales: ["Especialista de Proyectos"]
        - roles_excluidos_ratios: [roles sin incluir en ratios]

        Returns:
            Dict con claves: rol_jefe_comercial, rol_aprendiz_sena, rol_inclusion,
            roles_excluidos_ratios, roles_especiales.

        Raises:
            ParametrizationError: si ni reglas_staff ni ratios están disponibles.
        """
        self._ensure_hr_loaded()

        # Intentar cargar reglas_staff explícitas
        reglas = self._hr_data.get("reglas_staff")
        if reglas:
            logger.info(
                "[PARAM_SOURCE] parameter=reglas_staff source=HR-reglas_staff (explicit)"
            )
            return dict(reglas)

        # Si no existen, construir automáticamente desde ratios
        ratios_data = self._hr_data.get("ratios", [])
        if not ratios_data:
            raise ParametrizationError(
                "HR-reglas_staff section missing and HR-Ratios empty. "
                "Need either explicit reglas_staff or ratios data.",
                module="hr",
            )

        # Extraer todos los cargos únicos de ratios
        cargos_en_ratios = set()
        for row in ratios_data:
            cargo = row.get("cargo", "").strip()
            if cargo:
                cargos_en_ratios.add(cargo)

        # Definir roles especiales predeterminados
        rol_jefe_comercial = "Director de cuentas"
        rol_aprendiz_sena = "Aprendiz SENA"
        rol_inclusion = "Inclusión"
        roles_especiales = ["Especialista de Proyectos"]

        # Roles que no se incluyen en ratios (siempre agregados manualmente)
        roles_excluidos = ["Validador"]  # Roles sin incluir_en_deal=False

        # Construir reglas por defecto
        default_reglas = {
            "rol_jefe_comercial": rol_jefe_comercial,
            "rol_aprendiz_sena": rol_aprendiz_sena,
            "rol_inclusion": rol_inclusion,
            "roles_especiales": roles_especiales,
            "roles_excluidos_ratios": roles_excluidos,
        }

        logger.info(
            "[PARAM_SOURCE] parameter=reglas_staff source=HR-Ratios (auto-constructed) "
            "cargos=%d",
            len(cargos_en_ratios),
        )
        return default_reglas

    def get_ratios_staff(self, linea: str) -> Dict[str, float]:
        """Ratios de staff (cargo → agentes_por_cargo) para una línea de negocio.

        Fuente: HR-Ratios sheet.

        Resolución: busca primero ratios específicos para la línea. Si no encuentra,
        usa ratios por defecto (servicio="") que aplican globalmente a todas las líneas.

        Duplicado handling: Si un cargo aparece múltiples veces, toma el primer
        valor no nulo encontrado.

        Args:
            linea: Línea de negocio.

        Returns:
            Dict {cargo_normalizado: agentes_por_cargo}. Claves normalizadas para
            permitir búsqueda flexible (case-insensitive, sin acentos).
            Float para preservar precisión de ratios fraccionarios
            (ej. 24.76 para Especialista de Proyectos).

        Raises:
            ParametrizationError: si HR-Ratios está vacío o no hay ratios disponibles
                                  (ni específicos ni por defecto).
        """
        self._ensure_hr_loaded()
        ratios_data = self._hr_data.get("ratios", [])
        if not ratios_data:
            raise ParametrizationError("HR-Ratios sheet is empty", module="hr")

        result: Dict[str, float] = {}
        linea_norm = self._normalize(linea)

        # FASE 1: Buscar ratios específicos para esta línea
        for row in ratios_data:
            if self._normalize(row.get("servicio", "")) == linea_norm:
                cargo = row.get("cargo", "")
                agentes = row.get("agentes")
                # Only set if not already set (first non-null value wins)
                # Use normalized key to allow flexible access
                if cargo and agentes is not None:
                    cargo_norm = self._normalize(cargo)
                    if cargo_norm not in result:
                        result[cargo_norm] = float(agentes)

        # FASE 2: Si no encontramos ratios específicos, usar ratios por defecto
        # (donde servicio="") que aplican globalmente
        if not result:
            logger.debug(
                "[PARAMETRIZATION] No line-specific ratios for '%s', "
                "falling back to default ratios (servicio='')",
                linea,
            )
            for row in ratios_data:
                if row.get("servicio", "").strip() == "":  # Empty/default ratios
                    cargo = row.get("cargo", "")
                    agentes = row.get("agentes")
                    # Only set if not already set (first non-null value wins)
                    # Use normalized key to allow flexible access
                    if cargo and agentes is not None:
                        cargo_norm = self._normalize(cargo)
                        if cargo_norm not in result:
                            result[cargo_norm] = float(agentes)

        logger.info(
            "[PARAM_SOURCE] parameter=ratios_staff linea=%s source=HR-Ratios "
            "roles=%d %s",
            linea,
            len(result),
            "(line-specific)" if linea_norm != "" else "(defaults)",
        )

        if not result:
            raise ParametrizationError(
                f"No ratios found for linea='{linea}' in HR-Ratios "
                "(neither line-specific nor defaults). "
                "Verifique que HR-Ratios contiene datos.",
                module="hr",
            )

        return result

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _ensure_hr_loaded(self) -> None:
        """Load HR parametrization if not already loaded."""
        if self._hr_data is None:
            try:
                self._hr_data = self._resolver.get_active_hr()

                # Log top-level structure
                logger.info(
                    "[PAYROLL_REPO] Top-level keys loaded: %s",
                    list(self._hr_data.keys()),
                )

                # Log full key structure for debugging
                logger.debug(
                    "[PAYROLL_REPO] Full HR data structure: %s",
                    json.dumps(list(self._hr_data.keys()), indent=2),
                )

            except ParametrizationNotFoundError as e:
                raise ParametrizationError(
                    "Cannot load payroll parameters: HR parametrization not found",
                    module="hr",
                ) from e

        # Lazy-load rotacion_ausentismo cache on first use
        if not self._rotacion_loaded:
            self._load_rotacion_ausentismo_cache()


__all__ = ["PayrollStaffingMixin"]
