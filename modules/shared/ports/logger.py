"""
application.ports.logger
========================

Logger port. Application use cases depend on ILogger; concrete
implementations live in `infrastructure/logging/`.

This decouples the application from `stdlib logging` so tests can inject
a `NullLogger` and remain pure.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ILogger(Protocol):
    """
    Abstract logger consumed by application use cases.

    Implementations may wrap stdlib logging, structlog, or remote sinks.
    Methods accept structured kwargs that the implementation MAY embed
    in the message or emit as separate fields.
    """

    def info(self, msg: str, /, **kwargs: Any) -> None: ...
    def debug(self, msg: str, /, **kwargs: Any) -> None: ...
    def warning(self, msg: str, /, **kwargs: Any) -> None: ...
    def error(self, msg: str, /, **kwargs: Any) -> None: ...


class NullLogger:
    """
    No-op logger. Useful in tests where logging would be noise, or in
    pure-domain unit tests that exercise calculators directly.
    """

    def info(self, msg: str, /, **kwargs: Any) -> None:
        return None

    def debug(self, msg: str, /, **kwargs: Any) -> None:
        return None

    def warning(self, msg: str, /, **kwargs: Any) -> None:
        return None

    def error(self, msg: str, /, **kwargs: Any) -> None:
        return None


__all__ = ["ILogger", "NullLogger"]
