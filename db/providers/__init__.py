"""Concrete ``DocumentStore`` providers.

Domain code must NOT import from this package — providers are wired only by the
composition root via :func:`nexa_engine.db.factory.get_provider`.
"""
