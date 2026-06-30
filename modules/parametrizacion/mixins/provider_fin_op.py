"""Financial, OP and GN getter methods for ParametrizationProvider.

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


class ProviderFinOpMixin:
    """Mixin: Financial, OP and GN getter methods for ParametrizationProvider."""

    def tasa_mensual_financiacion(self) -> float:
        """
        Tasa mensual de financiación para amortización de inversiones (CadenaC).

        Fuente: OP-Config → clave='tasa_financiacion_mensual'

        Returns:
            Tasa como decimal.

        Raises:
            ParametrizationError: si no existe en OP-Config.
        """
        value = self._financial.get_tasa_financiacion()
        logger.debug(
            "[REPOSITORY] repository=FinancialParametrizationRepository "
            "operation=get_tasa_financiacion value=%s source=OP-Config",
            value,
        )
        return value


    def get_rampup(self, linea_negocio: str, mes: int) -> float:
        """
        Factor de ramp-up operacional para el mes dado.

        Fuente: HR-Campana → `get_campaign_value(linea, mes)`
        Cobertura: 60 meses por línea de negocio.

        Si la línea o el mes no existen → retorna 1.0 (operación plena) con WARNING.
        Este es el único fallback permitido: una línea desconocida opera al 100%
        por definición conservadora, no por un hardcode de negocio.

        Args:
            linea_negocio: Nombre de la línea (ej. "Cobranzas").
            mes:           Mes del contrato (1-based).

        Returns:
            Factor ramp-up en [0.0, 1.0].
        """
        canon = canonical_service(linea_negocio)
        try:
            try:
                value = self._profitability.get_campaign_value(canon, mes)
            except Exception:
                if canon != linea_negocio:
                    value = self._profitability.get_campaign_value(linea_negocio, mes)
                else:
                    raise
            logger.debug(
                "[REPOSITORY] repository=ProfitabilityParametrizationRepository "
                "operation=get_rampup linea=%s canon=%s mes=%d value=%s source=HR-Campana",
                linea_negocio, canon, mes, value,
            )
            return value

        except Exception as exc:
            logger.warning(
                "[REPOSITORY] repository=ProfitabilityParametrizationRepository "
                "operation=get_rampup linea=%s mes=%d fallback=1.0 reason=%s",
                linea_negocio, mes, exc,
            )
            return 1.0


    def get_tasa_polizas_efectiva(self, mes: int) -> float:
        """
        Tasa efectiva de pólizas de seguros activas en el mes.

        Fuente: OP-Poliza → `get_effective_policy_rate(mes)`
        Fórmula: SUMPRODUCT(tasa × atribución) para pólizas con mes_desde ≤ mes.

        Args:
            mes: Mes del contrato.

        Returns:
            Tasa efectiva como decimal.

        Raises:
            ParametrizationError: si OP-Poliza no existe.
        """
        value = self._financial.get_effective_policy_rate(mes)
        logger.debug(
            "[REPOSITORY] repository=FinancialParametrizationRepository "
            "operation=get_tasa_polizas_efectiva mes=%d value=%s source=OP-Poliza",
            mes, value,
        )
        return value


    def get_factor_periodo(self, dias: int) -> int:
        """
        Factor de período de pago: convierte días de crédito en meses.

        Implementación: lógica pura `max(1, dias // 30)`.
        Si el negocio requiere sobreescribir estos factores (ej. 45 días → 2),
        agregar tabla a OP Excel y leer desde `FinancialParametrizationRepository`.

        Args:
            dias: Días de crédito (30, 60, 90, 120).

        Returns:
            Número de meses equivalentes (mínimo 1).
        """
        factor = max(1, dias // 30)
        logger.debug(
            "[REPOSITORY] operation=get_factor_periodo "
            "dias=%d factor=%d source=pure_math",
            dias, factor,
        )
        return factor


    def get_margen_minimo(self, linea_negocio: str) -> float:
        """
        Margen mínimo requerido para una línea de negocio.

        Fuente: HR-Rentabilidad → `get_min_margin(linea_negocio)`
        Formato: decimal (0.17 = 17%).

        Args:
            linea_negocio: Línea de negocio.

        Returns:
            Margen mínimo como decimal.

        Raises:
            ParametrizationError: si la línea no existe.
        """
        canon = canonical_service(linea_negocio)
        try:
            value = self._profitability.get_min_margin(canon)
        except ParametrizationError:
            if canon != linea_negocio:
                value = self._profitability.get_min_margin(linea_negocio)
            else:
                raise
        logger.debug(
            "[REPOSITORY] repository=ProfitabilityParametrizationRepository "
            "operation=get_margen_minimo linea=%s canon=%s value=%s source=HR-Rentabilidad",
            linea_negocio, canon, value,
        )
        return value

    # ──────────────────────────────────────────────────────────────────────────
    # Financiero
    # ──────────────────────────────────────────────────────────────────────────


    def get_gmf(self) -> float:
        """GMF (Gravamen a los Movimientos Financieros). Fuente: OP-Poliza.

        Raises:
            ParametrizationError: si no existe fila GMF/Gravamen en OP-Poliza.
        """
        value = self._financial.get_gmf()
        logger.debug(
            "[REPOSITORY] repository=FinancialParametrizationRepository "
            "operation=get_gmf value=%s source=OP-Poliza",
            value,
        )
        return value


    def get_ica(self, ciudad: str) -> float:
        """Tasa ICA para una ciudad. Fuente: OP-ICA.

        Args:
            ciudad: Nombre de la ciudad.

        Raises:
            ParametrizationError: si la ciudad no existe en OP-ICA.
        """
        value = self._financial.get_ica(ciudad)
        logger.debug(
            "[REPOSITORY] repository=FinancialParametrizationRepository "
            "operation=get_ica ciudad=%s value=%s source=OP-ICA",
            ciudad, value,
        )
        return value

    # Mapeo de nombres canónicos usados en el código → nombres exactos en el Excel OP
    _COMPONENTE_ALIAS: dict = {
        # Códigos canónicos del código → nombres del Excel/OP (con " - ")
        "70SMMLV_30IPC": "70% SMMLV - 30% IPC",
        "80SMMLV_20IPC": "80% SMMLV - 20% IPC",
        "IPC_mas_1pt":   "IPC + 1 PUNTO",
        "IPC_neg_AVAL":  "IPC, previa negociación con AVAL",
        # GAP-INDEXACION (fix): formas Excel-espaciadas (sin " - ") que llegan del Panel
        # directamente vía context_builder — el storage las almacena con " - ".
        # Excel: Panel!L6/L7/L8 exportan sin guión; storage normaliza a " - " para todos.
        "80% SMMLV 20% IPC": "80% SMMLV - 20% IPC",
        "70% SMMLV 30% IPC": "70% SMMLV - 30% IPC",
        "20% SMMLV 80% IPC": "20% SMMLV - 80% IPC",
        # los demás coinciden exactamente con el Excel
    }


    def get_factor_indexacion(self, componente: str, anio: int) -> float:
        """
        Factor de indexación acumulado para un componente y año.

        Fuente primaria: OP-ComponenteAcumulado
        Fuente alternativa: compounding desde OP-Componente (año base desde OP-Config)

        Soporta tanto los nombres canónicos del código (ej. '70SMMLV_30IPC')
        como los nombres literales del Excel OP (ej. '70% SMMLV - 30% IPC').

        Args:
            componente: Nombre del componente (ej. "IPC", "SMLV", "70SMMLV_30IPC").
            anio:       Año del contrato.

        Returns:
            Factor acumulado (base año_base=1.0).

        Raises:
            ParametrizationError: si el componente/año no se encuentran en ninguna fuente.
        """
        self._financial._ensure_op_loaded()
        acum_sheet = self._financial._get_sheet(self._financial._op_data, "componenteacumulado")

        # Resolver alias: código → nombre exacto en Excel
        componente_excel = self._COMPONENTE_ALIAS.get(componente, componente)

        if acum_sheet and "rows" in acum_sheet:
            for row in acum_sheet["rows"]:
                if (row.get("componente") == componente_excel and
                        int(float(row.get("ano", 0))) == anio):
                    valor = row.get("valor")
                    if valor is not None:
                        v = float(valor)
                        logger.debug(
                            "[RESOLUTION] component=%s year=%d "
                            "source=OP-ComponenteAcumulado value=%s",
                            componente, anio, v,
                        )
                        return v

        # Fallback: acumular desde tasas anuales (año base desde OP-Config)
        try:
            anio_base    = int(self._financial.get_op_config("anio_base_indexacion"))
            annual_rate  = self._financial.get_economic_component(componente_excel, anio)
            base = 1.0
            for y in range(anio_base, anio):
                base *= (1 + self._financial.get_economic_component(componente_excel, y))
            base *= (1 + annual_rate)
            logger.debug(
                "[RESOLUTION] component=%s year=%d source=OP-Componente_compounded "
                "anio_base=%d value=%s", componente, anio, anio_base, base,
            )
            return base
        except Exception as exc:
            raise ParametrizationError(
                f"Factor de indexación '{componente}' año {anio} no encontrado en OP. "
                f"Verifique OP-ComponenteAcumulado y OP-Config(anio_base_indexacion). "
                f"Detalle: {exc}",
                module="op",
            ) from exc


    def get_componente_indexacion(self, componente: str, anio: int) -> float:
        """
        Tasa anual de crecimiento de un componente económico.

        Fuente: OP-Componente (tasa anual por componente/año).

        Soporta tanto los nombres canónicos del código (ej. '70SMMLV_30IPC')
        como los nombres literales del Excel OP (ej. '70% SMMLV - 30% IPC').

        Args:
            componente: Nombre del componente (ej. "IPC", "SMLV", "70SMMLV_30IPC").
            anio:       Año del contrato.

        Returns:
            Tasa anual de crecimiento (ej. 0.04 para 4% anual).

        Raises:
            ParametrizationError: si el componente/año no se encuentran.
        """
        componente_excel = self._COMPONENTE_ALIAS.get(componente, componente)
        valor = self._financial.get_economic_component(componente_excel, anio)
        logger.debug(
            "[RESOLUTION] parameter=componente_indexacion "
            "component=%s year=%d source=OP-Componente value=%s",
            componente, anio, valor,
        )
        return valor

    # ──────────────────────────────────────────────────────────────────────────
    # Nómina y costos laborales
    # ──────────────────────────────────────────────────────────────────────────


    def get_tipo_carga_rol(self, rol: str) -> str:
        """Tipo de carga laboral formal para un rol.

        Fuente: HR-rol_a_tipo_carga (catálogo explícito en storage).

        Tipos válidos:
            - EMPLEADO_ESTANDAR        (Ley 1819 estándar)
            - APRENDIZ_SENA            (Ley 789)
            - EQUIPO_SOPORTE_MANTENIMIENTO  (Cadena B SM)
            - SOPORTE_COMISIONABLE     (Director cuentas, GTR)
            - IMPLEMENTACION_PROYECTOS (Especialista de Proyectos)

        Returns:
            Código del tipo, o "EMPLEADO_ESTANDAR" si el rol no está catalogado.
        """
        self._payroll._ensure_hr_loaded()
        mapping = self._payroll._hr_data.get("rol_a_tipo_carga", {})
        # Try exact match, then stripped, then case-insensitive
        if rol in mapping:
            return mapping[rol]
        rol_norm = rol.strip()
        if rol_norm in mapping:
            return mapping[rol_norm]
        rol_low = rol_norm.lower()
        for k, v in mapping.items():
            if str(k).strip().lower() == rol_low:
                return v
        return "EMPLEADO_ESTANDAR"


    def get_tipos_carga_catalog(self) -> list:
        """Devuelve el catálogo completo de tipos_carga (HR-tipos_carga)."""
        self._payroll._ensure_hr_loaded()
        return self._payroll._hr_data.get("tipos_carga", [])


    def get_costo_empresa_override(self, rol: str) -> Optional[float]:
        """
        WAVE 3 (W3-4): override del costo cargado de empresa para roles especiales.

        Algunos roles (notablemente "Director de cuentas" en Excel V2-7) tienen un
        ``costo_empresa_override`` declarado en HR-Nomina que reemplaza el cálculo
        estándar de nómina cargada. Si está presente, debe usarse tal cual,
        sin re-aplicar la fórmula de carga social.

        Fuente: HR-Nomina col "costo_empresa_override" (V2-7).

        Args:
            rol: Nombre del rol.

        Returns:
            Valor del override (float positivo) si está declarado y es > 0,
            o None si el rol no tiene override (caso normal: usar fórmula estándar).
        """
        self._payroll._ensure_hr_loaded()
        nomina = self._payroll._hr_data.get("nomina", [])
        rol_norm = rol.strip().lower()
        for row in nomina:
            row_rol = str(row.get("rol", "")).strip().lower()
            if row_rol == rol_norm:
                raw = row.get("costo_empresa_override")
                if raw is None:
                    return None
                try:
                    val = float(raw)
                except (TypeError, ValueError):
                    return None
                if val > 0:
                    logger.debug(
                        "[REPOSITORY] operation=get_costo_empresa_override rol=%s value=%s "
                        "source=HR-Nomina(V2-7)",
                        rol, val,
                    )
                    return val
                return None
        return None


    def get_costo_no_payroll(self, sede: str) -> dict:
        """Costos de infraestructura por estación para una sede.

        Fuente: HR-CostoFijo.

        Args:
            sede: Nombre de la sede/localidad.

        Returns:
            Dict con keys: arriendo, energia, agua, gas, aseo, vigilancia, mantenimiento.

        Raises:
            ParametrizationError: si la sede no existe en HR-CostoFijo.
        """
        costos = self._infrastructure.get_infrastructure_costs(sede)
        logger.debug(
            "[REPOSITORY] repository=InfrastructureParametrizationRepository "
            "operation=get_costo_no_payroll sede=%s source=HR-CostoFijo",
            sede,
        )
        return costos


    def get_costo_operativo(self, clave: str) -> float:
        """Retorna un costo/parámetro operativo por su clave.

        Fuente: HR-costos_operativos.

        Claves disponibles:
            tarifa_dia_cap, opex_ti_por_estacion,
            capex_recurrente_por_estacion, capex_inicial_por_estacion,
            pct_aumento_tecnologico_anual, mes_inicio_ajuste_anual.

        Args:
            clave: Clave del parámetro.

        Returns:
            Valor como float.

        Raises:
            ParametrizationError: si la sección o clave no existe en HR.
        """
        value = self._payroll.get_costo_operativo(clave)
        logger.debug(
            "[REPOSITORY] repository=PayrollParametrizationRepository "
            "operation=get_costo_operativo clave=%s value=%s source=HR-costos_operativos",
            clave, value,
        )
        return value

    # ──────────────────────────────────────────────────────────────────────────
    # Reglas y ratios de staff  (HR-reglas_staff, HR-Ratios)
    # ──────────────────────────────────────────────────────────────────────────


    def get_v27_defaults(self) -> Dict[str, Any]:
        """Return the ``v2_7_defaults`` block from OP parametrization.

        Fuente: storage/parametrization/op/<active>.json → ``v2_7_defaults``.
        Estructura (resumida)::

            {
              "margenes": {
                  "margen_a_default": 0.21,
                  "margen_b_default": 0.30,
                  "margen_c_default": 0.20,
                  ...
              },
              "indexacion": {
                  "mes_ajuste": 6,
                  "tasa_interes_mensual": 0.0153,
                  ...
              },
              "imprevistos_default": 0.0,
              ...
            }

        Returns:
            Dict con los defaults, o ``{}`` si la versión activa no los expone
            (compatibilidad hacia atrás con parametrizaciones pre-V2-7).
        """
        self._financial._ensure_op_loaded()
        defaults = self._financial._op_data.get("v2_7_defaults", {}) if self._financial._op_data else {}
        if not defaults:
            logger.debug("[PARAMETRIZATION] op.v2_7_defaults no presente en la versión activa")
        return defaults

    # ──────────────────────────────────────────────────────────────────────────
    # Business rules & risk config (canonical YAML)
    # ──────────────────────────────────────────────────────────────────────────



__all__ = ["ProviderFinOpMixin"]
