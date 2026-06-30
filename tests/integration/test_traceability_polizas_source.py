"""
tests/integration/test_traceability_polizas_source.py
=====================================================
Validación contractual: diferenciar polizas null vs [] en traceability.

STEP3B MIGRATION: Updated to use TraceabilityRepository instead of filesystem.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.shared.models import PanelDeControl, PerfilCadenaA
from nexa_engine.modules.audit.writer import TraceabilityWriter
from nexa_engine.modules.calculator.persistence.traceability_repository import TraceabilityRepository
from nexa_engine.db.providers.json_document_store import JsonDocumentStore


def _panel() -> PanelDeControl:
    return PanelDeControl(
        cliente="Bancamia",
        tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas",
        fecha_inicio="2026-01-01",
        meses_contrato=12,
        margen=0.18,
        op_cont=0.025,
        com_cont=0.04,
        markup=0.0,
        descuento=0.0,
        tasa_ica=0.0,
        tasa_gmf=0.0,
        activa_financiacion=False,
        periodo_pago_dias=90,
        tasa_mensual_financ=0.0,
        ciudad="Bogota",
        sede="Toberin",
    )


def _solicitud():
    perfiles = [
        PerfilCadenaA(
            nombre="Inbound",
            modalidad="Inbound",
            canal="WhatsApp",
            fte=1.0,
            es_soporte=False,
        )
    ]
    return SimpleNamespace(
        panel=_panel(),
        perfiles_cadena_a=perfiles,
        cadena_b=SimpleNamespace(canales=[]),
        cadena_c=SimpleNamespace(canales=[]),
    )


def test_polizas_vacias_marcan_usuario():
    """Empty polizas_usuario list marks data source as 'usuario'."""
    writer = TraceabilityWriter(repository=None)  # Not needed for _build_audit

    audit = writer._build_audit(
        solicitud=_solicitud(),
        escenarios_aplicados=None,
        polizas_usuario=[],
    )

    data = audit["polizas_source"]
    assert data["fuente"] == "usuario"
    assert data["polizas_activas"] == []
    assert "Lista vacía" in data.get("nota", "")


def test_polizas_null_usan_storage():
    """None polizas_usuario marks data source as 'storage'."""
    writer = TraceabilityWriter(repository=None)  # Not needed for _build_audit

    audit = writer._build_audit(
        solicitud=_solicitud(),
        escenarios_aplicados=None,
        polizas_usuario=None,
    )

    data = audit["polizas_source"]
    assert data["fuente"] == "storage"
