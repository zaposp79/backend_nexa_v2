"""
nexa_engine/domain/services/servicio_catalogo.py
=================================================
GAP-CTS-ACT-1 / Task 3 — Service-driven behavior model (Excel V2-7).

Single source of truth for the `servicio` (Panel!C5) catalog and ALL
workbook-derived behavior gates. Every entry traces to a workbook cell.
No fabricated mappings.

Workbook evidence
-----------------
Catalog:
  Listas Desplegables!A4:A9 = Cobranzas, SAC, Ventas multicanal, SACO,
                               Plataformas, Captura de Datos

Functional gates keyed on servicio (Panel!C5):

  1. CTS per-channel detail header (C58/C87):
     IF($C$27="SAC", "✓ Habilitado", "— Deshabilitado")
     → habilitado only for "SAC"

  2. Panel!C120 — SACO/Ventas Multicanal section:
     IF(OR(C5="SACO", C5="Ventas Multicanal"), "✓ Habilitado", "— Deshabilitado")
     → habilitado for "SACO" or "Ventas multicanal"

  3. Panel!C152 — Cobranzas billing section:
     IF(C5="Cobranzas", "✓ Habilitado", "— Deshabilitado")
     → habilitado only for "Cobranzas"

  4. Panel!C184 — Captura de Datos section:
     IF(C5="Captura de Datos", "✓ Habilitado", "— Deshabilitado")
     → habilitado only for "Captura de Datos"

  5. Vision Tarifas!C77/D77 — VT special billing rows (SACO/Cobranzas):
     IF(C5="SACO", TRANSPOSE(Panel!C143:G143), IF(C5="Cobranzas",
       TRANSPOSE(Panel!C182:P182), ""))
     → "SACO": uses Panel!C143:G143 (Facturación Variable/Costo Variable)
     → "Cobranzas": uses Panel!C182:P182 (different billing structure)
     → others: "" (empty, no special VT billing row)
     IMPLEMENTATION NOTE: rendering of those rows is UNDETERMINED until input
     contracts for SACO/Cobranzas billing parameters are defined.

  6. Vision Tarifas!C133:
     IF(C5="SACO", Panel!C124, IF(C5="Cobranzas", Panel!C155, 0))
     → service selects a rate/multiplier; same UNDETERMINED caveat.

Non-service dimensions (input-driven, NOT service-driven):
  - Active chains A/B/C: Panel!M17/M30 (cadenas_activas input). No ref to C5.
  - Active channels:     volume Panel!L19:L25 > 0. No ref to C5.
  - Billing model:       EscenarioComercial.modelo_cobro (FTE/Tiempo/etc.)
  - Client type:         Panel!C7 ("Cliente Nuevo") — separate driver
  - FTE/Volume per chan: Panel!M19:M25, L19:L25 — user inputs per channel

Usage pattern:
  behavior = servicio_behavior(panel.linea_negocio)
  cts.canal_view_habilitado = behavior.canal_detail_habilitado
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# Authoritative service catalog — Listas Desplegables!A4:A9 (exact strings).
SERVICIOS_V27 = (
    "Cobranzas",
    "SAC",
    "Ventas multicanal",
    "SACO",
    "Plataformas",
    "Captura de Datos",
)

# ── Gates keyed on each service (cells cited in module docstring) ─────────────

_CANAL_DETAIL_HABILITADO = frozenset({"SAC"})                              # CTS!C58/C87
_SECCION_SACO_VENTAS     = frozenset({"SACO", "Ventas multicanal",         # Panel!C120
                                       "Ventas Multicanal"})
_SECCION_COBRANZAS       = frozenset({"Cobranzas"})                        # Panel!C152
_SECCION_CAPTURA_DATOS   = frozenset({"Captura de Datos"})                 # Panel!C184

VTBillingMode = Literal["SACO", "Cobranzas", "default"]


@dataclass(frozen=True)
class ServicioBehavior:
    """
    All workbook-derived behavioral dimensions for a service.
    Every field is traceable to a specific Excel cell/formula (see module docstring).
    """
    nombre: str
    es_servicio_conocido: bool
    canal_detail_habilitado: bool          # CTS!C58/C87
    seccion_saco_ventas_habilitada: bool   # Panel!C120
    seccion_cobranzas_habilitada: bool     # Panel!C152
    seccion_captura_datos_habilitada: bool  # Panel!C184
    vt_billing_mode: VTBillingMode         # VT!C77/D77/C133 (UNDETERMINED rendering)


def normalizar_servicio(servicio: Optional[str]) -> str:
    return (servicio or "").strip()


def servicio_behavior(servicio: Optional[str]) -> ServicioBehavior:
    """
    Return the full workbook-derived behavior for a service name.
    Unknown services get False/default for all gates — no invented mappings.
    """
    nombre = normalizar_servicio(servicio)
    return ServicioBehavior(
        nombre=nombre,
        es_servicio_conocido             = nombre in SERVICIOS_V27,
        canal_detail_habilitado          = nombre in _CANAL_DETAIL_HABILITADO,
        seccion_saco_ventas_habilitada   = nombre in _SECCION_SACO_VENTAS,
        seccion_cobranzas_habilitada     = nombre in _SECCION_COBRANZAS,
        seccion_captura_datos_habilitada = nombre in _SECCION_CAPTURA_DATOS,
        vt_billing_mode = (
            "SACO"      if nombre == "SACO"      else
            "Cobranzas" if nombre == "Cobranzas" else
            "default"
        ),
    )


def canal_detail_habilitado(servicio: Optional[str]) -> bool:
    """Shorthand: CTS per-channel detail header gate (Excel C58/C87)."""
    return servicio_behavior(servicio).canal_detail_habilitado
