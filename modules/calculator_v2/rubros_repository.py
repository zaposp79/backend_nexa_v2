"""
Repositorio para leer rubros_maestro desde CosmosDB.

Container: parameterization (COSMOS_CONTAINER_PARAMETRIZATION)
Partition key field: domain
Valor de partición: rubros_maestros
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from nexa_engine.db.ports.document_store import CollectionConfig, DocumentStore
from .models import RubroMaestro

logger = logging.getLogger("nexa.v2.rubros_repo")

_COLLECTION = CollectionConfig(
    name="parameterization",
    partition_key_field="domain",
)


class RubrosRepository:
    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    def get_rubros_maestros(self) -> List[RubroMaestro]:
        """Carga todos los rubros maestro ordenados por orden_calculo."""
        try:
            docs, _ = self._store.query(_COLLECTION, {"domain": "rubros_maestros"})
        except Exception as exc:
            logger.error("[v2] Error leyendo rubros_maestros de Cosmos: %s", exc)
            raise

        rubros: List[RubroMaestro] = []
        for doc in docs:
            try:
                rubros.append(RubroMaestro(**doc))
            except Exception as exc:
                logger.warning("[v2] Rubro inválido (id=%s): %s", doc.get("id"), exc)

        rubros.sort(key=lambda r: r.orden_calculo)
        logger.info("[v2] %d rubros_maestros cargados", len(rubros))
        return rubros

    def get_ramp_up_campana(self, servicio: str) -> Optional[List[float]]:
        """Lee el calendario de ramp-up desde HR-Campaña para el tipo de servicio.

        Fuente: payload.campana en la HR parametrización activa.
        Filtro: categoriaservicio == servicio (case-insensitive).
        Retorna lista ordenada por mes (índice 0 = mes 1).
        Retorna None si no hay datos para ese servicio.
        """
        try:
            docs, _ = self._store.query(_COLLECTION, {"domain": "hr"})
        except Exception as exc:
            logger.error("[v2] Error leyendo HR-Campaña: %s", exc)
            return None

        active = next((d for d in docs if d.get("status") == "active"), None)
        if not active:
            return None

        campana: List[dict] = active.get("payload", {}).get("campana", [])
        servicio_lower = str(servicio).strip().lower()

        # Filtra por servicio y ordena por mes
        items = sorted(
            (r for r in campana if str(r.get("categoriaservicio", "")).strip().lower() == servicio_lower),
            key=lambda r: int(r.get("mes", 0)),
        )
        if not items:
            logger.warning("[v2] No hay ramp_up en HR-Campaña para servicio='%s'", servicio)
            return None

        result = [float(r.get("valor", 1.0)) for r in items]
        logger.info("[v2] ramp_up '%s': %s", servicio, result[:12])
        return result

    def get_ipc_rates_op(self) -> Dict[int, float]:
        """Lee tasas IPC por año desde OP-Componente en CosmosDB (domain='op').

        # Excel V2-8: 'Panel de Control General'!L7-L10 — IPC indexación anual
        # Filtra filas de OP-Componente donde Componente='IPC' y retorna {año: tasa}.
        # Ejemplo: {2026: 0.0, 2027: 0.0555, 2028: 0.0584}
        """
        try:
            docs, _ = self._store.query(_COLLECTION, {"domain": "op"})
        except Exception as exc:
            logger.error("[v2] Error leyendo OP parametrización para IPC: %s", exc)
            return {}

        active = next((d for d in docs if d.get("status") == "active"), None)
        if not active:
            logger.warning("[v2] No hay OP parametrización activa — IPC no se aplicará")
            return {}

        componente_rows = active.get("payload", {}).get("componente", [])
        rates: Dict[int, float] = {}
        for row in componente_rows:
            if str(row.get("componente", "")).strip().upper() == "IPC":
                # Cosmos guarda el campo sin ñ ("ano"), fallback por si cambia
                anio = row.get("ano") if row.get("ano") is not None else row.get("año")
                valor = row.get("valor")
                if anio is not None and valor is not None:
                    rates[int(anio)] = float(valor)

        logger.info("[v2] OP IPC rates cargadas: %s", rates)
        return rates

    def get_hr_costo_fijo_estacion(self, ciudad: str, localidad: str = "") -> float:
        """Suma de costos fijos por estación para la ciudad/localidad del deal (de HR activa).

        Filtra primero por ciudad + localidad (sede); si no hay coincidencias exactas
        (localidad vacía o no configurada en HR), cae back a ciudad sola.
        Esto evita sumar costos de TODAS las localidades de una ciudad cuando el HR
        tiene múltiples localidades por ciudad (ej. Bogotá/Toberín, Bogotá/Chapinero).
        """
        try:
            docs, _ = self._store.query(_COLLECTION, {"domain": "hr"})
        except Exception as exc:
            logger.error("[v2] Error leyendo HR parametrización: %s", exc)
            return 0.0

        active = next((d for d in docs if d.get("status") == "active"), None)
        if not active:
            logger.warning("[v2] No hay HR parametrización activa")
            return 0.0

        cf_lista = active.get("payload", {}).get("costo_fijo", [])
        ciudad_lower = str(ciudad).strip().lower()
        localidad_lower = str(localidad).strip().lower()

        # Intento 1: filtrar por ciudad + localidad (más específico)
        if localidad_lower:
            rows_localidad = [
                r for r in cf_lista
                if str(r.get("ciudad", "")).strip().lower() == ciudad_lower
                and str(r.get("localidad", "")).strip().lower() == localidad_lower
            ]
            if rows_localidad:
                total = sum(float(r.get("valor", 0)) for r in rows_localidad)
                logger.info("[v2] HR costo_fijo_estacion '%s/%s' = %.2f", ciudad, localidad, total)
                return total
            logger.warning("[v2] No hay costo_fijo para '%s/%s' en HR — fallback a ciudad sola", ciudad, localidad)

        # Intento 2: fallback a ciudad sola (suma todas las localidades)
        total = sum(
            float(r.get("valor", 0))
            for r in cf_lista
            if str(r.get("ciudad", "")).strip().lower() == ciudad_lower
        )
        logger.info("[v2] HR costo_fijo_estacion '%s' (ciudad sola) = %.2f", ciudad, total)
        return total
