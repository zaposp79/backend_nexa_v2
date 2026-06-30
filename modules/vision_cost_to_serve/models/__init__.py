"""
Compatibility re-export: CostToServeFacts / CanalCTSFacts.

Canonical owner: calculator_motor/formulas/cts/cts_facts.py.

vision_cost_to_serve has NO formula implementation.
"""
from nexa_engine.modules.calculator_motor.formulas.cts.cts_facts import (
    CanalCTSFacts,
    CostToServeFacts,
)

__all__ = ["CanalCTSFacts", "CostToServeFacts"]
