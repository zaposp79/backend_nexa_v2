"""
tests/integration/test_full_traceability.py
============================================
FASE 7 — Pruebas de trazabilidad financiera completa.

Verifica que el AuditTracer captura entradas de todos los calculadores
del pipeline: nómina, no_payroll, cadena_b, cadena_c, costos_financieros,
pyg (ingreso) y kpis.

Principio: cada valor financiero no-cero debe tener al menos una entrada
de trace que lo documente.
"""

import json
import pytest
import sys
from pathlib import Path

# WAVE 7: marcado como legacy pre-V2-7 — usa fixtures sin cadenas_activas (TASK_3).
# Audit trace formato antiguo — se reescribirá en WAVE 10 (lineage).
# Ver docs/v27/WAVE7_TRIAGE.md (LEGACY_TRACEABILITY).
pytestmark = pytest.mark.legacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider


# ---------------------------------------------------------------------------
# Fixture: motor completo con trace activado
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def resultado_con_trace():
    """
    Ejecuta el motor con bancamia_whatsapp_only.json y retorna
    (resultado, audit_trace_dict).
    """
    test_case = PROJECT_ROOT / "backend_nexa" / "test_cases" / "input" / "bancamia_whatsapp_only.json"
    raw = json.loads(test_case.read_text())

    loader   = UserInputLoader()
    user_input = loader.cargar_desde_dict(raw)
    provider = ParametrizationProvider.build()
    builder  = SimulationContextBuilder(provider)
    solicitud = builder.construir(user_input)

    engine   = NexaPricingEngine(parametrizacion=provider)
    resultado = engine.calcular(solicitud)

    return resultado, resultado.audit_trace


@pytest.fixture(scope="module")
def audit_trace(resultado_con_trace):
    _, trace = resultado_con_trace
    return trace


# ---------------------------------------------------------------------------
# Test: audit_trace existe y es válido
# ---------------------------------------------------------------------------

class TestAuditTracePresence:

    def test_audit_trace_no_none(self, audit_trace):
        """PricingResult.audit_trace debe ser producido por el motor."""
        assert audit_trace is not None, "PricingResult.audit_trace es None"

    def test_audit_trace_es_dict(self, audit_trace):
        assert isinstance(audit_trace, dict)

    def test_audit_trace_tiene_entries(self, audit_trace):
        entries = audit_trace.get("entries", [])
        assert len(entries) > 0, "audit_trace sin entradas"

    def test_audit_trace_json_serializable(self, audit_trace):
        json_str = json.dumps(audit_trace, default=str)
        assert len(json_str) > 100


# ---------------------------------------------------------------------------
# Test: Cobertura de componentes
# ---------------------------------------------------------------------------

class TestAuditTraceComponentCoverage:
    """Verifica que cada calculador del pipeline generó al menos 1 entrada."""

    def _get_components(self, audit_trace):
        entries = audit_trace.get("entries", [])
        return {e.get("component", "") for e in entries}

    def test_trace_cubre_payroll(self, audit_trace):
        """NominaCalculator debe generar entradas de trace (ya estaba)."""
        components = self._get_components(audit_trace)
        payroll_components = {c for c in components if "payroll" in c.lower()}
        assert payroll_components, f"No hay trace de payroll. Componentes: {components}"

    def test_trace_cubre_no_payroll(self, audit_trace):
        """NoPayrollCalculator debe generar entradas de trace (FASE 7)."""
        components = self._get_components(audit_trace)
        assert "no_payroll" in components, f"no_payroll no encontrado. Componentes: {components}"

    def test_trace_cubre_cadena_b(self, audit_trace):
        """CadenaBCalculator debe generar entradas de trace (FASE 7)."""
        components = self._get_components(audit_trace)
        assert "cadena_b" in components, f"cadena_b no encontrado. Componentes: {components}"

    def test_trace_cubre_costos_financieros(self, audit_trace):
        """CostosFinancierosCalculator debe generar entradas (ya estaba)."""
        components = self._get_components(audit_trace)
        financiero = {c for c in components if "financier" in c.lower() or "poliz" in c.lower() or "ica" in c.lower()}
        assert financiero, f"No hay trace de costos financieros. Componentes: {components}"

    def test_trace_cubre_pyg_ingreso(self, audit_trace):
        """PyGCalculator debe generar entradas de ingreso (FASE 7)."""
        components = self._get_components(audit_trace)
        assert "pyg.ingreso" in components, f"pyg.ingreso no encontrado. Componentes: {components}"

    def test_trace_cubre_kpis(self, audit_trace):
        """KPIsCalculator debe generar entradas de trace (FASE 7)."""
        components = self._get_components(audit_trace)
        assert "kpis" in components, f"kpis no encontrado. Componentes: {components}"


# ---------------------------------------------------------------------------
# Test: Estructura de cada entrada
# ---------------------------------------------------------------------------

class TestAuditTraceEntryStructure:

    def test_entries_tienen_campos_requeridos(self, audit_trace):
        """Cada entrada debe tener component, rule, formula, inputs, result."""
        entries = audit_trace.get("entries", [])
        campos_requeridos = ["component", "rule", "formula", "inputs", "result"]
        for i, entry in enumerate(entries[:5]):  # Verificar las primeras 5
            for campo in campos_requeridos:
                assert campo in entry, f"Entrada {i} sin campo '{campo}': {entry.get('component', '?')}"

    def test_entries_result_es_numerico(self, audit_trace):
        """El campo result de cada entrada debe ser un número."""
        entries = audit_trace.get("entries", [])
        for entry in entries:
            assert isinstance(entry.get("result", None), (int, float)), (
                f"result no es numérico en {entry.get('component', '?')}: {entry.get('result')}"
            )

    def test_entries_inputs_es_dict(self, audit_trace):
        """El campo inputs de cada entrada debe ser un dict."""
        entries = audit_trace.get("entries", [])
        for entry in entries:
            assert isinstance(entry.get("inputs", None), dict), (
                f"inputs no es dict en {entry.get('component', '?')}"
            )

    def test_entries_tienen_mes(self, audit_trace):
        """Las entradas deben tener el campo mes (>=0)."""
        entries = audit_trace.get("entries", [])
        for entry in entries:
            assert "mes" in entry, f"Falta 'mes' en {entry.get('component', '?')}"
            assert entry["mes"] >= 0


# ---------------------------------------------------------------------------
# Test: Validez de valores traceados
# ---------------------------------------------------------------------------

class TestAuditTraceValueValidity:

    def test_no_payroll_result_positivo(self, audit_trace):
        """Las entradas de no_payroll deben tener result >= 0."""
        entries = audit_trace.get("entries", [])
        no_payroll_entries = [e for e in entries if e.get("component") == "no_payroll"]
        assert no_payroll_entries, "No hay entradas de no_payroll"
        for entry in no_payroll_entries:
            assert entry["result"] >= 0, f"no_payroll result negativo: {entry['result']}"

    def test_cadena_b_tiene_inputs_validos(self, audit_trace):
        """Las entradas de cadena_b deben tener n_canales >= 0."""
        entries = audit_trace.get("entries", [])
        cadena_b_entries = [e for e in entries if e.get("component") == "cadena_b"]
        assert cadena_b_entries, "No hay entradas de cadena_b"
        for entry in cadena_b_entries:
            assert entry["inputs"].get("n_canales", 0) >= 0

    def test_pyg_ingreso_tiene_margen(self, audit_trace):
        """Las entradas de pyg.ingreso deben documentar el margen."""
        entries = audit_trace.get("entries", [])
        pyg_entries = [e for e in entries if e.get("component") == "pyg.ingreso"]
        assert pyg_entries, "No hay entradas de pyg.ingreso"
        for entry in pyg_entries:
            assert "margen" in entry["inputs"], "pyg.ingreso no documenta el margen"
            assert entry["inputs"]["margen"] > 0

    def test_kpis_documenta_margen_minimo(self, audit_trace):
        """Las entradas de kpis deben documentar el margen_minimo."""
        entries = audit_trace.get("entries", [])
        kpi_entries = [e for e in entries if e.get("component") == "kpis"]
        assert kpi_entries, "No hay entradas de kpis"
        for entry in kpi_entries:
            assert "margen_minimo" in entry["inputs"], "kpis no documenta margen_minimo"
