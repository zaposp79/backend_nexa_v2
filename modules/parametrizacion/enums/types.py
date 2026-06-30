"""Shared enums and types for the NEXA simulator."""

from enum import Enum
from dataclasses import dataclass, field
from typing import List


class ParametrizationDomain(str, Enum):
    OP = "op"
    GN = "gn"
    HR = "hr"


class ChainType(str, Enum):
    A = "chain_a"
    B = "chain_b"
    C = "chain_c"


class Modalidad(str, Enum):
    INBOUND = "Inbound"
    OUTBOUND = "Outbound"


@dataclass
class ValidationResult:
    """Holds the outcome of a validation pass."""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
