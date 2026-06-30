from types import SimpleNamespace
from unittest.mock import MagicMock

import nexa_engine.modules.calculator_motor.formulas.graphics.graficos_result_builder as module

from nexa_engine.modules.calculator_motor.formulas.graphics.graficos_result_builder import (
    build_graficos_result,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.models import GraficosResult
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


def test_build_graficos_result_populates_all_graphs(monkeypatch):
    graficos = GraficosResult(
        bandas_vision_final=_graph_result("bandas_vision_final"),
    )
    outputs = {
        "ratios_cost_to_serve": _graph_result("ratios_cost_to_serve"),
        "ingresos_mensuales": _graph_result("ingresos_mensuales"),
        "waterfall_table": _graph_result("waterfall_table"),
        "cts_bargaining_zone": _graph_result("cts_bargaining_zone"),
    }

    monkeypatch.setattr(module, "calculate_graph_series", lambda **kwargs: graficos)
    monkeypatch.setattr(module, "build_ratios_cost_to_serve", lambda **kwargs: outputs["ratios_cost_to_serve"])
    monkeypatch.setattr(module, "build_ingresos_mensuales", lambda **kwargs: outputs["ingresos_mensuales"])
    monkeypatch.setattr(module, "build_waterfall_table", lambda **kwargs: outputs["waterfall_table"])
    monkeypatch.setattr(module, "build_cts_bargaining_zone", lambda **kwargs: outputs["cts_bargaining_zone"])
    monkeypatch.setattr(module, "NominaCalculator", lambda *args: object())

    parametrizacion = MagicMock()
    parametrizacion.get_portfolio_clientes.return_value = {
        "clientes": [],
        "promedios_por_categoria": {},
    }
    solicitud = SimpleNamespace(
        panel=SimpleNamespace(linea_negocio="SAC", cliente="Cliente", margen=0.1),
        escenarios=[object()],
        perfiles_cadena_a=[object()],
        parametros_nomina=object(),
        parametros_calculo=object(),
    )
    resultado = SimpleNamespace(
        pyg_por_mes=[SimpleNamespace(ingreso_neto=100.0, pct_contribucion=0.2)],
        kpis=SimpleNamespace(
            pct_utilidad_neta_total=0.08,
            costo_mensual_promedio=80.0,
            ingreso_neto_total=1200.0,
        ),
        datasets_vision=DatasetsVision(),
    )

    result = build_graficos_result(resultado, solicitud, parametrizacion)

    assert result is graficos
    assert result.ratios_cost_to_serve is outputs["ratios_cost_to_serve"]
    assert result.ingresos_mensuales is outputs["ingresos_mensuales"]
    assert result.waterfall_table is outputs["waterfall_table"]
    assert result.cts_bargaining_zone is outputs["cts_bargaining_zone"]
    assert set(result.as_dict()) == GRAPH_KEYS


def test_build_graficos_result_none_without_parametrizacion():
    resultado = SimpleNamespace(
        pyg_por_mes=[],
        kpis=SimpleNamespace(),
        datasets_vision=DatasetsVision(),
    )
    solicitud = SimpleNamespace(panel=SimpleNamespace())

    assert build_graficos_result(resultado, solicitud, parametrizacion=None) is None
