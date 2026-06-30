"""Excepciones técnicas para la capa de persistencia transversal."""

from __future__ import annotations


class DbError(Exception):
    """Clase base para todos los errores de la capa de persistencia."""


class DbNotFoundError(DbError):
    """El documento solicitado no existe en la colección."""


class DbConnectionError(DbError):
    """El backend es inaccesible o rechazó la conexión."""


class DbConfigurationError(DbError):
    """El backend está mal configurado (ruta faltante, credenciales, etc.)."""


class DbSerializationError(DbError):
    """Un documento no pudo ser serializado/deserializado o está malformado."""


class DbConflictError(DbError):
    """Una escritura conflictó con el estado actual del backend."""


class DbConcurrencyError(DbConflictError):
    """La precondición de concurrencia optimista falló."""


__all__ = [
    "DbError",
    "DbNotFoundError",
    "DbConnectionError",
    "DbConfigurationError",
    "DbSerializationError",
    "DbConflictError",
    "DbConcurrencyError",
]
