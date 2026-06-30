"""
nexa_engine/shared/canonicalization.py
======================================
Semantic canonicalization for the V2-7 parametrization layer.

Purpose
-------
Convert user-supplied free-form values (e.g. "S.A.C", "whatsapp", "SUPERVISOR",
"INB", "B") into the **canonical** form expected by the parametrization
storage and the calculators (e.g. "SAC", "WhatsApp", "Supervisor", "Inbound",
"BAJA").

Properties
----------
* **Pure functions**: no I/O, deterministic, side-effect free (except a single
  WARNING log when an alias is missing).
* **Idempotent**: ``canonical_x(canonical_x(s)) == canonical_x(s)``.
* **Non-destructive**: if no alias matches, the *original* input is returned
  unchanged (the calling layer decides whether to raise or accept).
* **Accent / case insensitive** during lookup (NFD normalization, lower-case).

Alias data sources
------------------
1. ``storage/parametrization/v2-7/op.json`` → ``canonicalization_aliases`` block
   (preferred, can be edited without changing code).
2. Built-in fallback maps below.

Public API
----------
* ``canonical_service(s)``        — services (SAC, SACO, Cobranzas, ...)
* ``canonical_channel(s)``        — channels (WhatsApp, Voz, ...)
* ``canonical_role(s)``           — HR roles (Supervisor, GTR, ...)
* ``canonical_modalidad(s)``      — Inbound / Outbound / Blended
* ``canonical_complejidad(s)``    — BAJA / MEDIA / ALTA
* ``reset_alias_cache()``         — for tests
"""

from __future__ import annotations
from nexa_engine.modules.shared.config.config import PARAMETRIZATION_V27_DIR

import json
import logging
import threading
import unicodedata
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── Built-in fallback aliases ────────────────────────────────────────────────
# All keys are normalized (lower, no accents, stripped). Values are the
# canonical form returned to callers.

_SERVICE_ALIASES: Dict[str, str] = {
    # SAC (Servicio al Cliente / Customer Care)
    "sac": "Sac",
    "s.a.c": "Sac",
    "s a c": "Sac",
    "servicio al cliente": "Sac",
    "customer care": "Sac",
    "atencion al cliente": "Sac",
    # SACO (Servicio al Cliente con Oferta / Ventas embebidas)
    "saco": "SACO",
    "s.a.c.o": "SACO",
    "sac+o": "SACO",
    # Ventas multicanal
    "ventas multicanal": "Ventas multicanal",
    "ventas": "Ventas multicanal",
    "ventas multi-canal": "Ventas multicanal",
    "multicanal": "Ventas multicanal",
    # Cobranzas
    "cobranzas": "Cobranzas",
    "cobranza": "Cobranzas",
    "collections": "Cobranzas",
    "recuperaciones": "Cobranzas",
    # Captura de Datos
    "captura de datos": "Captura de Datos",
    "captura datos": "Captura de Datos",
    "data capture": "Captura de Datos",
    "back office": "Captura de Datos",
    "backoffice": "Captura de Datos",
    # Plataformas
    "plataformas": "Plataformas",
    "plataforma": "Plataformas",
    "platforms": "Plataformas",
}

_CHANNEL_ALIASES: Dict[str, str] = {
    "voz": "Voz",
    "voice": "Voz",
    "telefonia": "Voz",
    "phone": "Voz",
    "whatsapp": "WhatsApp",
    "wa": "WhatsApp",
    "whats app": "WhatsApp",
    "whats-app": "WhatsApp",
    "wsp": "WhatsApp",
    "ws": "WhatsApp",
    "correo": "Correo",
    "email": "Correo",
    "mail": "Correo",
    "e-mail": "Correo",
    "webchat": "WebChat",
    "web chat": "WebChat",
    "chat": "WebChat",
    "chat web": "WebChat",
    "ivr": "IVR",
    "mensajes": "Mensajes",
    "sms": "Mensajes",
    "otros": "Otros",
    "other": "Otros",
    "fuerza de ventas": "Fuerza de ventas",
    "fuerza ventas": "Fuerza de ventas",
    "sales force": "Fuerza de ventas",
}

_ROLE_ALIASES: Dict[str, str] = {
    "supervisor": "Supervisor",
    "sup": "Supervisor",
    "sup.": "Supervisor",
    "supervisores": "Supervisor",
    "gtr": "GTR",
    "g.t.r": "GTR",
    "director de cuentas": "Director de cuentas",
    "director cuentas": "Director de cuentas",
    "director de cuenta": "Director de cuentas",
    "account director": "Director de cuentas",
    "formadores": "Formadores",
    "formador": "Formadores",
    "monitor de calidad": "Monitor de Calidad",
    "monitor calidad": "Monitor de Calidad",
    "qa": "Monitor de Calidad",
    "validador": "Validador",
    "jefe de operacion": "Jefe de Operación",
    "jefe operacion": "Jefe de Operación",
    "jefe de operación": "Jefe de Operación",
    "agente basico 1": "Agente Básico 1",
    "agente básico 1": "Agente Básico 1",
    "agente": "Agente Básico 1",
    "aprendiz sena": "Aprendiz SENA",
    "aprendiz": "Aprendiz SENA",
    "inclusion": "Inclusión",
    "inclusión": "Inclusión",
    "especialista de proyectos": "Especialista de Proyectos",
    "especialista proyectos": "Especialista de Proyectos",
}

_MODALIDAD_ALIASES: Dict[str, str] = {
    "inbound": "Inbound",
    "inb": "Inbound",
    "in": "Inbound",
    "entrante": "Inbound",
    "outbound": "Outbound",
    "out": "Outbound",
    "outb": "Outbound",
    "saliente": "Outbound",
    "blended": "Blended",
    "bld": "Blended",
    "mixto": "Blended",
    "mixed": "Blended",
}

_COMPLEJIDAD_ALIASES: Dict[str, str] = {
    "baja": "BAJA",
    "b": "BAJA",
    "low": "BAJA",
    "media": "MEDIA",
    "m": "MEDIA",
    "med": "MEDIA",
    "medium": "MEDIA",
    "alta": "ALTA",
    "a": "ALTA",
    "high": "ALTA",
}

# ── Cached overlay from storage ──────────────────────────────────────────────

_CACHE_LOCK = threading.Lock()
_LOADED: bool = False
_OVERLAY: Dict[str, Dict[str, str]] = {}

_V27_OP_PATH = (
    # refactor modular-pure: pasó de shared/ (1 nivel) a modules/shared/ (2 niveles);
    # +1 .parent para resolver al MISMO backend_nexa/storage/ — sin cambio de lógica.
    PARAMETRIZATION_V27_DIR
    / "op.json"
)


def _load_overlay() -> None:
    """Load ``canonicalization_aliases`` from op.json if present (lazy)."""
    global _LOADED, _OVERLAY
    with _CACHE_LOCK:
        if _LOADED:
            return
        _LOADED = True
        try:
            if _V27_OP_PATH.exists():
                with open(_V27_OP_PATH, encoding="utf-8") as f:
                    doc = json.load(f)
                aliases = doc.get("canonicalization_aliases") or {}
                # Normalize keys
                clean: Dict[str, Dict[str, str]] = {}
                for dim, mapping in aliases.items():
                    if not isinstance(mapping, dict):
                        continue
                    clean[dim] = {_norm_key(k): v for k, v in mapping.items()}
                _OVERLAY = clean
                if clean:
                    logger.info(
                        "[CANONICALIZATION] Loaded overlay aliases from op.json: dims=%s",
                        list(clean.keys()),
                    )
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[CANONICALIZATION] Could not load op.json overlay: %s", exc)
            _OVERLAY = {}


def reset_alias_cache() -> None:
    """Reset the lazy-loaded overlay cache (used by tests)."""
    global _LOADED, _OVERLAY
    with _CACHE_LOCK:
        _LOADED = False
        _OVERLAY = {}


# ── Core helpers ─────────────────────────────────────────────────────────────


def _strip_accents(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _norm_key(s: str) -> str:
    if s is None:
        return ""
    return _strip_accents(str(s).strip().lower())


def _canonicalize(value: object, dimension: str, builtin: Dict[str, str]) -> str:
    """Generic dispatcher: overlay first, then built-in, else passthrough."""
    if value is None:
        return ""
    s = str(value)
    if not s.strip():
        return s
    _load_overlay()
    key = _norm_key(s)
    # 1. Overlay from storage (op.json)
    overlay = _OVERLAY.get(dimension, {})
    if key in overlay:
        return overlay[key]
    # 2. Built-in
    if key in builtin:
        return builtin[key]
    # 3. Passthrough with WARNING
    logger.warning(
        "[CANONICALIZATION] No alias for dimension=%s value=%r; returning input unchanged",
        dimension, s,
    )
    return s


# ── Public API ───────────────────────────────────────────────────────────────


def canonical_service(s: object) -> str:
    """Canonicalize a service name (SAC, SACO, Cobranzas, ...)."""
    return _canonicalize(s, "services", _SERVICE_ALIASES)


def canonical_channel(s: object) -> str:
    """Canonicalize a channel name (Voz, WhatsApp, Correo, ...)."""
    return _canonicalize(s, "channels", _CHANNEL_ALIASES)


def canonical_role(s: object) -> str:
    """Canonicalize an HR role (Supervisor, GTR, ...)."""
    return _canonicalize(s, "roles", _ROLE_ALIASES)


def canonical_modalidad(s: object) -> str:
    """Canonicalize a modalidad (Inbound / Outbound / Blended)."""
    return _canonicalize(s, "modalidad", _MODALIDAD_ALIASES)


def canonical_complejidad(s: object) -> str:
    """Canonicalize a complejidad (BAJA / MEDIA / ALTA)."""
    return _canonicalize(s, "complejidad", _COMPLEJIDAD_ALIASES)


def canonicalize_linea(s: object) -> str:
    """Alias for :func:`canonical_service`. Used by parametrization provider
    where the parameter is named ``linea_negocio`` but maps to a service."""
    return canonical_service(s)


__all__ = [
    "canonical_service",
    "canonical_channel",
    "canonical_role",
    "canonical_modalidad",
    "canonical_complejidad",
    "canonicalize_linea",
    "reset_alias_cache",
]
