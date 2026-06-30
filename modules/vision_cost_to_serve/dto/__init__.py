"""
Public DTO contracts — shared between calculator_motor and vision layer.

Ownership: vision_cost_to_serve · public contract.
calculator_motor imports these types to build ResultadoCostToServe.
vision layer imports them to serialize API responses.

These DTOs are the public API contract; changes require version bump.
"""
from nexa_engine.modules.vision_cost_to_serve.dto.models import (  # noqa: F401
    DesgloseCTSCadenaA,
    DesgloseCTSCadenaB,
    CanalCTSDetalle,
    ResultadoCostToServe,
)
