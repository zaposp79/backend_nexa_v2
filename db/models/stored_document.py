"""Envoltorio técnico de persistencia para payloads lógicos de dominio.

``StoredDocument`` separa la metadata del backend (``id`` y valor opcional de
partición) del payload lógico perteneciente a un repositorio de dominio. Los
providers pueden usar la metadata para nombres de archivo, ids de documento o
ruteo de partición, pero no deben inyectarla en ``payload``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

JsonPayload = dict[str, Any] | list[Any]


@dataclass(frozen=True)
class StoredDocument:
    """Registro orientado al provider con metadata fuera del payload."""

    id: str
    payload: JsonPayload
    partition_value: str | None = None
    etag: str | None = None


__all__ = ["JsonPayload", "StoredDocument"]
