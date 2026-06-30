"""
nexa_engine/simulation/request_dto.py
======================================
Canonical API request model for the NEXA pricing engine.

Replaces the untyped ``Dict[str, Any]`` in ``CalculationRequest`` with a
fully validated Pydantic model that mirrors the domain ``UserInput`` structure.

Two entry formats are accepted (via UserInputLoader):
  1. **Domain format** (test fixtures): ``panel_de_control``, ``condiciones_cadena_a/b/c``
  2. **Frontend format**: ``pcg``, ``cdcA``, ``cdcB``, ``cdcC``

This module defines the typed wrapper for format #1.  Format #2 continues
to flow through ``UnifiedInputAdapter.from_frontend()`` unchanged.

Fields starting with ``_`` (metadata/documentation) are silently stripped.
Fields belonging to master data (``parametros_nomina``, etc.) are rejected.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


# ---------------------------------------------------------------------------
# Sub-models — Panel de Control
# ---------------------------------------------------------------------------

class PanelDeControlRequest(BaseModel):
    """Panel de Control section of the simulation request."""
    model_config = ConfigDict(extra="forbid")

    cliente: str = ""
    tipo_cliente: str = ""
    linea_negocio: str = ""
    ciudad: str = ""
    sede: str = ""
    fecha_inicio: str = ""
    meses_contrato: int = 12
    margen: float = 0.0
    op_cont: float = 0.0
    com_cont: float = 0.0
    markup: float = 0.0
    descuento: float = 0.0
    periodo_pago_dias: int = 90
    activa_financiacion: bool = True
    antiguedad_cliente: str = ""
    componente_indexacion_humano: str = "IPC"
    componente_indexacion_tecnologico: str = "IPC"
    tasa_ica: Optional[float] = None
    tasa_gmf: Optional[float] = None
    tasa_mensual_financ: Optional[float] = None
    pct_rotacion: Optional[float] = None
    pct_ausentismo: Optional[float] = None
    aplica_ley_1819: bool = True  # DESACTIVADO — retenido para compat; valor ignorado

    # ── WAVE 2 (Excel V2-7) — campos formalizados desde Panel ───────────
    # Defaults se resuelven desde `op.v2_7_defaults` cuando se omiten en el request.
    margen_b: Optional[float] = None              # Panel!D63 — default 0.30
    margen_c: Optional[float] = None              # Panel!E63 — default 0.20
    mes_ajuste_indexacion: Optional[int] = None   # Panel!L9 — default 6 (rango 1..12)
    tasa_interes_mensual: Optional[float] = None  # Panel!L10 — default 0.0153 (rango 0..1)
    imprevistos: Optional[float] = None           # Panel!C73 — default 0.0 (rango 0..1)

    @field_validator("margen_b", "margen_c", "tasa_interes_mensual", "imprevistos")
    @classmethod
    def _check_unit_range(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not (0.0 <= float(v) <= 1.0):
            raise ValueError("must be between 0 and 1")
        return v

    @field_validator("mes_ajuste_indexacion")
    @classmethod
    def _check_month(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not (1 <= int(v) <= 12):
            raise ValueError("mes_ajuste_indexacion must be between 1 and 12")
        return v


# ---------------------------------------------------------------------------
# Sub-models — Cadena A
# ---------------------------------------------------------------------------

class PerfilCadenaARequest(BaseModel):
    """A single operator profile in Cadena A."""
    model_config = ConfigDict(extra="allow")  # tolerate _comment, _k50_contrib

    nombre: str = ""
    rol: str = "Agente Basico"
    canal: str = ""
    modalidad: str = "Inbound"
    fte: float = 0.0
    pct_presencia: float = 1.0
    comision_pct: float = 0.0
    salario_base: Optional[float] = None
    incluye_examenes: bool = True
    incluye_seguridad: bool = False
    dias_cap_inicial: int = 10
    dias_cap_rotacion: int = 10
    tmo_segundos: float = 0.0
    modelo_cobro: str = "Fijo FTE"
    pct_fijo: float = 1.0
    vol_cadena_a_mensual: float = 0.0


class CondicionesCadenaARequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    perfiles: List[PerfilCadenaARequest] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sub-models — Cadena B
# ---------------------------------------------------------------------------

class CanalCadenaBRequest(BaseModel):
    model_config = ConfigDict(extra="allow")  # tolerate _comment, _l_contribution

    nombre: str = ""
    modalidad: str = ""
    producto: str = ""
    volumen_mensual: float = 0.0
    activo: bool = True
    opex_fijo: float = 0.0
    tarifa_unitaria: float = 0.0
    pct_escalamiento: float = 0.0
    costo_escalamiento: float = 0.0


class ItemOpexConsumoRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    nombre: str = ""
    producto: str = ""
    modalidad: str = ""
    canal: str = ""
    valor_unitario: float = 0.0
    cantidad: float = 0.0
    tipo_cobro: str = "Unitario"


class MiembroEquipoSMRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    rol: str = ""
    activo: bool = True
    pct_dedicacion: float = 0.0


class DispositivoSMRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    tipo: str = ""
    costo_unitario: float = 0.0
    cantidad: float = 0.0
    meses_amortizacion: int = 1


class CondicionesCadenaBRequest(BaseModel):
    model_config = ConfigDict(extra="allow")  # tolerate _comment, _l50_derivation

    canales: List[CanalCadenaBRequest] = Field(default_factory=list)
    opex_consumo_variable: List[ItemOpexConsumoRequest] = Field(default_factory=list)
    equipo_sm: List[MiembroEquipoSMRequest] = Field(default_factory=list)
    dispositivos_sm: List[DispositivoSMRequest] = Field(default_factory=list)
    inversion_plataforma: float = 0.0
    fte_equipo_sm: float = 1.0
    amortizar_dispositivos_sm: bool = True


# ---------------------------------------------------------------------------
# Sub-models — Cadena C
# ---------------------------------------------------------------------------

class CanalCadenaCRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    nombre: str = ""
    modalidad: str = ""
    volumen_mensual: float = 0.0
    activo: bool = True
    opex_fijo_integ: float = 0.0
    opex_var_integ: float = 0.0
    pct_escalamiento: float = 0.0
    costo_escalamiento: float = 0.0


class MiembroEquipoTransversalRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    rol: str = ""
    activo: bool = True
    pct_dedicacion: float = 0.0


class CondicionesCadenaCRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    canales: List[CanalCadenaCRequest] = Field(default_factory=list)
    equipo_transversal: List[MiembroEquipoTransversalRequest] = Field(default_factory=list)
    inversion_anual: float = 0.0


# ---------------------------------------------------------------------------
# Root request model
# ---------------------------------------------------------------------------

# Fields that belong to master data / parametrization — NEVER in a request.
_FORBIDDEN_KEYS = {
    "parametros_nomina",
    "parametros_no_payroll",
    "parametros_calculo",
    "parametros_cadena_b",
    "parametros_cadena_c",
    "horas_formacion_mensual",
    "perfiles_cadena_a",      # legacy domain format — use condiciones_cadena_a
}


class SimulationRequest(BaseModel):
    """
    Canonical typed request for ``POST /api/v1/simulation/calculate``.

    Sections:
      - ``panel_de_control`` — **required**
      - ``condiciones_cadena_a`` — optional, defaults to empty
      - ``condiciones_cadena_b`` — optional, defaults to empty
      - ``condiciones_cadena_c`` — optional, defaults to empty

    Fields starting with ``_`` are silently stripped (test metadata).
    Master-data fields (``parametros_nomina``, etc.) cause a validation error.
    """
    model_config = ConfigDict(extra="allow")  # tolerate _comment, _scenario, validaciones

    panel_de_control: PanelDeControlRequest
    condiciones_cadena_a: CondicionesCadenaARequest = Field(
        default_factory=CondicionesCadenaARequest,
    )
    condiciones_cadena_b: CondicionesCadenaBRequest = Field(
        default_factory=CondicionesCadenaBRequest,
    )
    condiciones_cadena_c: CondicionesCadenaCRequest = Field(
        default_factory=CondicionesCadenaCRequest,
    )

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_keys(cls, data: Any) -> Any:
        """Reject master-data / legacy-format keys at parse time."""
        if isinstance(data, dict):
            found = _FORBIDDEN_KEYS & set(data.keys())
            if found:
                raise ValueError(
                    f"Request must not contain master-data or legacy fields: "
                    f"{', '.join(sorted(found))}. "
                    f"These are resolved from the active parametrization."
                )
        return data

    def to_loader_dict(self) -> Dict[str, Any]:
        """
        Convert to the dict format that ``UserInputLoader.cargar_desde_dict()``
        expects, stripping metadata keys.

        This bridges the typed DTO to the existing loading pipeline without
        modifying any financial logic.
        """
        raw = self.model_dump(exclude_none=False)
        # Strip _-prefixed metadata at every level
        return _strip_metadata(raw)


def _strip_metadata(obj: Any) -> Any:
    """Recursively remove keys starting with ``_`` from dicts.

    Also removes keys with ``None`` values to avoid confusing downstream
    loaders that check ``if key in d`` (e.g., UserInputLoader._perfil_a
    would call ``float(None)`` if salario_base is present but None).
    """
    if isinstance(obj, dict):
        return {
            k: _strip_metadata(v)
            for k, v in obj.items()
            if not k.startswith("_") and v is not None
        }
    if isinstance(obj, list):
        return [_strip_metadata(item) for item in obj]
    return obj
