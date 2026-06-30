"""
backend_nexa / nexa_engine
==========================
Motor de reglas de precios NEXA.

API publica:
    from nexa_engine import NexaPricingEngine
    engine = NexaPricingEngine()
    result = engine.calcular(request)
"""

from __future__ import annotations

import sys
from types import ModuleType

# Set up nexa_engine as an alias for this package
current_module = sys.modules[__name__]
sys.modules.setdefault("nexa_engine", current_module)

# Ensure submodules are registered when accessed via nexa_engine
class _ModuleProxy(ModuleType):
    def __getattr__(self, name):
        # First try to get from current module
        try:
            return getattr(current_module, name)
        except AttributeError:
            # Then try to import as a submodule
            module_name = f"{current_module.__name__}.{name}"
            try:
                __import__(module_name)
                return sys.modules[module_name]
            except ImportError:
                raise AttributeError(f"module {current_module.__name__!r} has no attribute {name!r}")

# Override the nexa_engine module reference to use the proxy
nexa_engine_module = _ModuleProxy("nexa_engine")
nexa_engine_module.__dict__.update(current_module.__dict__)
sys.modules["nexa_engine"] = nexa_engine_module

from .modules.calculator_motor.engine import NexaPricingEngine

__all__ = ["NexaPricingEngine"]
__version__ = "3.0.0"
