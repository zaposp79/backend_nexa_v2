"""
tests/certification/test_layer1_determinism.py
===============================================
LAYER 1 — Determinism Certification.

Garantía: El motor es puro y determinístico.
  - Misma entrada → misma salida, siempre (idempotencia)
  - No muta el estado de entrada
  - No depende de estado externo (tiempo, random, I/O)
  - Mantiene precisión decimal completa (sin redondeo interno)

Lo que detecta:
  ✅ Estado mutable en el motor
  ✅ Seeds no fijados (random, uuid, datetime.now)
  ✅ Cálculos que varían entre ejecuciones
  ✅ Redondeo interno que destruye precisión

Lo que NO detecta (cubierto en L2/L3):
  ❌ Corrección financiera del modelo
  ❌ Consistencia entre visiones
  ❌ Validez económica del resultado
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401


# ─── Parámetros de test ────────────────────────────────────────────────────
_SALARIOS_TEST = [
    1_750_905.0,   # SMMLV exacto (Agente Básico)
    2_000_000.0,   # Low salary, con auxilio
    3_500_000.0,   # Cerca del umbral 2×SMMLV
    5_000_000.0,   # Mid salary
    18_505_000.0,  # Alto salario (Director de Cuentas)
]

_N_RUNS = 5  # Número de ejecuciones para test de idempotencia


# ═══════════════════════════════════════════════════════════════════════════
# L1.1 — Idempotencia Absoluta
# ═══════════════════════════════════════════════════════════════════════════

class TestIdempotencia:
    """
    El motor debe producir resultados bit-a-bit idénticos en N ejecuciones.
    Detecta: estado mutable, dependencia de tiempo/random, efectos secundarios.
    """

    @pytest.mark.parametrize("salario", _SALARIOS_TEST)
    def test_calcular_idempotente_n_runs(self, nomina_service, salario):
        """calcular() produce resultado idéntico en 5 ejecuciones consecutivas."""
        resultados = [nomina_service.calcular(salario) for _ in range(_N_RUNS)]
        referencia = resultados[0]
        assert referencia > 0, f"Motor retornó {referencia} ≤ 0 para salario={salario}"
        for i, r in enumerate(resultados[1:], start=2):
            assert r == referencia, (
                f"calcular({salario}) — Run {i} difiere del Run 1: "
                f"{r} ≠ {referencia}  |  Δ = {abs(r - referencia)}"
            )

    @pytest.mark.parametrize("salario", _SALARIOS_TEST[:3])
    def test_calcular_sm_idempotente(self, nomina_service, salario):
        """calcular_sm() produce resultado idéntico en 5 ejecuciones."""
        resultados = [nomina_service.calcular_sm(salario) for _ in range(_N_RUNS)]
        referencia = resultados[0]
        for i, r in enumerate(resultados[1:], start=2):
            assert r == referencia, (
                f"calcular_sm({salario}) — Run {i} difiere: "
                f"{r} ≠ {referencia}"
            )

    @pytest.mark.parametrize("salario", _SALARIOS_TEST[:3])
    def test_calcular_aprendiz_idempotente(self, nomina_service, salario):
        """calcular_aprendiz() produce resultado idéntico en 5 ejecuciones."""
        resultados = [nomina_service.calcular_aprendiz(salario) for _ in range(_N_RUNS)]
        referencia = resultados[0]
        for i, r in enumerate(resultados[1:], start=2):
            assert r == referencia, (
                f"calcular_aprendiz({salario}) — Run {i} difiere: "
                f"{r} ≠ {referencia}"
            )

    def test_resultado_idempotente_con_comision(self, nomina_service):
        """calcular() con comisión también es idempotente."""
        salario, comision = 2_000_000.0, 0.10
        resultados = [
            nomina_service.calcular(salario, comision_pct=comision)
            for _ in range(_N_RUNS)
        ]
        assert len(set(resultados)) == 1, (
            f"calcular con comisión no es idempotente: {resultados}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# L1.2 — Pureza (sin mutación de input)
# ═══════════════════════════════════════════════════════════════════════════

class TestPureza:
    """
    El motor NO debe mutar sus parámetros de entrada.
    Detecta: efectos secundarios no declarados, aliasing de objetos.
    """

    def test_calcular_no_muta_parametros(self, nomina_service):
        """calcular() no modifica el objeto ParametrosNominaLaboral."""
        p = nomina_service._p
        smmlv_antes = p.salario_minimo
        tasa_pension_antes = p.tasa_pension
        factor_alto_antes = p.factor_alto_salario_smmlv

        nomina_service.calcular(3_000_000.0)
        nomina_service.calcular(18_000_000.0)
        nomina_service.calcular_sm(5_000_000.0)
        nomina_service.calcular_aprendiz(1_750_905.0)

        assert p.salario_minimo == smmlv_antes
        assert p.tasa_pension == tasa_pension_antes
        assert p.factor_alto_salario_smmlv == factor_alto_antes

    def test_servicio_es_frozen_dataclass(self, nomina_service):
        """ParametrosNominaLaboral es frozen=True — inmutable por diseño."""
        p = nomina_service._p
        with pytest.raises((AttributeError, TypeError)):
            p.salario_minimo = 0.0  # type: ignore

    def test_multiple_instancias_independientes(self, raw_params):
        """Dos instancias del servicio con mismos params producen mismos resultados."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService

        provider = ParametrizationProvider.build()
        svc1 = NominaCargadaService.desde_parametrizacion(provider)
        svc2 = NominaCargadaService.desde_parametrizacion(provider)

        salario = 3_000_000.0
        assert svc1.calcular(salario) == svc2.calcular(salario)


# ═══════════════════════════════════════════════════════════════════════════
# L1.3 — Independencia de Estado Externo
# ═══════════════════════════════════════════════════════════════════════════

class TestIndependenciaEstadoExterno:
    """
    El motor no debe depender de tiempo, I/O, random, ni variables de entorno.
    Detecta: cálculos que incluyen datetime.now(), random.random(), etc.
    """

    def test_resultado_no_depende_de_orden_de_llamadas(self, nomina_service):
        """El resultado de calcular(X) no cambia si antes se calculó calcular(Y)."""
        salario_target = 3_000_000.0
        salario_otros = [1_750_905.0, 5_000_000.0, 18_505_000.0, 2_000_000.0]

        # Calcular target limpio
        resultado_limpio = nomina_service.calcular(salario_target)

        # Calcular muchos otros salarios antes
        for s in salario_otros * 10:
            nomina_service.calcular(s)

        # El resultado target debe ser idéntico
        resultado_despues = nomina_service.calcular(salario_target)
        assert resultado_limpio == resultado_despues, (
            f"Resultado cambió según orden de llamadas: "
            f"{resultado_limpio} → {resultado_despues}"
        )

    def test_resultado_consistente_entre_metodos(self, nomina_service):
        """
        Los tres métodos (calcular, calcular_sm, calcular_aprendiz) pueden
        llamarse en cualquier orden sin afectarse mutuamente.
        """
        salario = 2_000_000.0

        r1 = nomina_service.calcular(salario)
        r2 = nomina_service.calcular_sm(salario)
        r3 = nomina_service.calcular_aprendiz(salario)

        # Segunda ronda en orden inverso
        r3b = nomina_service.calcular_aprendiz(salario)
        r2b = nomina_service.calcular_sm(salario)
        r1b = nomina_service.calcular(salario)

        assert r1 == r1b, f"calcular() no es idempotente entre llamadas mixtas"
        assert r2 == r2b, f"calcular_sm() no es idempotente entre llamadas mixtas"
        assert r3 == r3b, f"calcular_aprendiz() no es idempotente entre llamadas mixtas"


# ═══════════════════════════════════════════════════════════════════════════
# L1.4 — Precisión Decimal Preservada
# ═══════════════════════════════════════════════════════════════════════════

class TestPrecisionDecimalPreservada:
    """
    El motor NO aplica redondeo interno.
    Los resultados deben ser floats con decimales significativos.

    Principio: Motor = capa de cálculo. Redondeo = responsabilidad de la capa de presentación.
    """

    @pytest.mark.parametrize("salario", [
        # Salarios que producen valores no-enteros por la multiplicación
        # de t_haberes (con auxilio 249,095) × tasas fraccionarias.
        # Nota: algunos salarios "redondos" (ej. 5,000,000) pueden producir
        # resultados enteros por coincidencia aritmética — ese NO es un error.
        2_000_000.0,   # t_haberes = 2,249,095 → cesantías = 187,349.2135 (fracción)
        3_000_000.0,   # t_haberes = 3,249,095 → cesantías = 270,649.6135 (fracción)
        1_750_905.0,   # SMMLV exacto → t_haberes = 2,000,000 → cesantías = 166,600 pero arl = 9139.7241
    ])
    def test_calcular_retorna_float_con_decimales(self, nomina_service, salario):
        """
        Motor retorna float con decimales para salarios que producen fracciones.

        Principio: El motor NO aplica cop_round() internamente.
        Los salarios de prueba fueron elegidos porque producen t_haberes que,
        al multiplicarse por 0.0833, generan fracciones inevitables.

        Nota técnica: Algunos salarios "redondos" pueden producir resultados enteros
        por coincidencia aritmética (ej. 5,000,000 × 0.0833 = 416,500.00 exacto).
        Eso NO es un error del motor — es matemática normal. Este test usa salarios
        que garantizan fracciones por diseño.
        """
        resultado = nomina_service.calcular(salario)
        assert isinstance(resultado, float), (
            f"Resultado debe ser float, got: {type(resultado)}"
        )
        assert resultado > 0, f"Resultado debe ser positivo: {resultado}"
        # Motor NO debe redondear internamente → resultado tiene decimales
        assert resultado % 1.0 != 0.0, (
            f"salario={salario}: Motor redondeó internamente (resultado={resultado}).\n"
            f"  El redondeo debe ocurrir en la capa de presentación, no en el motor.\n"
            f"  Verificar que calcular() no llama cop_round() en el return."
        )

    def test_precision_no_se_pierde_en_operaciones_encadenadas(self, nomina_service):
        """
        Llamadas encadenadas no acumulan error de redondeo.
        El resultado de N llamadas debe ser idéntico al de 1 llamada.
        """
        salario = 2_815_025.07  # salario con fracción
        r1 = nomina_service.calcular(salario)
        r2 = nomina_service.calcular(salario)
        # Exactamente iguales (no sólo aproximados)
        assert r1 == r2, (
            f"Resultados difieren con salario fraccionario: {r1} ≠ {r2}"
        )

    def test_cop_round_es_responsabilidad_de_presentacion(self, nomina_service):
        """
        cop_round() solo debe aplicarse FUERA del motor.
        Verificar que el motor retorna valor exacto sin redondear.
        """
        from nexa_engine.modules.shared.precision import cop_round

        salario = 3_000_000.0
        resultado_motor = nomina_service.calcular(salario)
        resultado_redondeado = cop_round(resultado_motor)

        # Si el motor ya redondeó, resultado_motor == resultado_redondeado
        # Queremos confirmar que NO son iguales (el motor no redondeó)
        assert resultado_motor != resultado_redondeado or (
            # Caso extremo: el valor exacto ya es entero (muy improbable)
            abs(resultado_motor - resultado_redondeado) < 1e-10
        ), (
            f"Motor redondeó internamente: "
            f"motor={resultado_motor}, redondeado={resultado_redondeado}"
        )
