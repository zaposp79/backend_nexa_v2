from unittest.mock import MagicMock

from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.adapters.volume_resolution import VolumeResolutionService
from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
from nexa_engine.modules.shared.models import KPIsDeal, PanelDeControl, PolizaContractual, PricingResult, PyGMensual
from nexa_engine.modules.calculator_motor.validation.contract_validator import ContractValidator


def _panel():
    return PanelDeControl(
        cliente="Bancamia",
        tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas",
        fecha_inicio="2026-01-01",
        meses_contrato=24,
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
    )


def _provider():
    provider = MagicMock()
    provider.get_tasa_polizas_efectiva.return_value = 0.99
    provider.get_factor_periodo.return_value = 1
    return provider


def test_poliza_solo_b_no_afecta_a_ni_c():
    calc = CostosFinancierosCalculator(
        _panel(),
        _provider(),
        polizas_usuario=[
            PolizaContractual(
                nombre="B only",
                activa=True,
                pct_poliza=0.10,
                pct_atribuible=1.0,
                aplica_a=False,
                aplica_b=True,
                aplica_c=False,
            )
        ],
    )

    result = calc.calcular(300.0, mes=1, costo_a=100.0, costo_b=200.0, costo_c=0.0)

    assert result.polizas_a == 0.0
    assert result.polizas_b > 0.0
    assert result.polizas_c == 0.0
    assert result.polizas == result.polizas_b


def test_polizas_vacias_no_usan_parametrizacion():
    provider = _provider()
    calc = CostosFinancierosCalculator(_panel(), provider, polizas_usuario=[])

    result = calc.calcular(100.0, mes=1, costo_a=100.0, costo_b=0.0, costo_c=0.0)

    assert result.polizas == 0.0
    provider.get_tasa_polizas_efectiva.assert_not_called()


def test_polizas_null_usan_parametrizacion():
    provider = _provider()
    calc = CostosFinancierosCalculator(_panel(), provider, polizas_usuario=None)

    result = calc.calcular(100.0, mes=1)

    assert result.polizas > 0.0
    provider.get_tasa_polizas_efectiva.assert_called_once_with(1)


def test_loader_parsea_cadenas_de_polizas():
    polizas = UserInputLoader()._polizas([
        {
            "nombre": "Solo C",
            "activa": True,
            "pct_poliza": 0.02,
            "pct_atribuible": 0.5,
            "cadenas": {"cadena_a": False, "cadena_b": False, "cadena_c": True},
        }
    ])

    assert polizas[0].aplica_a is False
    assert polizas[0].aplica_b is False
    assert polizas[0].aplica_c is True


def test_contract_validator_exige_cadenas_activas():
    payload = {
        "datos_operativos": {
            "cliente": "Bancamia",
            "servicio": "Cobranzas",
            "ciudad": "Bogota",
            "fecha_inicio": "2026-01-01",
            "duracion_meses": 12,
        },
        "reglas_negocio": {
            "margen_objetivo": 0.18,
            "contingencia_operativa": {"valor": 0.025},
            "contingencia_comercial": {"valor": 0.04},
            "markup": {"valor": 0.02},
        },
        "volumetria": {
            "indexacion": {
                "componente_humano": "IPC",
                "componente_tecnologico": "IPC",
                "frecuencia": "Anual",
                "mes_aplicacion": 1,
                "tasa_interes_mensual": 0.01,
            },
            "inbound": {"cadenas_activas": {}, "canales": []},
            "outbound": {"cadenas_activas": {}, "canales": []},
        },
    }

    result = ContractValidator().validate(payload)

    assert not result.is_valid
    assert any("activate at least one cadena" in error for error in result.errors)


def test_volume_resolution_respeta_cadenas_desactivadas():
    service = VolumeResolutionService({
        "inbound": {
            "cadenas_activas": {"cadena_a": True, "cadena_b": False, "cadena_c": True},
            "canales": [
                {
                    "canal": "WhatsApp",
                    "cadena_a": {"valor": 7},
                    "cadena_b": {"valor": 99},
                    "cadena_c": {"valor": 11},
                }
            ],
        },
        "outbound": {"cadenas_activas": {}, "canales": []},
    })

    assert service.volumen("Inbound", "WhatsApp", "cadena_a") == 7.0
    assert service.volumen("Inbound", "WhatsApp", "cadena_b") == 0.0
    assert service.volumen("Inbound", "WhatsApp", "cadena_c") == 11.0
    assert service.volumen_canal_total("Inbound", "WhatsApp") == 18.0


def test_serializer_expone_polizas_por_cadena():
    resultado = PricingResult(
        kpis=KPIsDeal(),
        pyg_por_mes=[
            PyGMensual(mes=1, polizas_a=10.0, polizas_b=20.0, polizas_c=0.0),
            PyGMensual(mes=2, polizas_a=1.0, polizas_b=2.0, polizas_c=3.0),
        ],
        panel=_panel(),
    )

    data = pricing_result_to_dict(resultado, "sim-test")

    assert data["polizas"] == {
        "cadena_a": 11.0,
        "cadena_b": 22.0,
        "cadena_c": 3.0,
    }
    assert data["pyg_por_mes"][0]["polizas_por_cadena"]["cadena_b"] == 20.0
