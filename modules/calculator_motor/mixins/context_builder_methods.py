from __future__ import annotations
"""Facade mixin re-exporting all private builder methods (FASE Z.4.3)."""
from nexa_engine.modules.calculator_motor.mixins.context_builder_cadena_a_mixin import ContextBuilderCadenaAMixin
from nexa_engine.modules.calculator_motor.mixins.context_builder_panel_bc_mixin import ContextBuilderPanelBCMixin


class ContextBuilderMethodsMixin(ContextBuilderCadenaAMixin, ContextBuilderPanelBCMixin):
    """Re-exports all private builder methods via multiple inheritance."""

__all__ = ["ContextBuilderMethodsMixin"]
