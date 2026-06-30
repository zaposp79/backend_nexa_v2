"""Snapshot capture for ParametrizationProvider.

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


class ProviderSnapshotMixin:
    """Mixin: Snapshot capture for ParametrizationProvider."""

    def capture_parametrization_snapshot(
        self,
        ciudad: str,
        linea_negocio: str,
        componente_humano: str = "IPC",
        componente_tecnologico: str = "IPC",
        anio_inicio: int = 2026,
        roles_usados: list | None = None,
        constantes_claves: list | None = None,
    ) -> dict:
        """
        Captura un snapshot de los valores de parametrización relevantes
        para un deal específico (ciudad, línea de negocio, año de inicio).

        FASE 4 — usado por SimulationContextBuilder para incluir en SimulationSnapshot
        la parametrización exacta activa al momento del cálculo.

        Args:
            ciudad:               Ciudad del deal (para ICA).
            linea_negocio:        Línea de negocio (para rotación, ausentismo).
            componente_humano:    Componente de indexación humana.
            componente_tecnologico: Componente de indexación tecnológica.
            anio_inicio:          Año de inicio del contrato.
            roles_usados:         Lista de roles para capturar salarios específicos.
            constantes_claves:    Lista de claves de costos operativos a capturar.

        Returns:
            Dict con todos los valores de parametrización capturados,
            compatible con ParametrizationSnapshot.as_dict().
        """
        from datetime import datetime, timezone

        # Nómina laboral — SMMLV y auxilio
        try:
            nomina_params = self.get_nomina_laboral_params()
            smmlv             = float(nomina_params.get("salario_minimo", 0))
            auxilio_transporte = float(nomina_params.get("auxilio_transporte", 0))
        except Exception:
            smmlv = 0.0
            auxilio_transporte = 0.0

        # Tasas operativas
        try:
            tasa_ica   = self.get_ica(ciudad)
        except Exception:
            tasa_ica   = 0.0
        try:
            tasa_gmf   = self.get_gmf()
        except Exception:
            tasa_gmf   = 0.0
        try:
            tasa_financ = self.tasa_mensual_financiacion()
        except Exception:
            tasa_financ = 0.0

        # HR — rotación, ausentismo, examen anual por línea
        try:
            pct_rotacion   = self.get_pct_rotacion(linea_negocio)
        except Exception:
            pct_rotacion   = 0.0
        try:
            pct_ausentismo = self.get_pct_ausentismo(linea_negocio)
        except Exception:
            pct_ausentismo = 0.0
        try:
            pct_examen     = self.get_pct_examen_anual(linea_negocio)
        except Exception:
            pct_examen     = 0.0

        # Factores de indexación para los años del contrato
        factores: Dict[str, float] = {}
        for anio in (anio_inicio, anio_inicio + 1, anio_inicio + 2):
            for comp_key, comp_val in (
                (componente_humano, componente_humano),
                (componente_tecnologico, componente_tecnologico),
            ):
                try:
                    factor = self.get_factor_indexacion(comp_val, anio)
                    factores[f"{comp_val}_{anio}"] = factor
                except Exception:
                    pass

        # Salarios por rol (solo los usados en el deal)
        salarios: Dict[str, float] = {}
        for rol in (roles_usados or []):
            try:
                salarios[rol] = self.get_salario_rol(rol)
            except Exception:
                pass

        # Constantes operativas relevantes
        # NOTA: tarifa_dia_cap, opex_ti_por_estacion, capex_recurrente_por_estacion
        # son valores calculados en runtime (no en parametrización).
        # mes_inicio_ajuste_anual es un backend constant (MES_INICIO_AJUSTE_ANUAL).
        # pct_aumento_tecnologico_anual se obtiene via get_componente_indexacion().
        constantes_default = []  # Ahora todos los valores vienen de otras fuentes
        constantes: Dict[str, float] = {}
        for clave in (constantes_claves or constantes_default):
            try:
                constantes[clave] = self.get_costo_operativo(clave)
            except Exception:
                pass

        return {
            "parametrization_id":      "",  # se llenará con versión activa si está disponible
            "captured_at":             datetime.now(timezone.utc).isoformat(),
            "smmlv":                   smmlv,
            "auxilio_transporte":      auxilio_transporte,
            "linea_negocio":           linea_negocio,
            "pct_rotacion_linea":      pct_rotacion,
            "pct_ausentismo_linea":    pct_ausentismo,
            "pct_examen_anual_linea":  pct_examen,
            "ciudad":                  ciudad,
            "tasa_ica_ciudad":         tasa_ica,
            "tasa_gmf":                tasa_gmf,
            "tasa_mensual_financiacion": tasa_financ,
            "componente_humano":       componente_humano,
            "componente_tecnologico":  componente_tecnologico,
            "factores_indexacion":     factores,
            "constantes_operativas":   constantes,
            "salarios_por_rol":        salarios,
        }


__all__ = ["ProviderSnapshotMixin"]
