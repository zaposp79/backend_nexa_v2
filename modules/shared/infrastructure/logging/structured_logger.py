"""
infrastructure.logging.structured_logger
========================================

`ILogger` implementation backed by stdlib `logging`. Produces structured
records of the form used across WAVE 5+:

    [PRICING_BUILD] op=... inputs={...} outputs={...} source=...

so existing log scrapers and the canonicalization / audit pipelines keep
working unchanged.
"""

from __future__ import annotations

import logging as _stdlib_logging
from typing import Any

from nexa_engine.modules.shared.ports.logger import ILogger


def _fmt_kwargs(kwargs: dict[str, Any]) -> str:
    if not kwargs:
        return ""
    parts = []
    for k, v in kwargs.items():
        parts.append(f"{k}={v!r}")
    return " " + " ".join(parts)


class StructuredLogger(ILogger):
    """
    Stdlib-backed logger producing the WAVE 5 tag format.

    Args:
        name: logger name (typical: `nexa_engine.application.use_cases.<x>`)
    """

    def __init__(self, name: str = "nexa_engine") -> None:
        self._log = _stdlib_logging.getLogger(name)

    def info(self, msg: str, /, **kwargs: Any) -> None:
        self._log.info("%s%s", msg, _fmt_kwargs(kwargs))

    def debug(self, msg: str, /, **kwargs: Any) -> None:
        self._log.debug("%s%s", msg, _fmt_kwargs(kwargs))

    def warning(self, msg: str, /, **kwargs: Any) -> None:
        self._log.warning("%s%s", msg, _fmt_kwargs(kwargs))

    def error(self, msg: str, /, **kwargs: Any) -> None:
        self._log.error("%s%s", msg, _fmt_kwargs(kwargs))


__all__ = ["StructuredLogger"]
