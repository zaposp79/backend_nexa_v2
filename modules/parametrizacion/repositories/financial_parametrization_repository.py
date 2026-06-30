"""Financial parametrization repository.

Extracts financial parameters from GN and OP parametrization modules:
- ICA rates by city
- GMF rates
- Financing rates
- Insurance policy rates
- Economic components (IPC, SMLV indices)

Data sources:
- GN: Financial catalogs and rates (currently empty)
- OP: ICA by city, Components (IPC, etc.), Polizas
"""

from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, List, Optional

from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.shared.exceptions import (
    DomainError,
    ParametrizationError,
    ParametrizationNotFoundError,
)

logger = logging.getLogger(__name__)


class FinancialParametrizationRepository:
    """Repository for financial parameters from parametrization.

    Access patterns:
    - get_ica(ciudad: str) → float: ICA tax rate for a city
    - get_gmf() → float: GMF financial transaction tax
    - get_tasa_financiacion() → float: Monthly financing rate
    - get_insurance_policies() → Dict: All insurance policy rates
    - get_economic_component(componente: str, ano: int) → float: Index value for year
    """

    def __init__(self, resolver: ParametrizationResolver):
        """Initialize repository with resolver.

        Args:
            resolver: ParametrizationResolver instance for loading active versions.
        """
        self._resolver = resolver
        self._op_data: Optional[Dict[str, Any]] = None
        self._gn_data: Optional[Dict[str, Any]] = None

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def get_ica(self, ciudad: str) -> float:
        """Get ICA (tax) rate for a city.

        ICA is extracted from OP-ICA sheet, "Tasa" category.

        Args:
            ciudad: City name (case-insensitive).

        Returns:
            ICA rate as decimal (e.g., 0.0197 for 1.97%).

        Raises:
            ParametrizationError: if city not found or rate invalid.
        """
        self._ensure_op_loaded()

        ciudad_normalized = self._normalize_city(ciudad)
        ica_sheet = self._get_sheet(self._op_data, "ica")

        if not ica_sheet or "rows" not in ica_sheet:
            raise ParametrizationError(
                f"OP-ICA sheet not found or invalid structure",
                module="op"
            )

        # Find "Tasa" / "Tarifa" category for this city (v2-6 used "Tasa", v2-7 uses "Tarifa")
        for row in ica_sheet["rows"]:
            if (self._normalize_city(row.get("ciudad", "")) == ciudad_normalized and
                row.get("ica") in ("Tasa", "Tarifa")):
                valor = row.get("valor")
                if valor is None:
                    raise ParametrizationError(
                        f"ICA rate missing for {ciudad}",
                        module="op"
                    )
                # Valor is sometimes stored as percentage (60 = 0.6%)
                # or as decimal (0.006 = 0.6%)
                # We assume parametrization uses percentage format and convert
                rate = float(valor)
                if rate > 1:
                    # Likely percentage (60 = 0.6%), convert to decimal
                    rate = rate / 100
                return rate

        raise ParametrizationError(
            f"ICA rate not found for city '{ciudad}' in OP-ICA sheet",
            module="op"
        )

    def get_gmf(self) -> float:
        """Get GMF (financial transaction tax) rate.

        Supports two OP schemas:
        - Legacy: OP-Poliza row with 'GMF'/'Gravamen' in poliza + valor field
        - New productiva: OP-PolizaFija row with 'GMF'/'Gravamen' + porcentaje field
          (porcentaje is raw %, e.g. 0.4 → 0.004 decimal)

        Raises:
            ParametrizationError: if GMF not found in either sheet.
        """
        self._ensure_op_loaded()

        # Legacy schema: OP-Poliza with valor field
        polizas_sheet = self._get_sheet(self._op_data, "poliza")
        if polizas_sheet and "rows" in polizas_sheet:
            for row in polizas_sheet["rows"]:
                nombre = row.get("poliza", "")
                if "gmf" in nombre.lower() or "gravamen" in nombre.lower():
                    val = row.get("valor")
                    if val is not None:
                        v = float(val)
                        logger.info(
                            "[PARAM_SOURCE] parameter=gmf source=OP-Poliza poliza='%s' value=%s",
                            nombre, v,
                        )
                        return v

        # New productiva schema: OP-PolizaFija with porcentaje field (raw %)
        polizafija_sheet = self._get_sheet(self._op_data, "polizafija")
        if polizafija_sheet and "rows" in polizafija_sheet:
            for row in polizafija_sheet["rows"]:
                nombre = row.get("poliza", "")
                if "gmf" in nombre.lower() or "gravamen" in nombre.lower():
                    pct = row.get("porcentaje")
                    if pct is not None:
                        v = float(pct) / 100.0
                        logger.info(
                            "[PARAM_SOURCE] parameter=gmf source=OP-PolizaFija poliza='%s' value=%s",
                            nombre, v,
                        )
                        return v

        raise ParametrizationError(
            "GMF rate not found in OP-Poliza or OP-PolizaFija. "
            "Add a row with 'GMF' or 'Gravamen' in the poliza column.",
            module="op",
        )

    _TASA_FINANCIACION_DEFAULT: float = 0.0088

    def get_tasa_financiacion(self) -> float:
        """Get monthly financing rate.

        Fuente: OP-Config sheet, clave='tasa_financiacion_mensual'.
        Fallback: 0.0088 (0.88%) when OP-Config sheet is absent (new productiva schema).

        Returns:
            Rate as decimal (e.g., 0.0088 for 0.88%).
        """
        self._ensure_op_loaded()
        config_sheet = self._get_sheet(self._op_data, "config")
        if config_sheet and "rows" in config_sheet:
            for row in config_sheet["rows"]:
                if row.get("clave") == "tasa_financiacion_mensual":
                    val = row.get("valor")
                    if val is not None:
                        v = float(val)
                        logger.info(
                            "[PARAM_SOURCE] parameter=tasa_financiacion source=OP-Config value=%s", v,
                        )
                        return v
        logger.warning(
            "[PARAM_SOURCE] parameter=tasa_financiacion source=OP-Config NOT FOUND "
            "— using default=%s (OP-Config sheet absent in active parametrization)",
            self._TASA_FINANCIACION_DEFAULT,
        )
        return self._TASA_FINANCIACION_DEFAULT

    def get_op_config(self, clave: str) -> float:
        """Get a scalar configuration value from OP-Config sheet.

        Args:
            clave: Configuration key (e.g., 'anio_base_indexacion',
                   'factor_alto_salario_smmlv', 'factor_corrector_alto_salario').

        Returns:
            Value as float.

        Raises:
            ParametrizationError: if key not found.
        """
        self._ensure_op_loaded()
        config_sheet = self._get_sheet(self._op_data, "config")
        if config_sheet and "rows" in config_sheet:
            for row in config_sheet["rows"]:
                if row.get("clave") == clave:
                    val = row.get("valor")
                    if val is not None:
                        v = float(val)
                        logger.info(
                            "[PARAM_SOURCE] parameter=%s source=OP-Config value=%s", clave, v,
                        )
                        return v
        raise ParametrizationError(
            f"OP-Config key '{clave}' not found. Available keys: "
            f"{[r.get('clave') for r in (config_sheet or {}).get('rows', [])]}",
            module="op",
        )

    def get_effective_policy_rate(self, mes: int) -> float:
        """Compute effective insurance policy rate for a given month.

        Formula: SUMPRODUCT(tasa × atribución) for policies where
        aplica=True AND mes_desde ≤ mes.

        Fuente completa: OP-Poliza (tasa, atribucion, mes_desde, aplica).
        No hay diccionarios hardcodeados en código.

        Args:
            mes: Contract month number (1-based).

        Returns:
            Effective rate as decimal (typically 0.01..0.03).

        Raises:
            ParametrizationError: if OP-Poliza sheet missing.
        """
        self._ensure_op_loaded()
        polizas_sheet = self._get_sheet(self._op_data, "poliza")
        if not polizas_sheet or "rows" not in polizas_sheet:
            raise ParametrizationError(
                "OP-Poliza sheet not found. Cannot compute effective policy rate.",
                module="op",
            )

        total = 0.0
        for row in polizas_sheet["rows"]:
            # New productiva schema: porcentaje (raw %) + porcentajeexigido (required coverage %)
            # Effective contribution = (porcentaje/100) * (porcentajeexigido/100)
            if "porcentaje" in row and "porcentajeexigido" in row:
                pct = float(row.get("porcentaje", 0) or 0) / 100.0
                exigido = float(row.get("porcentajeexigido", 0) or 0) / 100.0
                contribucion = pct * exigido
                total += contribucion
                logger.debug(
                    "[PARAM_SOURCE] poliza='%s' pct=%s exigido=%s contribucion=%s (new schema)",
                    row.get("poliza"), pct, exigido, contribucion,
                )
                continue

            # Legacy schema: aplica, mes_desde, valor, atribucion
            aplica = row.get("aplica", row.get("Aplica", False))
            if not aplica:
                continue
            mes_desde = int(row.get("mes_desde", row.get("mesdesde", row.get("MesDesde", 1))))
            if mes_desde > mes:
                continue
            tasa       = float(row.get("valor", row.get("Valor", 0)) or 0)
            atribucion = float(row.get("atribucion", row.get("Atribucion", 0)) or 0)
            total += tasa * atribucion
            logger.debug(
                "[PARAM_SOURCE] poliza='%s' tasa=%s atribucion=%s contribucion=%s",
                row.get("poliza"), tasa, atribucion, tasa * atribucion,
            )

        logger.info(
            "[PARAM_SOURCE] parameter=effective_policy_rate mes=%d source=OP-Poliza value=%s",
            mes, total,
        )
        return total

    def get_insurance_policies(self) -> Dict[str, Any]:
        """Get all insurance policy rates and attributes.

        Returns:
            Dict mapping policy name to {tasa, atribución}.

        Raises:
            ParametrizationError: if polizas sheet invalid.
        """
        self._ensure_op_loaded()

        polizas_sheet = self._get_sheet(self._op_data, "poliza")

        if not polizas_sheet or "rows" not in polizas_sheet:
            logger.warning("OP-Poliza sheet not found, returning empty policies")
            return {}

        policies = {}
        for row in polizas_sheet["rows"]:
            nombre = row.get("poliza")
            if nombre:
                policies[nombre] = {
                    "tasa": float(row.get("valor", 0)),
                    "atribución": float(row.get("atribución", 0)),
                }

        return policies

    def get_economic_component(self, componente: str, ano: int) -> float:
        """Get economic component value for a specific year.

        Args:
            componente: Component name (e.g., "IPC", "SMLV", "70SMMLV_30IPC").
            ano: Year (e.g., 2025, 2026).

        Returns:
            Component value (usually an index like 1.0, 1.05).

        Raises:
            ParametrizationError: if component not found.
        """
        self._ensure_op_loaded()

        componente_sheet = self._get_sheet(self._op_data, "componente")

        if not componente_sheet or "rows" not in componente_sheet:
            raise ParametrizationError(
                f"OP-Componente sheet not found",
                module="op"
            )

        # Find matching component and year
        for row in componente_sheet["rows"]:
            if (row.get("componente") == componente and
                int(float(row.get("ano", 0))) == ano):
                valor = row.get("valor")
                if valor is not None:
                    return float(valor)

        raise ParametrizationError(
            f"Economic component '{componente}' for year {ano} not found",
            module="op"
        )

    # -----------------------------------------------------------------------
    # OP-Costo fallbacks (new productiva schema — global rotation/absence)
    # -----------------------------------------------------------------------

    def get_global_pct_rotacion(self) -> Optional[float]:
        """Global rotation % from OP-Costo sheet (new productiva schema).

        New OP parametrization stores a single global rotation rate under
        'Porcentaje de Rotación' in the costo sheet (raw %, e.g. 9.0 → 0.09).

        Returns:
            Decimal rate or None if not available.
        """
        self._ensure_op_loaded()
        costo_sheet = self._get_sheet(self._op_data, "costo")
        if costo_sheet and "rows" in costo_sheet:
            for row in costo_sheet["rows"]:
                label = (row.get("costooperativo") or "").lower()
                if "rotaci" in label:
                    val = row.get("valor")
                    if val is not None:
                        v = float(val) / 100.0
                        logger.info(
                            "[PARAM_SOURCE] parameter=pct_rotacion source=OP-Costo value=%s", v,
                        )
                        return v
        return None

    def get_global_pct_ausentismo(self) -> Optional[float]:
        """Global ausentismo % from OP-Costo sheet (new productiva schema).

        Returns:
            Decimal rate or None if not available.
        """
        self._ensure_op_loaded()
        costo_sheet = self._get_sheet(self._op_data, "costo")
        if costo_sheet and "rows" in costo_sheet:
            for row in costo_sheet["rows"]:
                label = (row.get("costooperativo") or "").lower()
                if "ausentismo" in label:
                    val = row.get("valor")
                    if val is not None:
                        v = float(val) / 100.0
                        logger.info(
                            "[PARAM_SOURCE] parameter=pct_ausentismo source=OP-Costo value=%s", v,
                        )
                        return v
        return None

    def get_global_pct_examen_anual(self) -> float:
        """Global pct_examen_anual when HR-AutRot is absent.

        Returns 1.0 (100% agents pass annual exam — canonical default from v2-7).
        """
        return 1.0

    def get_portfolio_margen_bruto_rows(self) -> List[Dict[str, Any]]:
        """Return normalized rows from OP-MargenBruto sheet.

        Excel V2-8 · OP-MargenBruto — sheet key: "margenbruto"
        Row fields input: {servicio, cliente, margenbruto}
        Row fields output: {categoria: str, cliente: str, margen_bruto: float}
        Returns [] when sheet is missing (OP_CONTRACT_GAP).
        """
        try:
            self._ensure_op_loaded()
        except Exception:
            return []

        sheet = self._get_sheet(self._op_data, "margenbruto")
        if not sheet or "rows" not in sheet:
            logger.warning(
                "[PARAM_SOURCE] get_portfolio_margen_bruto_rows: OP_CONTRACT_GAP — margenbruto sheet missing"
            )
            return []

        result = []
        for row in sheet["rows"]:
            categoria = row.get("servicio", "")
            cliente = row.get("cliente", "")
            margen = row.get("margenbruto")
            if margen is None or not isinstance(margen, (int, float)):
                continue
            result.append({
                "categoria": str(categoria),
                "cliente": str(cliente),
                "margen_bruto": float(margen),
            })
        return result

    def get_grafico_margen_bruto_rows(self) -> List[Dict[str, Any]]:
        """Return normalized rows from OP-GraficoMargenBruto sheet.

        Excel V2-8 · OP-GraficoMargenBruto — sheet key: "graficomargenbruto"
        Row fields input: {servicios, margenbruto}
        Row fields output: {servicios: str, margen_bruto: float}
        Returns [] when sheet is missing.
        """
        try:
            self._ensure_op_loaded()
        except Exception:
            return []

        sheet = self._get_sheet(self._op_data, "graficomargenbruto")
        if not sheet or "rows" not in sheet:
            logger.warning(
                "[PARAM_SOURCE] get_grafico_margen_bruto_rows: graficomargenbruto sheet missing"
            )
            return []

        result = []
        for row in sheet["rows"]:
            servicios = row.get("servicios", "")
            margen = row.get("margenbruto")
            if margen is None or not isinstance(margen, (int, float)):
                continue
            result.append({
                "servicios": str(servicios),
                "margen_bruto": float(margen),
            })
        return result

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _ensure_op_loaded(self) -> None:
        """Load OP parametrization if not already loaded."""
        if self._op_data is None:
            try:
                self._op_data = self._resolver.get_active_op()
            except ParametrizationNotFoundError as e:
                raise ParametrizationError(
                    f"Cannot load financial parameters: OP parametrization not found",
                    module="op"
                ) from e

    def _ensure_gn_loaded(self) -> None:
        """Load GN parametrization if not already loaded."""
        if self._gn_data is None:
            try:
                self._gn_data = self._resolver.get_active_gn()
            except ParametrizationNotFoundError:
                logger.warning("GN parametrization not found, will skip GN-based rates")
                self._gn_data = {}

    def _get_sheet(self, data: Optional[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
        """Extract sheet from parametrization data by key.

        Args:
            data: Parametrization data dict.
            key: Sheet key (e.g., 'ica', 'componente', 'lv').

        Returns:
            Sheet dict or None if not found.
        """
        if not data:
            return None

        # For sheets array
        sheets = data.get("sheets", [])
        for sheet in sheets:
            if sheet.get("key") == key:
                return sheet

        # For lv field (HR-style)
        if key == "lv" and "lv" in data:
            return data["lv"]

        return None

    @staticmethod
    def _normalize_city(name: str) -> str:
        """Normaliza nombre de ciudad: elimina acentos, minúsculas, strip.

        Garantiza que 'Bogotá' y 'Bogota', 'Medellín' y 'Medellin',
        etc., se resuelvan al mismo lookup sin error.

        Ejemplos:
            'Bogotá'   → 'bogota'
            'Bogota'   → 'bogota'
            'Medellín' → 'medellin'
            'Cúcuta'   → 'cucuta'
        """
        if not isinstance(name, str):
            name = str(name) if name is not None else ""
        nfkd = unicodedata.normalize("NFKD", name)
        return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()
