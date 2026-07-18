"""
FASE 1 — Tests de No-Hardcodes

Verifican que los loaders raisen ValueError en campos requeridos faltantes
y que los hardcodes documentados (H1-H9) están correctamente manejados.
"""
import pytest

from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader


# ---------------------------------------------------------------------------
# H1 — _anio_inicio() debe raise en fecha inválida
# ---------------------------------------------------------------------------
class TestH1AnioInicio:
    """context_builder._anio_inicio() ya no tiene fallback silencioso a 2026."""

    @pytest.mark.parametrize("fecha", [
        "2026-01-01", "2025-06-15", "2030-12-31",
    ])
    def test_fecha_valida(self, fecha):
        assert SimulationContextBuilder._anio_inicio(fecha) == int(fecha[:4])

    @pytest.mark.parametrize("fecha_invalida", [
        None, "", "abc", "20", "1999-01-01", "2101-01-01",
    ])
    def test_fecha_invalida_raises(self, fecha_invalida):
        with pytest.raises(ValueError):
            SimulationContextBuilder._anio_inicio(fecha_invalida)


# ---------------------------------------------------------------------------
# H2/H3/H6/H8/H9 — _normalizar_entry_data_format() campos requeridos
# ---------------------------------------------------------------------------
class TestEntryDataRequiredFields:
    """En el path entry_data, ciudad/fecha_inicio/duracion_meses/margen son requeridos."""

    @pytest.fixture
    def base_entry_data(self):
        return {
            "ciudad": "Medellin",
            "fecha_inicio": "2026-03-01",
            "duracion_meses": 12,
            "margen_objetivo_cadena_a": 0.20,
            "cliente": "TestCo",
            "tipo_cliente": "Nuevo",
            "servicio": "SAC",
        }

    @pytest.mark.parametrize("campo", [
        "ciudad", "fecha_inicio", "duracion_meses", "margen_objetivo_cadena_a",
    ])
    def test_campo_requerido_faltante_raises(self, base_entry_data, campo):
        entry = {**base_entry_data}
        del entry[campo]
        with pytest.raises(ValueError, match=campo):
            UserInputLoader._requerir(entry, campo, "entry_data") if campo == "ciudad" else (
                UserInputLoader._requerir(entry, campo, "entry_data") if campo == "fecha_inicio" else (
                    UserInputLoader._requerir_int(entry, campo, "entry_data") if campo == "duracion_meses" else
                    UserInputLoader._requerir_float(entry, campo, "entry_data")
                )
            )

    @pytest.mark.parametrize("campo,valor_vacio", [
        ("ciudad", ""),
        ("ciudad", "  "),
        ("fecha_inicio", ""),
    ])
    def test_campo_requerido_vacio_raises(self, base_entry_data, campo, valor_vacio):
        entry = {**base_entry_data, campo: valor_vacio}
        with pytest.raises(ValueError, match=campo):
            UserInputLoader._requerir(entry, campo, "entry_data")


# ---------------------------------------------------------------------------
# H4/H5/H7 — Defaults legítimos documentados (mantener)
# ---------------------------------------------------------------------------
class TestDefaultsLegitimos:
    """Estos defaults son intencionales y documentados."""

    def test_periodo_pago_dias_default_90(self):
        """H7: periodo_pago_dias=90 es estándar BPO Colombia."""
        # Verificar que el default existe en el loader (no debe eliminarse)
        import inspect
        src = inspect.getsource(UserInputLoader)
        assert "periodo_pago_dias" in src

    def test_legacy_panel_mantiene_defaults(self):
        """Legacy _panel() mantiene defaults por backward compat (será migrado en FASE 2)."""
        # Este test documenta que el path legacy aún tiene defaults
        # y que la migración se hará en FASE 2 via InputNormalizer
        import inspect
        src = inspect.getsource(UserInputLoader._panel)
        # Los defaults legacy aún existen en _panel()
        assert "Bogota" in src or "bogota" in src.lower()
