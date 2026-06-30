from __future__ import annotations
"""ContextBuilderPerfilesMixin re-export (FASE Z.4.3)."""
from nexa_engine.modules.calculator_motor.mixins.context_builder_perfiles_light_mixin import ContextBuilderPerfilesLightMixin
from nexa_engine.modules.calculator_motor.mixins.context_builder_perfiles_soporte_mixin import ContextBuilderPerfilesSoporteMixin


class ContextBuilderPerfilesMixin(ContextBuilderPerfilesLightMixin, ContextBuilderPerfilesSoporteMixin):
    """Re-exports all cadena-A profile methods."""

__all__ = ["ContextBuilderPerfilesMixin"]
