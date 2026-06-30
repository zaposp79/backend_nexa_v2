"""cadena_a domain enums."""
from __future__ import annotations
from enum import Enum


class CargoTipo(Enum):
    OPERATIVO     = "OPERATIVO"
    ADMINISTRATIVO = "ADMINISTRATIVO"
    AGENTE        = "AGENTE"
    VALIDADOR     = "VALIDADOR"
    ESPECIALISTA  = "ESPECIALISTA"
    APRENDIZ      = "APRENDIZ"
    INCLUSION     = "INCLUSION"
    DESCONOCIDO   = "DESCONOCIDO"


# ─────────────────────────────────────────────────────────────────────────────
# CargoClassifier
# ─────────────────────────────────────────────────────────────────────────────


__all__ = ["CargoTipo"]
