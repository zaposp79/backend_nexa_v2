import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from nexa_engine.modules.calculator_motor.formulas.graphics.models import GraficosResult
from nexa_engine.modules.calculator_motor.models.snapshot import (
    PanelSummary,
    ParametrizationSnapshot,
    SimulationSnapshot,
)
from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
from nexa_engine.modules.shared.models import KPIsDeal, PanelDeControl, PricingResult, PyGMensual
from nexa_engine.modules.vision_imprimible.builders import graficos_dataset_builder as module
from nexa_engine.modules.vision_imprimible.builders.graficos_dataset_builder import (
    GraficosDatasetBuilder,
)
from nexa_engine.modules.vision_imprimible.builders.vision_datasets_builder import (
    VisionDatasetsBuilder,
)
from nexa_engine.modules.vision_imprimible.models.vision_datasets import DatasetsVision


GRAPH_KEYS = {
    "bandas_vision_final",
    "ratios_cost_to_serve",
    "ingresos_mensuales",
    "waterfall_table",
    "cts_bargaining_zone",
}


def _graph_result(name):
    result = MagicMock(name=name)
    result.as_dict.return_value = {"graph": name}
    return result


def _panel():
    return PanelDeControl(
        cliente="ContractClient",
        tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas",
        fecha_inicio="2026-01-01",
        meses_contrato=12,
        margen=0.21,
        op_cont=0.025,
        com_cont=0.04,
        markup=0.0,
        descuento=0.0,
        tasa_ica=0.0097,
        tasa_gmf=0.004,
        activa_financiacion=True,
        periodo_pago_dias=30,
        tasa_mensual_financ=0.0153,
        ciudad="Bogota",
        sede="Toberin",
    )


def _pricing_result_with_graphs():
    graficos = GraficosResult(
        bandas_vision_final=_graph_result("bandas_vision_final"),
        ratios_cost_to_serve=_graph_result("ratios_cost_to_serve"),
        ingresos_mensuales=_graph_result("ingresos_mensuales"),
        waterfall_table=_graph_result("waterfall_table"),
        cts_bargaining_zone=_graph_result("cts_bargaining_zone"),
    )
    return PricingResult(
        kpis=KPIsDeal(
            costo_mensual_promedio=80_000.0,
            ingreso_mensual=100_000.0,
            ingreso_neto_total=1_200_000.0,
            valor_total_deal=1_500_000.0,
            cumple_margen_minimo=True,
        ),
        pyg_por_mes=[
            PyGMensual(
                mes=1,
                ingreso_bruto_a=100_000.0,
                ingreso_bruto_b=0.0,
                ingreso_bruto_c=0.0,
                payroll_a=50_000.0,
                no_payroll_a=10_000.0,
                costo_b=12_000.0,
                costo_c=8_000.0,
            )
        ],
        panel=_panel(),
        datasets_vision=DatasetsVision(graficos=graficos),
    )


def test_graficos_dataset_builder_reads_precomputed_result():
    graficos = GraficosResult(
        bandas_vision_final=_graph_result("bandas_vision_final"),
        ratios_cost_to_serve=_graph_result("ratios_cost_to_serve"),
        ingresos_mensuales=_graph_result("ingresos_mensuales"),
        waterfall_table=_graph_result("waterfall_table"),
        cts_bargaining_zone=_graph_result("cts_bargaining_zone"),
    )
    resultado = SimpleNamespace(
        datasets_vision=SimpleNamespace(graficos=graficos),
    )

    result = GraficosDatasetBuilder().construir(resultado, SimpleNamespace())

    assert result is graficos
    assert set(result.as_dict()) == GRAPH_KEYS


def test_vision_datasets_builder_reads_graphs_from_result():
    graficos = GraficosResult(
        bandas_vision_final=_graph_result("bandas_vision_final"),
    )
    resultado = SimpleNamespace(
        datasets_vision=SimpleNamespace(graficos=graficos),
    )
    builder = VisionDatasetsBuilder(parametrizacion=object())

    result = builder._build_graficos(SimpleNamespace(), resultado)

    assert result is graficos


def test_vision_module_does_not_import_graph_calculators():
    assert not hasattr(module, "calculate_graph_series")
    assert not hasattr(module, "build_ratios_cost_to_serve")
    assert not hasattr(module, "build_ingresos_mensuales")
    assert not hasattr(module, "build_waterfall_table")
    assert not hasattr(module, "build_cts_bargaining_zone")
    assert not hasattr(module, "NominaCalculator")


def test_pricing_result_serialization_preserves_graph_payload():
    resultado = _pricing_result_with_graphs()

    serialized = pricing_result_to_dict(resultado, result_id="sim-graph-01")
    graficos = serialized["datasets_vision"]["graficos"]

    assert set(graficos) == GRAPH_KEYS
    assert graficos["bandas_vision_final"]["graph"] == "bandas_vision_final"
    assert graficos["ratios_cost_to_serve"]["graph"] == "ratios_cost_to_serve"
    assert graficos["ingresos_mensuales"]["graph"] == "ingresos_mensuales"
    assert graficos["waterfall_table"]["graph"] == "waterfall_table"
    assert graficos["cts_bargaining_zone"]["graph"] == "cts_bargaining_zone"


def test_snapshot_round_trip_keeps_stored_graph_payload():
    resultado = _pricing_result_with_graphs()
    serialized = pricing_result_to_dict(resultado, result_id="sim-graph-02")
    expected_graphs = serialized["datasets_vision"]["graficos"]

    snapshot = SimulationSnapshot(
        simulation_id="sim-graph-02",
        created_at=datetime.now(timezone.utc).isoformat(),
        raw_input={"source": "unit-test"},
        normalized_input={"source": "unit-test"},
        normalization_log={"defaults_applied": [], "warnings": [], "errors": []},
        parametrization=ParametrizationSnapshot(
            parametrization_id="param-001",
            captured_at="2026-06-14T00:00:00+00:00",
            smmlv=1.0,
            auxilio_transporte=1.0,
            linea_negocio="Cobranzas",
            ciudad="Bogota",
        ),
        data_provenance={},
        pricing_result=serialized,
        panel_summary=PanelSummary(
            simulation_id="sim-graph-02",
            cliente="ContractClient",
            linea_negocio="Cobranzas",
            ciudad="Bogota",
            meses_contrato=12,
        ),
    )

    restored = SimulationSnapshot.from_dict(json.loads(json.dumps(snapshot.as_dict())))

    assert restored.pricing_result["datasets_vision"]["graficos"] == expected_graphs
