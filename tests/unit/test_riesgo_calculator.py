"""
tests/unit/test_riesgo_calculator.py
=====================================
Tests unitarios para RiesgoCalculator.

Cubre:
  - Scoring de cada categoría (Cliente / Operativo)
  - Score total ponderado
  - Clasificación del score
  - requiere_aprobacion (valor_total_deal vs umbral SMMLV)
  - Criterio 1: clasificación de oportunidad
  - Criterio 2: tipo de cliente
  - Criterio 3: período de pago
  - Criterio 4: experiencia con el cliente
  - Criterio 6: alertas activadas (contingencias bajo mínimo)
  - Criterio 7: complejidad (canales activos)
  - Criterio 9: rotación
  - Criterio 10: dependencia de terceros
"""
import pytest
from unittest.mock import MagicMock

from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator

# BUSINESS_RULES_FIX_2B: smmlv es obligatorio. Usar HR canónico en todos los tests.
_SMMLV_HR_2026: float = 1_750_905.0
from nexa_engine.modules.shared.models import (
    CanalCadenaB,
    CanalCadenaC,
    Indexacion,
    KPIsDeal,
    PanelDeControl,
    ParametrosCadenaB,
    ParametrosCadenaC,
    PerfilCadenaA,
    PyGMensual,
)


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _panel(
    tipo_cliente="No Grupo Aval",
    antiguedad_cliente="Cliente Nuevo",
    periodo_pago_dias=30,
    margen=0.1339,
    op_cont=0.02,
    com_cont=0.0,
    markup=0.0,
    descuento=0.0,
    pct_ausentismo=0.065,
) -> PanelDeControl:
    return PanelDeControl(
        cliente=           "Bancamia",
        tipo_cliente=      tipo_cliente,
        linea_negocio=     "Cobranzas",
        fecha_inicio=      "2026-01-01",
        meses_contrato=    12,
        margen=            margen,
        op_cont=           op_cont,
        com_cont=          com_cont,
        markup=            markup,
        descuento=         descuento,
        tasa_ica=          0.02,
        tasa_gmf=          0.004,
        activa_financiacion=True,
        periodo_pago_dias= periodo_pago_dias,
        tasa_mensual_financ=0.0153,
        ciudad=            "Medellín",
        sede=              "Medellín",
        antiguedad_cliente=antiguedad_cliente,
        pct_ausentismo=    pct_ausentismo,
        indexacion=        Indexacion(componente_humano="IPC", frecuencia="Anual"),
    )


def _kpis(valor_total_deal=5_564_538_255.66) -> KPIsDeal:
    return KPIsDeal(
        costo_mensual_promedio=       401_864_564.78,
        costo_cadena_a_promedio=      42_358_375.19,
        ingreso_mensual=              355_764_509.40,
        facturacion_mensual_proyectada=355_764_509.40,
        ingreso_bruto_total=          5_363_910_489.35,
        ingreso_neto_total=           5_471_188_699.14,
        costo_total_contrato=         4_822_374_777.42,
        contribucion_total=           648_813_921.72,
        utilidad_neta_total=          648_813_921.72,
        pct_utilidad_neta_total=      -0.02,
        valor_total_deal=             valor_total_deal,
        margen_minimo_requerido=      0.0,
        cumple_margen_minimo=         False,
    )


def _pyg_lista(n=12) -> list:
    """Lista de n meses de PyGMensual con valores típicos."""
    return [
        PyGMensual(
            mes=i + 1,
            rampup=1.0,
            payroll_a=30_017_216.83,
            no_payroll_a=9_285_618.27,
            costo_b=358_701_004.10,
            costo_c=0.0,
            financiacion=0.0,
            polizas=25_738_337.47,
            ica=800_000.0,
            gmf=400_000.0,
            ingreso_bruto_a=37_880_662.01,
            ingreso_bruto_b=345_721_408.28,
            ingreso_bruto_c=0.0,
            contingencia_op=7_672_041.41,
            contingencia_com=0.0,
            markup_ingreso=0.0,
            descuento_ingreso=0.0,
        )
        for i in range(n)
    ]


def _perfil(canal="WhatsApp", fte=6, dias_cap=7, es_soporte=False) -> PerfilCadenaA:
    return PerfilCadenaA(
        nombre=       f"Perfil {canal}",
        modalidad=    "Inbound",
        canal=        canal,
        fte=          fte,
        dias_cap_inicial=dias_cap,
        es_soporte=   es_soporte,
    )


def _cadena_b(canales=None) -> ParametrosCadenaB:
    if canales is None:
        canales = [CanalCadenaB(nombre="WhatsApp", modalidad="Inbound",
                                producto="WhatsApp", volumen_mensual=7534.89)]
    return ParametrosCadenaB(canales=canales)


def _cadena_c(canales=None) -> ParametrosCadenaC:
    if canales is None:
        canales = []
    return ParametrosCadenaC(canales=canales)


def _calc():
    # BUSINESS_RULES_FIX_2B: smmlv obligatorio — pasar HR canónico explícitamente.
    return RiesgoCalculator(smmlv=_SMMLV_HR_2026)


# ---------------------------------------------------------------------------
# Tests de scoring
# ---------------------------------------------------------------------------

class TestScoring:

    def test_score_cliente_formula(self):
        """score_cliente = SUMPRODUCT(puntaje × peso) para criterios Cliente."""
        # Con los datos de referencia del Excel V2-4:
        # Criterio 1: puntaje=3 peso=0.30 → 0.90
        # Criterio 2: puntaje=3 peso=0.25 → 0.75
        # Criterio 3: puntaje=1 peso=0.25 → 0.25
        # Criterio 4: puntaje=3 peso=0.10 → 0.30
        # Criterio 5: puntaje=1 peso=0.10 → 0.10
        # Total = 2.30
        panel = _panel(
            tipo_cliente="No Grupo Aval",
            antiguedad_cliente="Cliente Nuevo",
            periodo_pago_dias=30,
        )
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        assert abs(resultado.score_cliente - 2.30) < 0.001

    def test_score_total_ponderado(self):
        """score_total = score_cliente × 0.4 + score_operativo × 0.6"""
        panel = _panel(periodo_pago_dias=30)
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        expected = resultado.score_cliente * 0.4 + resultado.score_operativo * 0.6
        assert abs(resultado.score_total - expected) < 0.0001

    def test_clasificacion_medio(self):
        """score en [1.5, 2.5) → "Medio"."""
        panel = _panel(tipo_cliente="No Grupo Aval",
                       antiguedad_cliente="Cliente Nuevo",
                       periodo_pago_dias=30)
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        assert resultado.clasificacion_total == "Medio"

    def test_clasificacion_bajo_score_minimo(self):
        """score < 1.5 → "Bajo"."""
        calc = _calc()
        assert calc._clasificar(1.0) == "Bajo"
        assert calc._clasificar(1.49) == "Bajo"

    def test_clasificacion_alto_score_maximo(self):
        """score ≥ 2.5 → "Alto"."""
        calc = _calc()
        assert calc._clasificar(2.5) == "Alto"
        assert calc._clasificar(3.0) == "Alto"

    def test_clasificacion_medio_rango(self):
        """1.5 ≤ score < 2.5 → "Medio"."""
        calc = _calc()
        assert calc._clasificar(1.5) == "Medio"
        assert calc._clasificar(2.0) == "Medio"
        assert calc._clasificar(2.49) == "Medio"


# ---------------------------------------------------------------------------
# Tests de requiere_aprobacion
# ---------------------------------------------------------------------------

class TestRequiereAprobacion:

    def test_requiere_aprobacion_deal_grande(self):
        """Deal > 1000 SMMLV requiere aprobación."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        umbral_cop = calc._umbral_aprobacion_smmlv * calc._smmlv
        kpis = _kpis(valor_total_deal=umbral_cop + 1)
        resultado = _calc().calcular(
            panel=_panel(), kpis=kpis, pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        assert resultado.requiere_aprobacion is True

    def test_no_requiere_aprobacion_deal_pequeno(self):
        """Deal < 1000 SMMLV no requiere aprobación."""
        kpis = _kpis(valor_total_deal=100_000_000.0)  # 100M COP < umbral
        resultado = _calc().calcular(
            panel=_panel(), kpis=kpis, pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        assert resultado.requiere_aprobacion is False


# ---------------------------------------------------------------------------
# Tests de criterios individuales
# ---------------------------------------------------------------------------

class TestCriterioPeriodoPago:

    def test_periodo_30_dias_es_bajo(self):
        panel = _panel(periodo_pago_dias=30)
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c3 = next(c for c in resultado.criterios if c.id == 3)
        assert c3.calificacion == "Bajo"
        assert c3.puntaje == 1

    def test_periodo_90_dias_es_alto(self):
        panel = _panel(periodo_pago_dias=90)
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c3 = next(c for c in resultado.criterios if c.id == 3)
        assert c3.calificacion == "Alto"
        assert c3.puntaje == 3


class TestCriterioTipoCliente:

    def test_no_grupo_aval_es_alto(self):
        panel = _panel(tipo_cliente="No Grupo Aval")
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c2 = next(c for c in resultado.criterios if c.id == 2)
        assert c2.calificacion == "Alto"
        assert c2.puntaje == 3

    def test_grupo_aval_es_bajo(self):
        panel = _panel(tipo_cliente="Grupo Aval")
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c2 = next(c for c in resultado.criterios if c.id == 2)
        assert c2.calificacion == "Bajo"
        assert c2.puntaje == 1


class TestCriterioAlertasActivadas:

    def test_sin_alertas_es_bajo(self):
        """Todas las contingencias dentro del rango → 0 alertas → Bajo."""
        panel = _panel(op_cont=0.06, com_cont=0.05)  # ambas por encima del mínimo
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c6 = next(c for c in resultado.criterios if c.id == 6)
        assert c6.calificacion == "Bajo"
        assert c6.puntaje == 1

    def test_dos_alertas_es_medio(self):
        """op_cont y com_cont por debajo de sus mínimos → 2 alertas → Medio."""
        panel = _panel(op_cont=0.02, com_cont=0.00)  # ambas bajo mínimo
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c6 = next(c for c in resultado.criterios if c.id == 6)
        assert c6.calificacion == "Medio"
        assert c6.puntaje == 2


class TestCriterioComplejidad:

    def test_un_canal_es_bajo(self):
        """1 canal → Bajo (≤ 3)."""
        perfiles = [_perfil(canal="WhatsApp")]
        cadena_b = _cadena_b([CanalCadenaB(
            nombre="WhatsApp", modalidad="Inbound",
            producto="WhatsApp", volumen_mensual=1000
        )])
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=perfiles, cadena_b=cadena_b, cadena_c=_cadena_c(),
        )
        c7 = next(c for c in resultado.criterios if c.id == 7)
        assert c7.puntaje == 1  # Bajo

    def test_muchos_canales_es_alto(self):
        """7 canales activos → Alto (> 6)."""
        canales_b = [
            CanalCadenaB(nombre=f"Canal{i}", modalidad="Inbound",
                         producto=f"Canal{i}", volumen_mensual=100)
            for i in range(7)
        ]
        perfiles = [_perfil(canal=f"Canal{i}") for i in range(7)]
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=perfiles,
            cadena_b=_cadena_b(canales_b), cadena_c=_cadena_c(),
        )
        c7 = next(c for c in resultado.criterios if c.id == 7)
        assert c7.puntaje == 3  # Alto


class TestCriterioRotacion:

    def test_baja_rotacion_es_bajo(self):
        """pct_ausentismo < 5% → Bajo."""
        panel = _panel(pct_ausentismo=0.03)
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c9 = next(c for c in resultado.criterios if c.id == 9)
        assert c9.puntaje == 1

    def test_alta_rotacion_es_alto(self):
        """pct_ausentismo > 10% → Alto."""
        panel = _panel(pct_ausentismo=0.12)
        resultado = _calc().calcular(
            panel=panel, kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        c9 = next(c for c in resultado.criterios if c.id == 9)
        assert c9.puntaje == 3


class TestCriterioDependenciaTerceros:

    def test_sin_cadena_c_es_bajo(self):
        """0 canales Cadena C → Bajo."""
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c([]),
        )
        c10 = next(c for c in resultado.criterios if c.id == 10)
        assert c10.puntaje == 1

    def test_con_cadena_c_activa_es_medio(self):
        """1 canal Cadena C activo → Medio."""
        canales_c = [CanalCadenaC(nombre="AI1", modalidad="Inbound",
                                  volumen_mensual=500)]
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(canales_c),
        )
        c10 = next(c for c in resultado.criterios if c.id == 10)
        assert c10.puntaje == 2  # Medio


# ---------------------------------------------------------------------------
# Tests estructurales
# ---------------------------------------------------------------------------

class TestEstructuraResultado:

    def test_tiene_exactamente_10_criterios(self):
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        assert len(resultado.criterios) == 10

    def test_ids_son_consecutivos_1_a_10(self):
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        ids = [c.id for c in resultado.criterios]
        assert ids == list(range(1, 11))

    def test_suma_pesos_cliente_es_1(self):
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        suma_cliente = sum(
            c.peso for c in resultado.criterios if c.categoria == "Cliente"
        )
        assert abs(suma_cliente - 1.0) < 0.0001

    def test_suma_pesos_operativo_es_1(self):
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        suma_op = sum(
            c.peso for c in resultado.criterios if c.categoria == "Operativo"
        )
        assert abs(suma_op - 1.0) < 0.0001

    def test_puntaje_valido_rango(self):
        """Todos los puntajes deben ser 1, 2 o 3."""
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        for c in resultado.criterios:
            assert c.puntaje in {1, 2, 3}, f"Criterio {c.id} tiene puntaje inválido: {c.puntaje}"

    def test_calificacion_valida(self):
        """Todas las calificaciones deben ser Alto, Medio o Bajo."""
        resultado = _calc().calcular(
            panel=_panel(), kpis=_kpis(), pyg_por_mes=_pyg_lista(),
            perfiles_cadena_a=[_perfil()],
            cadena_b=_cadena_b(), cadena_c=_cadena_c(),
        )
        for c in resultado.criterios:
            assert c.calificacion in {"Alto", "Medio", "Bajo"}, \
                f"Criterio {c.id} tiene calificación inválida: {c.calificacion}"
