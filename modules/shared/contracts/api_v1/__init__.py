"""
contracts/api_v1
=================

Frozen public API contract (version 1) for the NEXA pricing engine.

Anything exposed here is part of the binding wire contract. Breaking
changes go in ``api_v2``; ``api_v1`` only accepts additive, optional
fields. See ``contracts/README.md``.

The on-the-wire identifier is ``api-v1`` (kept dashed for HTTP/JSON
compatibility); the Python package uses ``api_v1`` (underscored) so
``import contracts.api_v1`` works.
"""

from .request.entry_data import EntryDataV1, ContractMetadataV1
from .request.panel import PanelDeControlRequestV1
from .request.cadena_a import (
    CadenaARequestV1,
    PerfilCadenaAV1,
)
from .request.cadena_b import (
    CadenaBRequestV1,
    CanalCadenaBV1,
    ItemOpexConsumoV1,
    MiembroEquipoSMV1,
    DispositivoSMV1,
)
from .request.cadena_c import (
    CadenaCRequestV1,
    CanalCadenaCV1,
    MiembroEquipoTransversalV1,
)
from .request.escenarios import EscenarioComercialV1
from .response.visions import (
    VisionTarifasV1,
    VisionPyGV1,
    CostToServeV1,
    WaterfallV1,
    VisionsBundleV1,
)
from .response.kpis import KpisV1
from .response.simulation_result import SimulationResultV1
from .adapter import entry_data_v1_to_simulation_request

API_VERSION = "api-v1"

__all__ = [
    "API_VERSION",
    "EntryDataV1",
    "ContractMetadataV1",
    "PanelDeControlRequestV1",
    "CadenaARequestV1",
    "PerfilCadenaAV1",
    "CadenaBRequestV1",
    "CanalCadenaBV1",
    "ItemOpexConsumoV1",
    "MiembroEquipoSMV1",
    "DispositivoSMV1",
    "CadenaCRequestV1",
    "CanalCadenaCV1",
    "MiembroEquipoTransversalV1",
    "EscenarioComercialV1",
    "VisionTarifasV1",
    "VisionPyGV1",
    "CostToServeV1",
    "WaterfallV1",
    "VisionsBundleV1",
    "KpisV1",
    "SimulationResultV1",
    "entry_data_v1_to_simulation_request",
]
