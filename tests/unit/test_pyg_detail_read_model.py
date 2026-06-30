import inspect
import json
from dataclasses import asdict
from datetime import datetime, timezone

from nexa_engine.modules.calculator_motor.formulas.pyg import build_pyg_detail_read_model
from nexa_engine.modules.calculator_motor.models.snapshot import (
    PanelSummary,
    ParametrizationSnapshot,
    SimulationSnapshot,
)
from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
from nexa_engine.modules.shared.models import (
    KPIsDeal,
    PanelDeControl,
    PricingResult,
    PyGMensual,
    ResultadoCadenaB,
    ResultadoCadenaC,
    ResultadoNoPayroll,
    ResultadoNomina,
)
from nexa_engine.modules.vision_pyg.builders.vision_pyg_builder import VisionPyGBuilder


class _NominaCalc:
    def calcular_para_mes(self, perfiles, mes):
        return ResultadoNomina(
            salario_fijo=100.0 * mes,
            comisiones=10.0 * mes,
            capacitacion_inicial=1.0 * mes,
            capacitacion_rotacion=2.0 * mes,
            examenes=3.0 * mes,
            seguridad=4.0 * mes,
            crucero=5.0 * mes,
        )


class _NoPayrollCalc:
    def calcular_para_mes(self, perfiles, mes):
        return ResultadoNoPayroll(
            opex_ti=20.0 * mes,
            capex=30.0 * mes,
            costos_fijos=40.0 * mes,
        )


class _CadenaBCalc:
    def calcular_para_mes(self, mes):
        return ResultadoCadenaB(
            opex_fijo=50.0 * mes,
            inversiones=60.0 * mes,
            soporte_mantenimiento=70.0 * mes,
            costo_variable=80.0 * mes,
            escalamiento=90.0 * mes,
            hitl=100.0 * mes,
        )


class _CadenaCCalc:
    def calcular_para_mes(self, mes):
        return ResultadoCadenaC(
            tarifa_proveedor=110.0 * mes,
            opex_fijo_integ=120.0 * mes,
            inversiones=130.0 * mes,
            equipo_integ=140.0 * mes,
            escalamiento=150.0 * mes,
            opex_var_integ=160.0 * mes,
            hitl=170.0 * mes,
        )


def _panel():
    return PanelDeControl(
        cliente="Client",
        tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas",
        fecha_inicio="2026-01-01",
        meses_contrato=2,
        margen=0.2,
        op_cont=0.0,
        com_cont=0.0,
        markup=0.0,
        descuento=0.0,
        tasa_ica=0.0,
        tasa_gmf=0.0,
        activa_financiacion=False,
        periodo_pago_dias=0,
        tasa_mensual_financ=0.0,
        ciudad="Bogota",
        sede="Toberin",
    )


def _pyg_por_mes():
    return [
        PyGMensual(
            mes=1,
            ingreso_bruto_a=1_000.0,
            payroll_a=100.0,
            no_payroll_a=20.0,
            costo_b=30.0,
            costo_c=40.0,
            ica=7.0,
            ica_a=1.0,
            ica_c=2.0,
            gmf=11.0,
            gmf_a=3.0,
            gmf_c=4.0,
            polizas=18.0,
            polizas_a=5.0,
            polizas_b=6.0,
            polizas_c=7.0,
        ),
        PyGMensual(
            mes=2,
            ingreso_bruto_a=2_000.0,
            payroll_a=200.0,
            no_payroll_a=40.0,
            costo_b=60.0,
            costo_c=80.0,
            ica=14.0,
            ica_a=2.0,
            ica_c=4.0,
            gmf=22.0,
            gmf_a=6.0,
            gmf_c=8.0,
            polizas=36.0,
            polizas_a=10.0,
            polizas_b=12.0,
            polizas_c=14.0,
        ),
    ]


def _inputs():
    return {
        "pyg_por_mes": _pyg_por_mes(),
        "perfiles_cadena_a": [],
        "calc_nomina": _NominaCalc(),
        "calc_no_payroll": _NoPayrollCalc(),
        "calc_cadena_b": _CadenaBCalc(),
        "calc_cadena_c": _CadenaCCalc(),
    }


def _kpis():
    return KPIsDeal(
        valor_total_deal=3_000.0,
        ingreso_neto_total=3_000.0,
        costo_total_contrato=570.0,
        contribucion_total=2_430.0,
    )


def test_calculator_motor_builds_pyg_detail_read_model():
    detail = build_pyg_detail_read_model(**_inputs())

    assert [row.key for row in detail] == [
        "salario_fijo",
        "salario_variable",
        "cap_inicial",
        "cap_rotacion",
        "examenes",
        "estudios_seguridad",
        "crucero",
        "opex_fijo_a",
        "inversiones_a",
        "costos_fijos_a",
        "opex_fijo_b",
        "inversiones_b",
        "sm_b",
        "tarifa_canal_b",
        "tasa_escalamiento_b",
        "hitl_b",
        "tarifa_proveedor_c",
        "opex_fijo_integ_c",
        "inversiones_integ_c",
        "equipo_integ_c",
        "tasa_escalamiento_c",
        "opex_var_integ_c",
        "hitl_c",
        "ica_a",
        "ica_c",
        "gmf_a",
        "gmf_c",
        "polizas_a",
        "polizas_b",
        "polizas_c",
    ]
    assert detail[0].valores == [100.0, 200.0]
    assert detail[0].acumulado == 300.0
    assert detail[0].promedio == 150.0


def test_stored_detail_shape_matches_current_vision_pyg_builder_detail_shape():
    inputs = _inputs()
    stored_detail = build_pyg_detail_read_model(**inputs)
    builder = VisionPyGBuilder()
    result = builder.construir(
        inputs["pyg_por_mes"],
        _kpis(),
        fecha_inicio="2026-01-01",
        panel=_panel(),
        filas_detalle=stored_detail,
    )

    assert [asdict(row) for row in result.filas_detalle] == [asdict(row) for row in stored_detail]


def test_pricing_result_serialization_preserves_pyg_detail_read_model():
    inputs = _inputs()
    detail = build_pyg_detail_read_model(**inputs)
    vision_pyg = VisionPyGBuilder().construir(
        inputs["pyg_por_mes"],
        _kpis(),
        fecha_inicio="2026-01-01",
        panel=_panel(),
        filas_detalle=detail,
    )
    resultado = PricingResult(
        kpis=_kpis(),
        pyg_por_mes=inputs["pyg_por_mes"],
        panel=_panel(),
        vision_pyg=vision_pyg,
    )

    serialized = pricing_result_to_dict(resultado, result_id="sim-pyg-detail")

    payroll_row = next(
        row
        for section in serialized["vision_pyg"]["secciones"]
        for row in section["filas"]
        if row["key"] == "payroll_a"
    )
    assert payroll_row["detalle"][0] == asdict(detail[0])


def test_simulation_snapshot_round_trip_preserves_pyg_detail_read_model():
    inputs = _inputs()
    detail = build_pyg_detail_read_model(**inputs)
    vision_pyg = VisionPyGBuilder().construir(
        inputs["pyg_por_mes"],
        _kpis(),
        fecha_inicio="2026-01-01",
        panel=_panel(),
        filas_detalle=detail,
    )
    resultado = PricingResult(
        kpis=_kpis(),
        pyg_por_mes=inputs["pyg_por_mes"],
        panel=_panel(),
        vision_pyg=vision_pyg,
    )
    serialized = pricing_result_to_dict(resultado, result_id="sim-pyg-detail")
    expected_vision_pyg = serialized["vision_pyg"]

    snapshot = SimulationSnapshot(
        simulation_id="sim-pyg-detail",
        created_at=datetime.now(timezone.utc).isoformat(),
        raw_input={"source": "unit-test"},
        normalized_input={"source": "unit-test"},
        normalization_log={"defaults_applied": [], "warnings": [], "errors": []},
        parametrization=ParametrizationSnapshot(
            parametrization_id="param-001",
            captured_at="2026-06-15T00:00:00+00:00",
            smmlv=1.0,
            auxilio_transporte=1.0,
            linea_negocio="Cobranzas",
            ciudad="Bogota",
        ),
        data_provenance={},
        pricing_result=serialized,
        panel_summary=PanelSummary(
            simulation_id="sim-pyg-detail",
            cliente="Client",
            linea_negocio="Cobranzas",
            ciudad="Bogota",
            meses_contrato=2,
        ),
    )

    restored = SimulationSnapshot.from_dict(json.loads(json.dumps(snapshot.as_dict())))

    assert restored.pricing_result["vision_pyg"] == expected_vision_pyg


def test_vision_pyg_builder_uses_persisted_detail_without_calculator_calls():
    inputs = _inputs()
    stored_detail = build_pyg_detail_read_model(**inputs)

    result = VisionPyGBuilder().construir(
        inputs["pyg_por_mes"],
        _kpis(),
        fecha_inicio="2026-01-01",
        panel=_panel(),
        filas_detalle=stored_detail,
    )

    assert [asdict(row) for row in result.filas_detalle] == [asdict(row) for row in stored_detail]
    assert "calcular_para_mes" not in inspect.getsource(VisionPyGBuilder)


def test_vision_pyg_builder_defaults_to_empty_detail_when_absent():
    inputs = _inputs()
    result = VisionPyGBuilder().construir(
        inputs["pyg_por_mes"],
        _kpis(),
        perfiles_cadena_a=inputs["perfiles_cadena_a"],
        fecha_inicio="2026-01-01",
        panel=_panel(),
    )

    assert result.filas_detalle == []
