"""
nexa_engine/domain/normalized_input.py
=======================================
Resultado de la normalización de entrada — FASE 2.

Contiene:
  - El input original sin modificar (raw)
  - El input normalizado listo para el pipeline (data)
  - El log de auditoría: defaults aplicados, advertencias, errores
  - El modo de normalización usado

Este dataclass es el contrato entre InputNormalizer (FASE 2)
y el resto del pipeline. Garantiza trazabilidad completa de
cualquier transformación o default aplicado a los datos de entrada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class NormalizationMode(str, Enum):
    """
    Modo de normalización — controla cómo se manejan campos faltantes y errores.

    STRICT:
        Raise ValueError inmediatamente ante cualquier campo requerido faltante
        o valor inválido. El modo más seguro para producción.

    VALIDATION:
        Recolecta todos los errores de validación sin interrumpir el proceso.
        Al finalizar, si hay errores los lanza como un único ValueError consolidado.
        Útil para feedback completo al usuario (formulario de entrada).

    AUDIT:
        Loguea advertencias pero continúa incluso con campos faltantes,
        aplicando defaults documentados. Útil para pipelines de migración de datos
        o revisión de inputs históricos. NO usar en producción para nuevos contratos.
    """
    STRICT = "strict"
    CONTRACT_STRICT = "contract_strict"
    VALIDATION = "validation"
    AUDIT = "audit"


@dataclass
class DefaultApplied:
    """Registro de un default aplicado durante la normalización."""
    field_path: str       # ruta al campo, ej. "datos_operativos.ciudad"
    value: Any            # valor del default aplicado
    reason: str           # justificación documentada del default


@dataclass
class NormalizationWarning:
    """Advertencia no-bloqueante durante la normalización."""
    field_path: str
    message: str
    original_value: Any = None


@dataclass
class NormalizationError:
    """Error de validación — campo requerido faltante o valor inválido."""
    field_path: str
    message: str
    original_value: Any = None


@dataclass
class NormalizationLog:
    """
    Log de auditoría completo de la normalización.

    El log permite reconstruir exactamente qué transformaciones
    se aplicaron al input original para producir el input normalizado.
    """
    mode: NormalizationMode = NormalizationMode.STRICT
    defaults_applied: List[DefaultApplied] = field(default_factory=list)
    warnings: List[NormalizationWarning] = field(default_factory=list)
    errors: List[NormalizationError] = field(default_factory=list)

    # ── helpers ────────────────────────────────────────────────────────

    def add_default(self, field_path: str, value: Any, reason: str) -> None:
        self.defaults_applied.append(DefaultApplied(field_path, value, reason))

    def add_warning(self, field_path: str, message: str, original_value: Any = None) -> None:
        self.warnings.append(NormalizationWarning(field_path, message, original_value))

    def add_error(self, field_path: str, message: str, original_value: Any = None) -> None:
        self.errors.append(NormalizationError(field_path, message, original_value))

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def raise_if_errors(self) -> None:
        """Lanza ValueError consolidado si hay errores (modo VALIDATION)."""
        if not self.has_errors:
            return
        msgs = "\n".join(
            f"  [{i+1}] Campo '{e.field_path}': {e.message}"
            for i, e in enumerate(self.errors)
        )
        raise ValueError(
            f"Se encontraron {len(self.errors)} errores de validación:\n{msgs}"
        )

    def summary(self) -> str:
        """Resumen textual del log para logging/debugging."""
        lines = [f"NormalizationLog (mode={self.mode.value})"]
        if self.defaults_applied:
            lines.append(f"  Defaults aplicados ({len(self.defaults_applied)}):")
            for d in self.defaults_applied:
                lines.append(f"    {d.field_path} = {d.value!r} — {d.reason}")
        if self.warnings:
            lines.append(f"  Advertencias ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"    {w.field_path}: {w.message}")
        if self.errors:
            lines.append(f"  Errores ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"    {e.field_path}: {e.message}")
        return "\n".join(lines)


@dataclass
class NormalizedInput:
    """
    Input normalizado — resultado de InputNormalizer.normalize().

    Contrato:
      raw:  El JSON original del usuario, sin modificar.
            Preservado para trazabilidad completa y auditoría.

      data: El dict normalizado listo para ingresar al pipeline
            (UserInputLoader → SimulationContextBuilder → NexaPricingEngine).
            Campo names alineados con el formato interno.
            Defaults explícitamente aplicados.
            Estructuras aplanadas donde el pipeline lo requiere.

      log:  Registro completo de cada transformación:
            - defaults aplicados (con justificación)
            - advertencias no-bloqueantes
            - errores de validación (en modo VALIDATION/AUDIT)
    """
    raw: Dict[str, Any]
    data: Dict[str, Any]
    log: NormalizationLog

    @property
    def mode(self) -> NormalizationMode:
        return self.log.mode

    @property
    def is_valid(self) -> bool:
        return not self.log.has_errors
