"""Tests del modo auditoría (debug_trace)."""
from __future__ import annotations

import pytest


class TestAuditTracer:
    """El AuditTracer registra cálculos cuando enabled=True."""

    def test_tracer_disabled_no_overhead(self):
        from nexa_engine.modules.audit.trace import get_tracer
        tracer = get_tracer()
        tracer.reset()
        tracer.stop()
        tracer.entry(
            component="test", rule="test", formula="x=1",
            inputs={"a": 1}, result=1.0,
        )
        # disabled → no entry recorded
        assert len(tracer.entries) == 0

    def test_tracer_enabled_records(self):
        from nexa_engine.modules.audit.trace import get_tracer
        tracer = get_tracer()
        tracer.start(case="test")
        tracer.entry(
            component="payroll", rule="EMPLEADO.test", formula="x=1",
            inputs={"a": 1}, result=42.0,
        )
        assert len(tracer.entries) == 1
        assert tracer.entries[0].result == 42.0
        assert tracer.entries[0].component == "payroll"
        tracer.stop()

    @pytest.mark.legacy  # WAVE 7: fixture whatsapp_only_case sin cadenas_activas (TASK_3)
    def test_tracer_captures_engine_run(self, whatsapp_only_case, run_engine):
        from nexa_engine.modules.audit.trace import get_tracer
        tracer = get_tracer()
        tracer.start(case="test_capture")
        run_engine(whatsapp_only_case)
        tracer.stop()
        # Engine debería emitir entries
        assert len(tracer.entries) > 100, f"Got only {len(tracer.entries)} entries"
        # By component variety
        components = {e.component for e in tracer.entries}
        assert "payroll.salario_fijo" in components
        assert "costos_financieros" in components

    @pytest.mark.legacy  # WAVE 7: fixture whatsapp_only_case sin cadenas_activas (TASK_3)
    def test_tracer_export_json(self, tmp_path, whatsapp_only_case, run_engine):
        from nexa_engine.modules.audit.trace import get_tracer
        tracer = get_tracer()
        tracer.start(case="export_test")
        run_engine(whatsapp_only_case)
        tracer.stop()
        path = tmp_path / "trace.json"
        tracer.export(path)
        assert path.exists()
        import json
        data = json.loads(path.read_text())
        assert "entries" in data
        assert "summary" in data
        assert data["summary"]["total_entries"] > 0

    @pytest.mark.legacy  # WAVE 7: fixture whatsapp_only_case sin cadenas_activas (TASK_3)
    def test_tracer_tipo_laboral_correcto(self, whatsapp_only_case, run_engine):
        """Trace debe marcar tipo_laboral apropiado para cada rol."""
        from nexa_engine.modules.audit.trace import get_tracer
        tracer = get_tracer()
        tracer.start(case="tipo_check")
        run_engine(whatsapp_only_case)
        tracer.stop()
        by_tipo = tracer.to_dict()["summary"]["by_tipo_laboral"]
        # Debe haber entries de distintos tipos laborales
        assert "EMPLEADO_ESTANDAR" in by_tipo
        assert "APRENDIZ_SENA" in by_tipo
        assert "IMPLEMENTACION_PROYECTOS" in by_tipo
        assert "SOPORTE_COMISIONABLE" in by_tipo
