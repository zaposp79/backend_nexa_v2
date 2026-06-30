from __future__ import annotations
"""ContextBuilderCadenaAMixin re-export (FASE Z.4.3)."""
from nexa_engine.modules.calculator_motor.mixins.context_builder_panel_mixin import ContextBuilderPanelMixin
from nexa_engine.modules.calculator_motor.mixins.context_builder_perfiles_mixin import ContextBuilderPerfilesMixin


class ContextBuilderCadenaAMixin(ContextBuilderPanelMixin, ContextBuilderPerfilesMixin):
    """Re-exports panel and cadena-A profile methods."""

__all__ = ["ContextBuilderCadenaAMixin"]
