"""Servicio de generación de alias determinístico para identidades anónimas.

El alias se deriva del identityId (UUID v4) mediante SHA-256 sobre sus bytes.
La misma entrada siempre produce el mismo alias (determinismo estricto).
El algoritmo está aislado para permitir cambios futuros sin tocar IdentityService.
"""
from __future__ import annotations

import hashlib
from uuid import UUID

_ANIMALS = [
    "Jaguar", "Lince", "Cóndor", "Puma", "Águila", "Zorro", "Lobo",
    "Tigre", "León", "Pantera", "Guepardo", "Halcón", "Delfín", "Búfalo",
    "Colibrí", "Ocelote", "Nutria", "Guacamayo", "Tucán", "Perezoso",
    "Venado", "Coatí", "Capibara", "Tapir", "Caimán", "Flamenco",
    "Armadillo", "Manatí", "Paca", "Hormiguero",
]

_COLORS = [
    "Azul", "Dorado", "Verde", "Gris", "Rojo", "Plateado", "Negro",
    "Blanco", "Coral", "Turquesa", "Violeta", "Esmeralda", "Ámbar",
    "Jade", "Índigo", "Escarlata", "Celeste", "Carmesí", "Bronce", "Magenta",
]

# Números del 10 al 99 — evita ceros iniciales y da 90 combinaciones adicionales
_NUMBERS = list(range(10, 100))


class AliasService:
    """Genera alias legibles y determinísticos a partir de un identityId.

    Ejemplo:
        AliasService().generate("9b8c7f...") → "Jaguar Azul 27"
        AliasService().generate("9b8c7f...") → "Jaguar Azul 27"  # siempre igual
    """

    def generate(self, identity_id: str) -> str:
        """Genera el alias para el identityId dado.

        Args:
            identity_id: UUID v4 en formato string.

        Returns:
            Alias en formato "Animal Color Número" (ej. "Jaguar Azul 27").
        """
        uid_bytes = UUID(identity_id).bytes          # 16 bytes del UUID
        digest = hashlib.sha256(uid_bytes).digest()  # 32 bytes uniformes

        animal_idx = int.from_bytes(digest[0:4], "big") % len(_ANIMALS)
        color_idx  = int.from_bytes(digest[4:8], "big") % len(_COLORS)
        number     = _NUMBERS[int.from_bytes(digest[8:10], "big") % len(_NUMBERS)]

        return f"{_ANIMALS[animal_idx]} {_COLORS[color_idx]} {number}"
