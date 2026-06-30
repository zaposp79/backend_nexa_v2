"""Maps raw Excel row dicts to HR domain models."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from nexa_engine.modules.parametrizacion.hr.models.models import (
    CampanaConfig,
    CostoFijoConfig,
    HRMasterData,
    MedSegConfig,
    NivelesLV,
    NominaConfig,
    PrestacionesConfig,
    RatiosConfig,
    RentabilidadConfig,
    RecargosConfig,
    SalarioBasico,
    SegSocialConfig,
)

logger = logging.getLogger("nexa.parametrization.hr")


def _float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return round(float(val), 5)
    except (ValueError, TypeError):
        return default


def _int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val).strip()


class HRMapper:
    """Converts raw sheet row-dicts to :class:`HRMasterData`."""

    def map(self, version_id: str, sheets: Dict[str, List[dict]]) -> HRMasterData:
        # Standard HR sheets (typed, specific mappers)
        STANDARD_SHEETS = {
            "HR-LV", "HR-SalarioBasico", "HR-Nomina", "HR-Recargos",
            "HR-SegSocial", "HR-Prestaciones", "HR-Ratios", "HR-Rentabilidad",
            "HR-Campana", "HR-CostoFijo", "HR-Med-Seg"
        }

        # Capture any additional sheets not in the standard list
        extra_sheets = {
            sheet_name: rows
            for sheet_name, rows in sheets.items()
            if sheet_name not in STANDARD_SHEETS and rows
        }

        if extra_sheets:
            logger.info(
                "[MAPPER] Extra sheets detected (not in standard HR spec): %s",
                list(extra_sheets.keys())
            )

        return HRMasterData(
            version_id=version_id,
            niveles=self._map_niveles(sheets.get("HR-LV", [])),
            salarios=self._map_salarios(sheets.get("HR-SalarioBasico", [])),
            nomina=self._map_nomina(sheets.get("HR-Nomina", [])),
            recargos=self._map_recargos(sheets.get("HR-Recargos", [])),
            seg_social=self._map_seg_social(sheets.get("HR-SegSocial", [])),
            prestaciones=self._map_prestaciones(sheets.get("HR-Prestaciones", [])),
            ratios=self._map_ratios(sheets.get("HR-Ratios", [])),
            rentabilidad=self._map_rentabilidad(sheets.get("HR-Rentabilidad", [])),
            campana=self._map_campana(sheets.get("HR-Campana", [])),
            costo_fijo=self._map_costo_fijo(sheets.get("HR-CostoFijo", [])),
            med_seg=self._map_med_seg(sheets.get("HR-Med-Seg", [])),
            extra_sheets=extra_sheets,
        )

    def _map_niveles(self, rows: List[dict]) -> NivelesLV:
        if not rows:
            return NivelesLV()
        seen: dict = {col: {} for col in rows[0].keys()}
        for row in rows:
            for col, val in row.items():
                v = _str(val)
                if v and v not in seen[col]:
                    seen[col][v] = {"name": v}
        catalogs = {col: list(vals.values()) for col, vals in seen.items() if vals}
        return NivelesLV(catalogs=catalogs)

    def _map_salarios(self, rows: List[dict]) -> List[SalarioBasico]:
        result = []
        for row in rows:
            result.append(SalarioBasico(
                servicio=_str(row.get("servicio")),
                valor=_float(row.get("valor")),
            ))
        return result

    def _map_nomina(self, rows: List[dict]) -> List[NominaConfig]:
        result = []
        for row in rows:
            result.append(NominaConfig(
                tipo=_str(row.get("tipo")),
                rol=_str(row.get("rol")),
                salario=_float(row.get("salario")),
            ))
        return result

    def _map_recargos(self, rows: List[dict]) -> List[RecargosConfig]:
        result = []
        for row in rows:
            result.append(RecargosConfig(
                recargo=_str(row.get("recargo")),
                valor=_float(row.get("valor")),
            ))
        return result

    def _map_seg_social(self, rows: List[dict]) -> List[SegSocialConfig]:
        result = []
        for row in rows:
            result.append(SegSocialConfig(
                ssparafiscales=_str(row.get("ssparafiscales")),
                proporcion=_float(row.get("proporcion")),
            ))
        return result

    def _map_prestaciones(self, rows: List[dict]) -> List[PrestacionesConfig]:
        result = []
        for row in rows:
            result.append(PrestacionesConfig(
                prestaciones=_str(row.get("prestaciones")),
                valor=_float(row.get("valor")),
            ))
        return result

    def _map_ratios(self, rows: List[dict]) -> List[RatiosConfig]:
        result = []

        # Log column names from first row to debug mapping issues
        if rows:
            col_names = list(rows[0].keys())
            logger.warning(
                "[MAPPING] HR-Ratios sheet columns: %s",
                col_names
            )

        for idx, row in enumerate(rows, start=1):
            cargo = _str(row.get("cargo")) or _str(row.get("Cargo"))
            if not cargo:
                continue

            # Try multiple variations of column names (case-insensitive approach)
            # Look for each field with various possible Excel column names
            categoria_servicio = (
                _str(row.get("CategoriaServicio")) or
                _str(row.get("categoriaservicio")) or
                _str(row.get("categoria_servicio")) or
                _str(row.get("Categoria Servicio")) or
                _str(row.get("categoria servicio")) or
                _str(row.get("servicio")) or
                _str(row.get("Servicio"))
            )

            tipo = (
                _str(row.get("Tipo")) or
                _str(row.get("tipo")) or
                _str(row.get("TIPO"))
            )

            agentes = _float(
                row.get("Agentes") or
                row.get("agentes") or
                row.get("AGENTES")
            )

            # Log all rows to see actual values
            logger.info(
                "[MAPPING] HR-Ratios row %d: cargo=%r, categoria_servicio=%r, tipo=%r, agentes=%s | raw_keys=%s",
                idx, cargo, categoria_servicio, tipo, agentes,
                list(row.keys())
            )

            result.append(RatiosConfig(
                cargo=cargo,
                servicio=categoria_servicio,  # Primary field for backward compatibility
                agentes=agentes,
                tipo=tipo,
                categoria_servicio=categoria_servicio,
            ))
        return result

    def _map_rentabilidad(self, rows: List[dict]) -> List[RentabilidadConfig]:
        # minimo / margenobjetivo arrive as float (0.17) after contract normalization
        result = []
        for row in rows:
            result.append(RentabilidadConfig(
                categoriaservicio=_str(row.get("categoriaservicio")),
                minimo=_float(row.get("minimo")),
                margenobjetivo=_float(row.get("margenobjetivo")),
            ))
        return result

    def _map_campana(self, rows: List[dict]) -> List[CampanaConfig]:
        result = []
        for row in rows:
            result.append(CampanaConfig(
                categoriaservicio=_str(row.get("categoriaservicio")),
                mes=_int(row.get("mes")),
                valor=_float(row.get("valor")),
            ))
        return result

    def _map_costo_fijo(self, rows: List[dict]) -> List[CostoFijoConfig]:
        result = []
        for row in rows:
            # CRITICAL: Keep localidad EXACTLY as-is from Excel (no truncation)
            localidad = _str(row.get("localidad")).strip()
            servicio = _str(row.get("servicio")).strip()

            # CRITICAL: Convert valor to float WITHOUT division or rounding
            # If Excel has 153301, store as 153301.0 (not 153.301)
            valor_raw = row.get("valor")
            if valor_raw is None:
                valor = 0.0
            else:
                try:
                    # Convert directly without _float() which rounds to 5 decimals
                    valor = float(valor_raw)
                except (ValueError, TypeError):
                    valor = 0.0

            result.append(CostoFijoConfig(
                localidad=localidad,
                servicio=servicio,
                valor=valor,
            ))
        return result

    def _map_med_seg(self, rows: List[dict]) -> List[MedSegConfig]:
        result = []
        for row in rows:
            # CRITICAL: Keep localidad EXACTLY as-is from Excel (no truncation)
            localidad = _str(row.get("localidad")).strip()
            centrocosto = _str(row.get("centrocosto")).strip()

            # CRITICAL: Convert valor to float WITHOUT division or transformation
            valor_raw = row.get("valor")
            if valor_raw is None:
                valor = 0.0
            else:
                try:
                    valor = float(valor_raw)
                except (ValueError, TypeError):
                    valor = 0.0

            result.append(MedSegConfig(
                localidad=localidad,
                centrocosto=centrocosto,
                valor=valor,
            ))
        return result

    def to_dict(self, master: HRMasterData) -> dict:
        import dataclasses
        return dataclasses.asdict(master)
