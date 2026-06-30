"""Cadena A normalization methods for InputNormalizer.

Mixin for InputNormalizer — FASE Z.2.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from nexa_engine.modules.calculator_motor.dto.normalized_input import (
    NormalizationLog, NormalizationWarning, NormalizationError,
    NormalizationMode, DefaultApplied, NormalizedInput,
)
logger = logging.getLogger(__name__)


class InputNormalizerCadenaAMixin:
    """Mixin: Cadena A normalization methods for InputNormalizer."""

    def _normalizar_cadena_a(
        self,
        cadena_a: Dict,
        mode: NormalizationMode,
        log: NormalizationLog,
    ) -> Dict:
        """
        Normaliza condiciones_cadena_a para compatibilidad con el pipeline interno.

        Transforma cada perfil:
        - Aplanar capacitacion{} → campos top-level compatibles con _perfil_a()
        - Preservar estructura completa (capacitacion, opex_fijo, inversiones,
          roles_operativos) para uso por SimulationContextBuilder
        - Aplicar defaults documentados en cada campo de capacitacion
        - Detectar y desanidar doble-anidamiento accidental de condiciones_cadena_a
        """
        # Detect accidental double-nesting: {"condiciones_cadena_a": {"perfiles": [...]}}
        # instead of {"perfiles": [...]}. Unwrap transparently and log a warning.
        if "condiciones_cadena_a" in cadena_a and "perfiles" not in cadena_a:
            inner = cadena_a["condiciones_cadena_a"]
            if isinstance(inner, dict) and "perfiles" in inner:
                log.add_warning(
                    "condiciones_cadena_a",
                    "condiciones_cadena_a doble-anidado detectado "
                    "({'condiciones_cadena_a': {'perfiles': [...]}}) — "
                    "desanidando automáticamente. El JSON debe enviar "
                    "{'perfiles': [...]} directamente sin envoltura extra.",
                )
                cadena_a = inner

        perfiles_raw = cadena_a.get("perfiles", [])
        perfiles_normalizados = []

        for i, perfil in enumerate(perfiles_raw):
            perfil_norm = self._normalizar_perfil_a(perfil, i, mode, log)
            perfiles_normalizados.append(perfil_norm)

        return {**cadena_a, "perfiles": perfiles_normalizados}


    def _normalizar_perfil_a(
        self,
        perfil: Dict,
        idx: int,
        mode: NormalizationMode,
        log: NormalizationLog,
    ) -> Dict:
        """
        Normaliza un perfil de cadena_a:

        1. Valida campos requeridos (nombre, modalidad, canal, fte)
        2. Aplana capacitacion{} → campos flat para _perfil_a()
        3. Preserva todas las sub-estructuras ricas (capacitacion, opex_fijo,
           inversiones, roles_operativos) para SimulationContextBuilder

        El perfil resultante tiene TODOS los campos del original MÁS los
        campos flat necesarios para el pipeline interno. NO se elimina nada.
        """
        prefix = f"condiciones_cadena_a.perfiles[{idx}]"
        perfil_norm = dict(perfil)  # copia shallow — sub-dicts son referencias

        # ── a. Validar campos requeridos del perfil ───────────────────────
        for campo_req in ("nombre", "modalidad", "canal", "fte"):
            if perfil.get(campo_req) is None or (
                isinstance(perfil.get(campo_req), str)
                and not perfil.get(campo_req).strip()
            ):
                self._registrar_error(
                    f"Campo requerido '{campo_req}' falta o está vacío en perfil[{idx}].",
                    f"{prefix}.{campo_req}",
                    perfil.get(campo_req),
                    mode,
                    log,
                )

        # ── b. Aplanar capacitacion{} → campos flat ───────────────────────
        # La especificación oficial usa capacitacion{} pero _perfil_a() espera
        # los campos a nivel raíz del perfil. Hacemos el flatten aquí y
        # PRESERVAMOS capacitacion{} completo para SimulationContextBuilder.
        cap = perfil.get("capacitacion", {})

        # dias_cap_inicial / dias_cap_rotacion ← capacitacion.dias_capacitacion_perfil
        if "dias_cap_inicial" not in perfil_norm:
            dias = cap.get("dias_capacitacion_perfil")
            if dias is None:
                dias = 10
                log.add_default(
                    f"{prefix}.dias_cap_inicial",
                    10,
                    "Días de capacitación inicial: 10 es estándar operativo BPO",
                )
            perfil_norm["dias_cap_inicial"] = int(dias)
            perfil_norm["dias_cap_rotacion"] = int(dias)  # mismo valor por defecto

        # incluye_examenes ← capacitacion.incluye_costo_examenes_ingreso
        if "incluye_examenes" not in perfil_norm:
            val = cap.get("incluye_costo_examenes_ingreso", True)
            perfil_norm["incluye_examenes"] = bool(val)
            if "incluye_costo_examenes_ingreso" not in cap:
                log.add_default(
                    f"{prefix}.incluye_examenes",
                    True,
                    "Exámenes médicos de ingreso incluidos por defecto (estándar legal Colombia)",
                )

        # incluye_seguridad ← capacitacion.incluye_estudio_seguridad_ingreso
        if "incluye_seguridad" not in perfil_norm:
            val = cap.get("incluye_estudio_seguridad_ingreso", False)
            perfil_norm["incluye_seguridad"] = bool(val)
            if "incluye_estudio_seguridad_ingreso" not in cap:
                log.add_default(
                    f"{prefix}.incluye_seguridad",
                    False,
                    "Estudio de seguridad NO incluido por defecto — solo clientes que lo requieran",
                )

        # ── c. Defaults de campos opcionales del perfil ───────────────────
        if perfil_norm.get("pct_presencia") is None:
            perfil_norm["pct_presencia"] = 1.0
            log.add_default(
                f"{prefix}.pct_presencia",
                1.0,
                "Presencia 100% por defecto — modelo híbrido requiere valor explícito",
            )

        if perfil_norm.get("comision_pct") is None:
            perfil_norm["comision_pct"] = 0.0
            log.add_default(
                f"{prefix}.comision_pct",
                0.0,
                "Sin comisión por defecto — solo perfiles de venta la usan",
            )

        # ── d. rol — si no existe, usar nombre del perfil como fallback ───
        # (backward compat con pipeline existente que hace d.get("rol", d.get("nombre")))
        if not perfil_norm.get("rol"):
            perfil_norm["rol"] = perfil_norm.get("nombre", "Agente Basico")
            log.add_default(
                f"{prefix}.rol",
                perfil_norm["rol"],
                "Rol derivado del nombre del perfil — proveer 'rol' explícito para lookup en parametrización",
            )

        # ── e. Preservar capacitacion completo para SimulationContextBuilder ──
        # Ya está en perfil_norm como referencia desde el dict original.
        # Si capacitacion no está, inicializar vacío para que el context_builder
        # no falle al acceder a sub-campos.
        if "capacitacion" not in perfil_norm:
            perfil_norm["capacitacion"] = {}

        return perfil_norm

    # ──────────────────────────────────────────────────────────────────────
    # Normalización de escenarios_comerciales
    # ──────────────────────────────────────────────────────────────────────



__all__ = ["InputNormalizerCadenaAMixin"]
