"""
Unit tests for ENGINE_MEDIUM_RISK_FIXES_01:
  Fix 1 — Silent ParametrizationError swallowed in context_builder_panel_mixin
  Fix 2 — Hardcoded salary 1423000 in volumetry fallback of user_input_loader
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from nexa_engine.modules.shared.exceptions import DomainError, ParametrizationError


# ── Fix 1: provider fallback must NOT be swallowed ──────────────────────────

class _StubPanel:
    """Minimal panel stub — all optional fields set to None so provider fallback is exercised."""
    tasa_ica = None
    tasa_gmf = None
    tasa_mensual_financ = None
    tasa_interes_mensual = None
    pct_ausentismo = None
    margen_b = None
    margen_c = None
    mes_ajuste_indexacion = None
    cliente = "TestClient"
    tipo_cliente = "SMALL"
    fecha_inicio = "2026-01-01"
    meses_contrato = 12
    margen = 0.21
    op_cont = 0.05
    com_cont = 0.03
    markup = 0.0
    descuento = 0.0
    activa_financiacion = True
    periodo_pago_dias = 90
    sede = "Bogotá"
    antiguedad_cliente = 1
    horas_formacion_mensual = 0
    componente_indexacion_humano = "IPC"
    componente_indexacion_tecnologico = "IPC"
    indexacion_frecuencia = "Anual"
    indexacion_mes_aplicacion = None
    imprevistos = 0.0


def _make_failing_provider():
    """Provider whose get_v27_defaults() raises RuntimeError (simulates storage failure)."""
    prov = MagicMock()
    prov.get_ica.return_value = 0.005
    prov.get_gmf.return_value = 0.004
    prov.tasa_mensual_financiacion.return_value = 0.0088
    prov.get_pct_ausentismo.return_value = 0.05
    prov.get_v27_defaults.side_effect = RuntimeError("OP storage unavailable")
    return prov


def test_provider_failure_in_get_v27_defaults_raises_parametrization_error():
    """get_v27_defaults() failure must propagate as ParametrizationError, not be silenced."""
    from nexa_engine.modules.calculator_motor.mixins.context_builder_panel_mixin import (
        ContextBuilderPanelMixin,
    )

    class _Stub(ContextBuilderPanelMixin):
        pass

    stub = _Stub.__new__(_Stub)
    stub._prov = _make_failing_provider()

    with pytest.raises(ParametrizationError) as exc_info:
        stub._construir_panel(_StubPanel(), ciudad="Bogotá", linea="SAC")

    assert "OP" in str(exc_info.value.message) or "get_v27_defaults" in str(exc_info.value.message)
    assert exc_info.value.module == "OP"
    # Original cause must be chained
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_provider_failure_is_not_swallowed_as_empty_defaults():
    """After Fix 1, engine must NOT silently continue with margen_b=0.30 when provider fails."""
    from nexa_engine.modules.calculator_motor.mixins.context_builder_panel_mixin import (
        ContextBuilderPanelMixin,
    )

    class _Stub(ContextBuilderPanelMixin):
        pass

    stub = _Stub.__new__(_Stub)
    stub._prov = _make_failing_provider()

    # Must raise, NOT return a PanelDeControl with hardcoded defaults
    with pytest.raises(ParametrizationError):
        stub._construir_panel(_StubPanel(), ciudad="Bogotá", linea="SAC")


def test_provider_success_does_not_raise():
    """When provider.get_v27_defaults() succeeds, no ParametrizationError is raised (no regression)."""
    from nexa_engine.modules.calculator_motor.mixins.context_builder_panel_mixin import (
        ContextBuilderPanelMixin,
    )

    class _Stub(ContextBuilderPanelMixin):
        pass

    prov = MagicMock()
    prov.get_ica.return_value = 0.005
    prov.get_gmf.return_value = 0.004
    prov.tasa_mensual_financiacion.return_value = 0.0088
    prov.get_pct_ausentismo.return_value = 0.05
    prov.get_v27_defaults.return_value = {
        "margenes": {"margen_b_default": 0.30, "margen_c_default": 0.20},
        "indexacion": {"mes_ajuste": 6, "tasa_interes_mensual": 0.0153},
    }

    stub = _Stub.__new__(_Stub)
    stub._prov = prov

    # Use a MagicMock panel — all attributes auto-return MagicMock (pass-through check only)
    panel = MagicMock()
    panel.tasa_mensual_financ = None
    panel.tasa_interes_mensual = None
    panel.pct_ausentismo = None
    panel.tasa_ica = None
    panel.tasa_gmf = None
    panel.margen_b = 0.30   # panel provides value — provider fallback not needed
    panel.margen_c = 0.20
    panel.mes_ajuste_indexacion = 6

    # Should not raise — provider is healthy
    try:
        stub._construir_panel(panel, ciudad="Bogotá", linea="SAC")
    except ParametrizationError:
        pytest.fail("ParametrizationError raised unexpectedly when provider is healthy")
    except Exception:
        pass  # Other exceptions from MagicMock fields are acceptable in this stub context


# ── Fix 2: hardcoded salary 1423000 must not be silently used ────────────────

def _volumetry_data_without_salario(canal: str = "Chat") -> dict:
    """Entry data that has volumetry but NO condiciones_cadena_a (triggers the fallback path)."""
    return {
        "datos_operativos": {
            "ciudad": "Bogotá",
            "sede": "Bogotá",
            "fecha_inicio": "2026-01-01",
            "duracion_meses": 12,
            "servicio": "SAC",
            "cliente": "TestClient",
            "tipo_cliente": "SMALL",
            # salario_base_default intentionally absent
        },
        "reglas_negocio": {
            "margen_objetivo_cadena_a": 0.21,
        },
        "volumetria": {
            "inbound": {
                "canales": [{"canal": canal, "cadena_a": {"valor": 5}}]
            },
            "outbound": {"canales": []},
            "indexacion": {"frecuencia": "Anual"},
        },
        # condiciones_cadena_a NOT present → triggers else branch with salary lookup
    }


def _volumetry_data_with_salario(canal: str = "Chat", salary: float = 1800000.0) -> dict:
    """Entry data with volumetry and explicit salario_base_default in datos_operativos."""
    data = _volumetry_data_without_salario(canal)
    data["datos_operativos"]["salario_base_default"] = salary
    return data


def test_volumetry_path_without_salario_raises_domain_error():
    """Volumetry fallback must raise DomainError when salario_base_default is missing."""
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

    data = _volumetry_data_without_salario()
    with pytest.raises(DomainError) as exc_info:
        UserInputLoader._normalizar_entry_data_format(data)

    assert "salario_base_default" in str(exc_info.value.message)
    assert "hardcodeado" in str(exc_info.value.message)


def test_volumetry_path_with_salario_uses_provided_value():
    """When salario_base_default is in datos_operativos, it must be used (no hardcode)."""
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

    data = _volumetry_data_with_salario(salary=1800000.0)
    result = UserInputLoader._normalizar_entry_data_format(data)

    perfiles = result.get("condiciones_cadena_a", {}).get("perfiles", [])
    assert len(perfiles) >= 1, "debe haber al menos un perfil Inbound"
    for p in perfiles:
        assert p["salario_base"] == pytest.approx(1800000.0), (
            f"perfil {p['nombre']}: salario_base debe ser 1800000 (del request), no 1423000"
        )


def test_volumetry_path_never_uses_1423000_silently():
    """The literal 1423000 must never appear as a salary when salario_base_default is absent."""
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

    data = _volumetry_data_without_salario()
    try:
        result = UserInputLoader._normalizar_entry_data_format(data)
        perfiles = result.get("condiciones_cadena_a", {}).get("perfiles", [])
        for p in perfiles:
            assert p.get("salario_base") != 1423000, (
                "1423000 must never be silently used as default salary"
            )
    except DomainError:
        pass  # raised correctly — the fix works
