"""Input normalization owned by calculator_motor.validation.

FASE 2 — InputNormalizer: punto único de normalización del JSON de entrada.

Canonical location note:
  - Este archivo vive en ``calculator_motor.validation`` como ubicación canónica.
  - Su responsabilidad es de validación/normalización previa a builders.
  - Sus helpers internos viven en ``validation.normalization_mixins``.

Responsabilidades:
  1. Validar campos requeridos según NormalizationMode (STRICT/VALIDATION/AUDIT)
  2. Aplanar estructuras anidadas del formato oficial a nombres internos
  3. Aplicar defaults explícitos y documentados (sin defaults silenciosos)
  4. Retornar NormalizedInput con log de auditoría completo

Principios de diseño (IMPORTANTE — NO violar):
  - NO inferir campos mágicamente
  - NO simplificar estructuras de datos
  - NO eliminar campos aparentemente redundantes
  - NO recalcular información que ya viene en el JSON
  - Cada default aplicado DEBE estar documentado en el log
  - El input original (raw) se preserva intacto

Mappings principales (official JSON → internal format):
  condiciones_cadena_a.perfiles[].capacitacion.dias_capacitacion_perfil
      → perfiles[].dias_cap_inicial (y dias_cap_rotacion)
  condiciones_cadena_a.perfiles[].capacitacion.incluye_costo_examenes_ingreso
      → perfiles[].incluye_examenes
  condiciones_cadena_a.perfiles[].capacitacion.incluye_estudio_seguridad_ingreso
      → perfiles[].incluye_seguridad

Defaults explícitos documentados (DefaultRegistry):
  Ver DEFAULT_REGISTRY al final del módulo.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from nexa_engine.modules.calculator_motor.dto.normalized_input import (
    NormalizationLog,
    NormalizationMode,
    NormalizedInput,
)

# ---------------------------------------------------------------------------
# Registro de defaults explícitos — CADA default debe estar aquí documentado
# ---------------------------------------------------------------------------

# (field_path, default_value, reason)
DEFAULT_REGISTRY: List[tuple] = [
    # ── datos_operativos ──────────────────────────────────────────────────
    (
        "datos_operativos.pct_ausentismo",
        None,
        "Override opcional — si es None, la parametrización activa provee el valor por línea de negocio",
    ),
    (
        "datos_operativos.pct_rotacion",
        None,
        "Override opcional — si es None, la parametrización activa provee el valor por línea de negocio",
    ),
    (
        "datos_operativos.tasa_ica",
        None,
        "Override opcional — si es None, lookup por ciudad en parametrización activa",
    ),
    (
        "datos_operativos.tasa_gmf",
        None,
        "Override opcional — si es None, parametrización activa",
    ),
    (
        "datos_operativos.cons_costo_de_financiacion",
        True,
        "Default: se incluye financiación — estándar BPO Colombia",
    ),
    (
        "datos_operativos.sede",
        "",
        "Sede opcional — si está vacía no afecta cálculos",
    ),
    # ── reglas_negocio ───────────────────────────────────────────────────
    (
        "reglas_negocio.contingencia_operativa.valor",
        0.025,
        "Default estándar de contingencia operativa BPO; mínimo contractual típico",
    ),
    (
        "reglas_negocio.contingencia_comercial.valor",
        0.0,
        "Sin contingencia comercial por defecto — legítimo si el deal no tiene riesgo comercial adicional",
    ),
    (
        "reglas_negocio.markup.valor",
        0.0,
        "Sin markup por defecto — se aplica solo si el cliente lo negocia",
    ),
    (
        "reglas_negocio.imprevistos",
        0.0,
        "Sin imprevistos por defecto (GAP-PYG-1); solo para deals con riesgo operativo alto",
    ),
    # ── volumetria.indexacion ────────────────────────────────────────────
    (
        "volumetria.indexacion.componente_humano",
        "IPC",
        "Componente de indexación humana: IPC es el estándar contractual BPO",
    ),
    (
        "volumetria.indexacion.componente_tecnologico",
        "IPC",
        "Componente de indexación tecnológica: IPC por defecto",
    ),
    (
        "volumetria.indexacion.frecuencia",
        "Anual",
        "Frecuencia de indexación anual — estándar BPO Colombia",
    ),
    (
        "volumetria.indexacion.mes_aplicacion",
        1,
        "Mes de aplicación de la indexación: mes 1 del año (enero) por defecto",
    ),
    # ── perfiles cadena_a ────────────────────────────────────────────────
    (
        "condiciones_cadena_a.perfiles[].pct_presencia",
        1.0,
        "Presencia 100% por defecto — modelo híbrido requiere valor explícito",
    ),
    (
        "condiciones_cadena_a.perfiles[].comision_pct",
        0.0,
        "Sin comisión por defecto — solo perfiles de venta la usan",
    ),
    (
        "condiciones_cadena_a.perfiles[].capacitacion.dias_capacitacion_perfil",
        10,
        "Días de capacitación inicial: 10 es estándar operativo BPO (FASE 1 — H7 equivalente para cap)",
    ),
    (
        "condiciones_cadena_a.perfiles[].capacitacion.incluye_costo_examenes_ingreso",
        True,
        "Se incluyen exámenes médicos de ingreso por defecto (estándar legal Colombia)",
    ),
    (
        "condiciones_cadena_a.perfiles[].capacitacion.incluye_costo_examenes_rotacion",
        True,
        "Se incluyen exámenes médicos de rotación por defecto",
    ),
    (
        "condiciones_cadena_a.perfiles[].capacitacion.incluye_estudio_seguridad_ingreso",
        False,
        "Estudio de seguridad NO incluido por defecto — solo clientes que lo requieran",
    ),
    (
        "condiciones_cadena_a.perfiles[].capacitacion.incluye_estudio_seguridad_rotacion",
        False,
        "Estudio de seguridad en rotación NO incluido por defecto",
    ),
    # ── periodo de pago ──────────────────────────────────────────────────
    (
        "panel_de_control.periodo_pago_dias",
        90,
        "Período de pago 90 días — estándar BPO Colombia (FASE 1 — H7)",
    ),
]


# ---------------------------------------------------------------------------
# InputNormalizer
# ---------------------------------------------------------------------------


from nexa_engine.modules.calculator_motor.validation.normalization_mixins.input_normalizer_validation import (
    InputNormalizerValidationMixin,
)
from nexa_engine.modules.calculator_motor.validation.normalization_mixins.input_normalizer_defaults import (
    InputNormalizerDefaultsMixin,
)
from nexa_engine.modules.calculator_motor.validation.normalization_mixins.input_normalizer_cadena_a import (
    InputNormalizerCadenaAMixin,
)
from nexa_engine.modules.calculator_motor.validation.normalization_mixins.input_normalizer_misc import (
    InputNormalizerMiscMixin,
)


class InputNormalizer(
    InputNormalizerValidationMixin,
    InputNormalizerDefaultsMixin,
    InputNormalizerCadenaAMixin,
    InputNormalizerMiscMixin,
):
    """Normalizes entry_data format to internal pipeline format.

    Methods organized in mixins (FASE Z.2):
      InputNormalizerValidationMixin — _validar_*
      InputNormalizerDefaultsMixin   — _aplicar_defaults_*
      InputNormalizerCadenaAMixin    — _normalizar_cadena_a/perfil_a
      InputNormalizerMiscMixin       — _normalizar_escenarios, _registrar_error
    """

    def normalize(
        self,
        raw: Dict[str, Any],
        mode: NormalizationMode = NormalizationMode.STRICT,
    ) -> NormalizedInput:
        """
        Normaliza el input oficial y retorna un NormalizedInput con log de auditoría.

        Args:
            raw: JSON original del usuario (no modificado).
            mode: STRICT (default) | VALIDATION | AUDIT

        Returns:
            NormalizedInput con:
              - raw: input original intacto
              - data: dict normalizado para el pipeline
              - log: auditoría completa de transformaciones y defaults

        Raises:
            ValueError: en modo STRICT o VALIDATION si hay campos requeridos faltantes.
        """
        log = NormalizationLog(mode=mode)
        data = copy.deepcopy(raw)

        # Solo normalizar formato oficial (datos_operativos)
        if "datos_operativos" not in data:
            # Formato legacy — sin transformación, pasa directo
            return NormalizedInput(raw=raw, data=data, log=log)

        # ── 1. Validar campos requeridos ──────────────────────────────────
        self._validar_secciones_requeridas(data, mode, log)
        self._validar_datos_operativos(data, mode, log)
        self._validar_reglas_negocio(data, mode, log)

        # En VALIDATION, lanzar errores consolidados antes de continuar
        if mode == NormalizationMode.VALIDATION:
            log.raise_if_errors()

        # ── 2. Aplicar defaults explícitos a secciones opcionales ─────────
        self._aplicar_defaults_volumetria(data, log)
        self._aplicar_defaults_reglas_negocio(data, log)

        # ── 3. Normalizar condiciones_cadena_a — flatten capacitacion ─────
        if "condiciones_cadena_a" in data:
            data["condiciones_cadena_a"] = self._normalizar_cadena_a(
                data["condiciones_cadena_a"], mode, log
            )

        # ── 4. Normalizar escenarios_comerciales ──────────────────────────
        if "escenarios_comerciales" in data:
            data["escenarios_comerciales"] = self._normalizar_escenarios(
                data["escenarios_comerciales"], log
            )

        return NormalizedInput(raw=raw, data=data, log=log)

    # ──────────────────────────────────────────────────────────────────────
    # Validaciones de campos requeridos
    # ──────────────────────────────────────────────────────────────────────
