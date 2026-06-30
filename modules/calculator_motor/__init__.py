"""calculator_motor package.

Owns pricing orchestration, calculation-side request assembly, motor-owned
formulas, validation helpers, adapters, serializers, and result models.

Current key entrypoints:

- ``engine.py``: ``NexaPricingEngine``
- ``context_builder.py``: ``SimulationContextBuilder``
- ``adapters/user_input_loader.py``: ``UserInputLoader``
- ``serializers/``: pricing result serialization helpers

This package documents the current structure only. It does not claim that all
validation files already live under ``validation/`` or that any pending layout
cleanup has been completed.
"""
