"""Rotacion, ausentismo and cache loader methods.

Mixin for PayrollParametrizationRepository — FASE Z.2.
"""
from __future__ import annotations
import logging
import re
import collections
from typing import Any, Dict, Optional
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
from nexa_engine.modules.shared.exceptions import ParametrizationError, ParametrizationNotFoundError, DomainError
logger = logging.getLogger(__name__)


class PayrollRotacionMixin:
    """Mixin: Rotacion, ausentismo and cache loader methods."""

    def get_pct_rotacion(self, linea: str) -> float:
        """Porcentaje de rotación mensual para una línea de negocio.

        Fuente: HR-rotacion_ausentismo (sección agregada en storage JSON).

        Args:
            linea: Línea de negocio (ej. 'Cobranzas', 'SAC').

        Returns:
            Tasa mensual como decimal (ej. 0.1199 = 11.99%).

        Raises:
            ParametrizationError: si la sección no existe en HR.
        """
        return self._get_rotacion_field(linea, "pct_rotacion_mensual")


    def get_pct_ausentismo(self, linea: str) -> float:
        """Porcentaje de ausentismo para una línea de negocio."""
        return self._get_rotacion_field(linea, "pct_ausentismo")


    def get_pct_examen_anual(self, linea: str) -> float:
        """Porcentaje de exámenes médicos anuales para una línea de negocio."""
        return self._get_rotacion_field(linea, "pct_examen_anual")


    def _get_rotacion_field(self, linea: str, campo: str) -> float:
        """Lookup linea/campo en el cache de rotacion_ausentismo.

        El cache siempre está en formato lista normalizada:
            [{"linea": "Cobranzas", "pct_rotacion_mensual": X, "pct_ausentismo": Y, ...}]

        Estrategia: busca la linea exacta (case-insensitive), si no existe usa "default".
        """
        self._ensure_hr_loaded()

        tabla = self._rotacion_ausentismo
        if not tabla:
            raise ParametrizationError(
                "HR-rotacion_ausentismo section missing. "
                "Sube un Excel con hoja HR-AutRot que tenga columnas: "
                "tipo (Rotacion/Ausentismo), servicio, mes, valor.",
                module="hr",
            )

        linea_norm = self._normalize(linea)

        # Búsqueda 1: match exacto por linea normalizada
        for row in tabla:
            if self._normalize(row.get("linea", "")) == linea_norm:
                val = row.get(campo)
                if val is None:
                    raise ParametrizationError(
                        f"Campo '{campo}' no encontrado para linea='{linea}' "
                        f"en HR-rotacion_ausentismo. Row: {row}",
                        module="hr",
                    )
                v = float(val)
                logger.info(
                    "[PARAM_SOURCE] parameter=%s linea=%s source=HR-AutRot value=%s",
                    campo, linea, v,
                )
                return v

        # Búsqueda 2: fila "default"
        for row in tabla:
            if self._normalize(row.get("linea", "")) == "default":
                v = float(row.get(campo, 0.0))
                logger.info(
                    "[PARAM_SOURCE] parameter=%s linea=%s source=HR-AutRot(default) value=%s",
                    campo, linea, v,
                )
                return v

        # Nada encontrado — loguear opciones disponibles
        disponibles = [r.get("linea") for r in tabla]
        logger.error(
            "[ROTACION_LOOKUP] linea='%s' no encontrada. Disponibles: %s",
            linea, disponibles
        )
        raise ParametrizationError(
            f"Linea '{linea}' no encontrada en HR-AutRot. "
            f"Disponibles: {disponibles}. "
            f"Agrega una fila con linea='{linea}' o linea='default'.",
            module="hr",
        )

    # -----------------------------------------------------------------------
    # Costos Operativos (HR-costos_operativos)
    # -----------------------------------------------------------------------


    def _load_rotacion_ausentismo_cache(self) -> None:
        """Detect and cache rotacion_ausentismo from multiple possible locations.

        Supports two formats:

        Formato A — ya normalizado (linea/pct_*):
            [{"linea": "Cobranzas", "pct_rotacion_mensual": 0.10, "pct_ausentismo": 0.08, ...}]

        Formato B — raw HR-AutRot (tipo/servicio/mes/valor):
            [{"tipo": "Rotacion", "servicio": "Cobranzas", "mes": 1.0, "valor": 0.0931}, ...]
            → Se transforma automáticamente al Formato A promediando los meses.
        """
        if self._rotacion_loaded:
            return

        raw = (
            self._hr_data.get("rotacion_ausentismo")
            or self._hr_data.get("payroll", {}).get("rotacion_ausentismo")
            or self._hr_data.get("hr", {}).get("rotacion_ausentismo")
        )

        sheet_source = "top-level"
        if not raw:
            extra_sheets = self._hr_data.get("extra_sheets", {})
            logger.debug(
                "[PAYROLL_REPO] extra_sheets available: %s",
                list(extra_sheets.keys()) if extra_sheets else "NONE"
            )
            for candidate in ["HR-Rotacion", "HR-AutRot", "HR-rotacion_ausentismo", "HR-Rotacion-Ausentismo"]:
                if candidate in extra_sheets:
                    raw = extra_sheets[candidate]
                    sheet_source = candidate
                    break
            if not raw:
                patterns = ["rotacion", "ausentismo", "autrot"]
                for name, data in extra_sheets.items():
                    if any(p in name.lower() for p in patterns):
                        raw = data
                        sheet_source = name
                        break

        if not raw:
            extra_sheets = self._hr_data.get("extra_sheets", {})
            logger.warning(
                "[PAYROLL_REPO] rotacion_ausentismo NOT FOUND. "
                "extra_sheets disponibles: %s",
                list(extra_sheets.keys()) if extra_sheets else "NONE"
            )
            self._rotacion_ausentismo = []
            self._rotacion_loaded = True
            return

        logger.info(
            "[PAYROLL_REPO] rotacion_ausentismo raw encontrado en '%s' (%s)",
            sheet_source,
            f"{len(raw)} filas" if isinstance(raw, (list, dict)) else type(raw).__name__,
        )

        # Formato V2-7: dict {"ausentismo": {linea: pct, ...}, "rotacion": {linea: pct, ...}}
        # Lo transformamos a la lista canónica [{linea, pct_rotacion_mensual, pct_ausentismo, pct_examen_anual}, ...]
        if isinstance(raw, dict) and ("ausentismo" in raw or "rotacion" in raw):
            ausent_map = raw.get("ausentismo", {}) or {}
            rot_map    = raw.get("rotacion", {}) or {}
            lineas = set(ausent_map.keys()) | set(rot_map.keys())
            rows: list = []
            for linea in sorted(lineas):
                rows.append({
                    "linea": linea,
                    "pct_rotacion_mensual": float(rot_map.get(linea, 0.0) or 0.0),
                    "pct_ausentismo":       float(ausent_map.get(linea, 0.0) or 0.0),
                    "pct_examen_anual":     1.0,
                })
            self._rotacion_ausentismo = rows
            logger.info(
                "[PAYROLL_REPO] rotacion_ausentismo (dict V2-7) normalizado a %d filas",
                len(rows),
            )
        else:
            # Detectar formato: si las filas tienen "tipo"/"servicio"/"mes"/"valor"
            # es el formato HR-AutRot y hay que transformarlo
            first = raw[0] if raw else {}
            if "tipo" in first and "servicio" in first and "mes" in first:
                self._rotacion_ausentismo = self._transform_autrot(raw, sheet_source)
            else:
                # Ya está en Formato A, usar directamente
                self._rotacion_ausentismo = raw
                logger.info(
                    "[PAYROLL_REPO] rotacion_ausentismo ya en formato linea/pct_* (%d filas)",
                    len(raw)
                )

        self._rotacion_loaded = True
        logger.info(
            "[PAYROLL_REPO] rotacion_ausentismo cache listo: %d lineas — %s",
            len(self._rotacion_ausentismo),
            [r.get("linea") for r in self._rotacion_ausentismo]
        )

    @staticmethod

    def _transform_autrot(rows: list, source: str) -> list:
        """Transforma HR-AutRot (tipo/servicio/mes/valor) al formato estándar.

        Agrupa por servicio, promedia todos los meses por tipo, y devuelve:
            [{"linea": "Cobranzas", "pct_rotacion_mensual": X, "pct_ausentismo": Y, "pct_examen_anual": 1.0}]

        pct_examen_anual se fija en 1.0 (todos los agentes pasan examen anual).
        Si el Excel lo incluye como tipo "Examen Anual" o similar se toma su promedio.
        """
        from collections import defaultdict

        # Mapeo flexible de los valores del campo "tipo"
        TIPO_ROTACION  = {"rotacion", "rotación", "rotation"}
        TIPO_AUSENT    = {"ausentismo", "ausencia", "absence"}
        TIPO_EXAMEN    = {"examen anual", "examen_anual", "examen", "annual exam"}

        # Acumular sumas y conteos por servicio+tipo
        sums: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            tipo     = str(row.get("tipo", "")).strip().lower()
            servicio = str(row.get("servicio", "")).strip()
            valor    = row.get("valor")
            if not servicio or valor is None:
                continue
            sums[servicio][tipo].append(float(valor))

        result = []
        for servicio, tipo_vals in sums.items():
            def _avg(tipo_set):
                vals = []
                for tipo_key, lista in tipo_vals.items():
                    if tipo_key in tipo_set:
                        vals.extend(lista)
                return sum(vals) / len(vals) if vals else None

            pct_rotacion = _avg(TIPO_ROTACION)
            pct_ausent   = _avg(TIPO_AUSENT)
            pct_examen   = _avg(TIPO_EXAMEN)

            entry = {
                "linea":                servicio,
                "pct_rotacion_mensual": pct_rotacion if pct_rotacion is not None else 0.0,
                "pct_ausentismo":       pct_ausent   if pct_ausent   is not None else 0.0,
                # 1.0 = 100% de agentes pasan examen anual (se divide /12 en el calculador)
                "pct_examen_anual":     pct_examen   if pct_examen   is not None else 1.0,
            }
            result.append(entry)
            logger.debug(
                "[AUTROT_TRANSFORM] %s → rot=%.4f ausen=%.4f exam=%.4f",
                servicio,
                entry["pct_rotacion_mensual"],
                entry["pct_ausentismo"],
                entry["pct_examen_anual"],
            )

        logger.info(
            "[AUTROT_TRANSFORM] Transformación completa desde '%s': %d servicios → %s",
            source, len(result), [r["linea"] for r in result]
        )
        return result



__all__ = ["PayrollRotacionMixin"]
