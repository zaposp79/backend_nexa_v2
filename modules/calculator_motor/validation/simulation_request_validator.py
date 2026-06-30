"""
nexa_engine/validators/simulation_request_validator.py
======================================================
Business-rule validation for ``SimulationRequest`` at the API boundary.

Validates structural correctness and domain constraints BEFORE the request
enters the pricing pipeline. This catches errors early and returns actionable
messages to the caller.

Does NOT modify any financial formula, math result, or pipeline behavior.
All checks are read-only assertions on the request payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from nexa_engine.modules.calculator_motor.dto.request_dto import SimulationRequest


@dataclass
class ValidationResult:
    """Validation outcome with blocking errors and informational warnings."""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Derived / output-only fields that must NOT appear in a request
# ---------------------------------------------------------------------------

_DERIVED_PROFILE_FIELDS = {
    "no_payroll_mensual",
    "cadena_b_mensual",
    "costos_financieros_mensual",
}

_VALID_MODALIDADES = {"Inbound", "Outbound"}
_VALID_MODELOS_COBRO = {"Fijo FTE", "Híbrido", "Variable"}


class SimulationRequestValidator:
    """
    Validates a ``SimulationRequest`` against business rules.

    Usage::

        result = SimulationRequestValidator().validate(request)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
    """

    def validate(self, req: SimulationRequest) -> ValidationResult:
        result = ValidationResult()
        self._validate_panel(req, result)
        self._validate_cadena_a(req, result)
        self._validate_cadena_b(req, result)
        self._validate_cadena_c(req, result)
        return result

    # ── Panel ─────────────────────────────────────────────────────

    def _validate_panel(self, req: SimulationRequest, r: ValidationResult) -> None:
        p = req.panel_de_control

        if not p.linea_negocio.strip():
            r.errors.append("panel_de_control.linea_negocio is required")

        if not p.fecha_inicio.strip():
            r.errors.append("panel_de_control.fecha_inicio is required")

        if p.meses_contrato <= 0:
            r.errors.append(
                f"panel_de_control.meses_contrato must be > 0, got {p.meses_contrato}"
            )

        if not p.ciudad.strip():
            r.warnings.append(
                "panel_de_control.ciudad is empty — ICA will use default rate"
            )

        if p.margen < 0:
            r.warnings.append(
                f"panel_de_control.margen is negative ({p.margen})"
            )

        if p.op_cont < 0:
            r.errors.append(
                f"panel_de_control.op_cont must be >= 0, got {p.op_cont}"
            )

        if p.periodo_pago_dias <= 0:
            r.errors.append(
                f"panel_de_control.periodo_pago_dias must be > 0, got {p.periodo_pago_dias}"
            )

    # ── Cadena A ──────────────────────────────────────────────────

    def _validate_cadena_a(self, req: SimulationRequest, r: ValidationResult) -> None:
        for i, perfil in enumerate(req.condiciones_cadena_a.perfiles):
            prefix = f"condiciones_cadena_a.perfiles[{i}]"

            if perfil.fte <= 0:
                r.errors.append(f"{prefix}.fte must be > 0, got {perfil.fte}")

            if perfil.modalidad not in _VALID_MODALIDADES:
                r.warnings.append(
                    f"{prefix}.modalidad '{perfil.modalidad}' not in {_VALID_MODALIDADES}"
                )

            if not (0 <= perfil.pct_presencia <= 1.0):
                r.warnings.append(
                    f"{prefix}.pct_presencia should be in [0, 1], got {perfil.pct_presencia}"
                )

            if perfil.modelo_cobro not in _VALID_MODELOS_COBRO:
                r.warnings.append(
                    f"{prefix}.modelo_cobro '{perfil.modelo_cobro}' not in {_VALID_MODELOS_COBRO}"
                )

    # ── Cadena B ──────────────────────────────────────────────────

    def _validate_cadena_b(self, req: SimulationRequest, r: ValidationResult) -> None:
        cb = req.condiciones_cadena_b

        for i, canal in enumerate(cb.canales):
            prefix = f"condiciones_cadena_b.canales[{i}]"
            if canal.volumen_mensual < 0:
                r.errors.append(
                    f"{prefix}.volumen_mensual must be >= 0, got {canal.volumen_mensual}"
                )

        for i, item in enumerate(cb.opex_consumo_variable):
            prefix = f"condiciones_cadena_b.opex_consumo_variable[{i}]"
            if item.valor_unitario < 0:
                r.warnings.append(f"{prefix}.valor_unitario is negative ({item.valor_unitario})")

        for i, m in enumerate(cb.equipo_sm):
            prefix = f"condiciones_cadena_b.equipo_sm[{i}]"
            if m.pct_dedicacion < 0 or m.pct_dedicacion > 1.0:
                r.warnings.append(
                    f"{prefix}.pct_dedicacion should be in [0, 1], got {m.pct_dedicacion}"
                )

        for i, d in enumerate(cb.dispositivos_sm):
            prefix = f"condiciones_cadena_b.dispositivos_sm[{i}]"
            if d.costo_unitario < 0:
                r.warnings.append(f"{prefix}.costo_unitario is negative ({d.costo_unitario})")
            if d.meses_amortizacion <= 0:
                r.errors.append(
                    f"{prefix}.meses_amortizacion must be > 0, got {d.meses_amortizacion}"
                )

    # ── Cadena C ──────────────────────────────────────────────────

    def _validate_cadena_c(self, req: SimulationRequest, r: ValidationResult) -> None:
        cc = req.condiciones_cadena_c

        for i, canal in enumerate(cc.canales):
            prefix = f"condiciones_cadena_c.canales[{i}]"
            if canal.volumen_mensual < 0:
                r.errors.append(
                    f"{prefix}.volumen_mensual must be >= 0, got {canal.volumen_mensual}"
                )

        for i, m in enumerate(cc.equipo_transversal):
            prefix = f"condiciones_cadena_c.equipo_transversal[{i}]"
            if m.pct_dedicacion < 0 or m.pct_dedicacion > 1.0:
                r.warnings.append(
                    f"{prefix}.pct_dedicacion should be in [0, 1], got {m.pct_dedicacion}"
                )

        if cc.inversion_anual < 0:
            r.warnings.append(
                f"condiciones_cadena_c.inversion_anual is negative ({cc.inversion_anual})"
            )
