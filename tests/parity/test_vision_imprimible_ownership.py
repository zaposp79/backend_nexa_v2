"""
FASE VISION_IMPRIMIBLE_2 - Tests de ownership y estabilidad de contrato.

Verifica:
  1. Los 15 campos del GET vision-imprimible mantienen su contrato.
  2. Los campos BUILDER_CANONICAL son consistentes entre builder y serializer.
  3. Los campos SERIALIZER_CANONICAL son mas ricos que los del builder (no regresar a builder).
  4. comparativo_escenarios sigue persistido (regresion de GAP-VIS-1).
  5. Divergencias conocidas entre builder y serializer estan documentadas y son estables.
  6. aprobaciones_requeridas removido del backend (BLOCK_25) — API field returns [].

Ownership documentado en docs/refactor/vision_imprimible_existing_module_audit.md
  Seccion: FASE VISION_IMPRIMIBLE_2 - Ownership Builder vs Serializer
"""
from __future__ import annotations

import pytest

from nexa_engine.modules.calculator_motor.serializers import (
    pricing_result_to_dict,
    pricing_result_to_visions_response,
)


# ---------------------------------------------------------------------------
# TAREA 5.1 - Contrato completo de los 15 campos del GET vision-imprimible
# ---------------------------------------------------------------------------

_GET_VISION_IMPRIMIBLE_CAMPOS = [
    "ficha_deal",
    "kpis",
    "pyg_por_mes",
    "waterfall_promedio",
    "configuracion_comercial",
    "reglas_negocio",
    "evaluacion_riesgo",
    "vision_pyg",
    "cost_to_serve",
    "vision_tarifas",
    "vision_por_servicio",
    "vision_por_canal",
    "detalle_por_canal",
    "estructura_equipo",
    "comparativo_escenarios",
]


@pytest.mark.parametrize("campo", _GET_VISION_IMPRIMIBLE_CAMPOS)
def test_documento_contiene_campo_del_get_endpoint(run_engine, canonical_input, campo):
    """El documento persistido contiene todos los campos que el GET endpoint necesita."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-contract")
    assert campo in doc, (
        f"REGRESION DE CONTRATO: campo '{campo}' ausente del documento persistido. "
        f"El GET /vision-imprimible no podra servir este campo."
    )


# ---------------------------------------------------------------------------
# TAREA 5.2 - Campos BUILDER_CANONICAL: consistencia builder <-> serializer
# ---------------------------------------------------------------------------

def test_builder_canonical_vision_por_servicio_equivale_a_doc(run_engine, canonical_input):
    """vision_por_servicio en el builder y en el doc serializado son equivalentes."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-vps")

    vi = resultado.vision_imprimible
    assert vi is not None, "VisionImprimible debe estar construida"

    # El serializer usa _vision_ejecutiva_sections() que lee de vi.vision_por_servicio
    assert len(doc["vision_por_servicio"]) == len(vi.vision_por_servicio), (
        "vision_por_servicio: conteo diferente entre builder y documento serializado"
    )
    if vi.vision_por_servicio:
        s0_builder = vi.vision_por_servicio[0]
        s0_doc = doc["vision_por_servicio"][0]
        assert s0_doc["servicio"] == s0_builder.servicio
        assert abs(s0_doc["margen"] - s0_builder.margen) < 1e-9


def test_builder_canonical_comparativo_escenarios_equivale_a_doc(run_engine, canonical_input):
    """comparativo_escenarios en el builder y en el doc serializado son equivalentes (GAP-VIS-1)."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-comp")

    vi = resultado.vision_imprimible
    assert vi is not None

    assert len(doc["comparativo_escenarios"]) == len(vi.comparativo_escenarios), (
        "comparativo_escenarios: conteo diferente entre builder y documento serializado"
    )
    if vi.comparativo_escenarios:
        ce0_builder = vi.comparativo_escenarios[0]
        ce0_doc = doc["comparativo_escenarios"][0]
        assert ce0_doc["escenario"] == ce0_builder.escenario
        assert ce0_doc["modalidad_canal"] == ce0_builder.modalidad_canal
        assert ce0_doc["modelo_cobro"] == ce0_builder.modelo_cobro


# ---------------------------------------------------------------------------
# TAREA 5.3 - Campos SERIALIZER_CANONICAL: mas ricos que builder
#             Con divergencias conocidas documentadas
# ---------------------------------------------------------------------------

def test_serializer_canonical_ficha_deal_mas_rica_que_builder(run_engine, canonical_input):
    """ficha_deal serializado tiene mas campos que FichaDelDeal del builder (NO regresionar).

    DIVERGENCIAS DOCUMENTADAS entre builder y serializer (BUILDER_ONLY => SERIALIZER_CANONICAL):
      - FichaDelDeal.servicio        => ficha_deal["linea_negocio"]    (mismo dato, diferente clave)
      - FichaDelDeal.duracion        => ficha_deal["duracion_contrato"] (diferente formato de texto)
    Los campos cliente y fecha_inicio SI son equivalentes.
    """
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-ficha")

    vi = resultado.vision_imprimible
    assert vi is not None, "VisionImprimible debe estar construida"

    doc_ficha = doc["ficha_deal"]

    # El serializer produce muchos mas campos que FichaDelDeal (4 campos del builder)
    assert len(doc_ficha) > 4, (
        "ficha_deal serializado debe tener MAS campos que FichaDelDeal del builder (4 campos). "
        "Si no, el serializer fue regresionado a la version simplificada del builder."
    )

    # cliente y fecha_inicio son equivalentes entre builder y serializer
    assert doc_ficha["cliente"] == vi.ficha.cliente
    assert doc_ficha["fecha_inicio"] == vi.ficha.fecha_inicio

    # DIVERGENCIA CONOCIDA: FichaDelDeal.servicio => ficha_deal["linea_negocio"] (mismo dato, clave diferente)
    assert "linea_negocio" in doc_ficha, (
        "DIVERGENCIA: serializer debe exponer 'linea_negocio' (no 'servicio' del builder)"
    )
    assert doc_ficha["linea_negocio"] == vi.ficha.servicio, (
        "DIVERGENCIA CONOCIDA: builder.ficha.servicio y ficha_deal['linea_negocio'] "
        "deben apuntar al mismo valor (panel.linea_negocio) aunque la clave difiere."
    )

    # DIVERGENCIA CONOCIDA: FichaDelDeal.duracion ("N meses") != ficha_deal["duracion_contrato"] (rango fechas)
    assert "duracion_contrato" in doc_ficha, "ficha_deal debe tener 'duracion_contrato'"
    # Los formatos son diferentes por diseno - el builder produce "12 meses", el serializer produce "DD/MM/YYYY a DD/MM/YYYY"
    assert vi.ficha.duracion.endswith("meses"), "FichaDelDeal.duracion debe ser formato 'N meses'"
    assert "/" in doc_ficha["duracion_contrato"], "ficha_deal.duracion_contrato debe ser rango de fechas"


def test_serializer_canonical_kpis_mas_ricos_que_economics(run_engine, canonical_input):
    """kpis serializado tiene mas campos que EconomicsDeal del builder (NO regresionar).

    DIVERGENCIAS DOCUMENTADAS:
      - EconomicsDeal.ingreso_mensual = vision_tarifas.ingreso_mensual (total del contrato)
      - kpis["ingreso_mensual"]       = kpis.ingreso_mensual (promedio mensual)
      Estos son DIFERENTES metricas aunque comparten nombre.
      - EconomicsDeal.margen          = panel.margen (EQUIVALENTE a kpis["margen"])
    """
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-kpis")

    vi = resultado.vision_imprimible
    assert vi is not None

    doc_kpis = doc["kpis"]

    # El serializer produce mas que los 5 campos de EconomicsDeal
    assert len(doc_kpis) > 5, (
        "kpis serializado debe tener MAS campos que EconomicsDeal del builder (5 campos)."
    )

    # DIVERGENCIA CONOCIDA: KPIsDeal NO tiene campo 'margen' (EconomicsDeal.margen = panel.margen)
    # El margen del deal NO esta en kpis serializado - esta en panel o configuracion_comercial
    assert "margen" not in doc_kpis, (
        "kpis serializado NO debe tener campo 'margen' (KPIsDeal no lo define). "
        "Si aparece, alguien lo agrego — verificar que no rompe contrato con frontend."
    )

    # contribucion_total SI es equivalente entre builder (EconomicsDeal) y serializer (KPIsDeal)
    assert abs(doc_kpis["contribucion_total"] - vi.economics.contribucion_total) < 1e-9, (
        "contribucion_total debe ser igual entre EconomicsDeal del builder y kpis serializado"
    )

    # DIVERGENCIA CONOCIDA: ingreso_mensual representa metricas DIFERENTES
    # EconomicsDeal.ingreso_mensual = vision_tarifas.ingreso_mensual (puede ser total del contrato)
    # kpis.ingreso_mensual          = promedio mensual calculado por KPIsCalculator
    # La divergencia es estructural — no se puede unificar sin cambiar semantica
    assert "ingreso_mensual" in doc_kpis, "kpis debe contener ingreso_mensual"
    assert doc_kpis["ingreso_mensual"] > 0, "kpis.ingreso_mensual debe ser positivo"
    assert vi.economics.ingreso_mensual > 0, "EconomicsDeal.ingreso_mensual debe ser positivo"


def test_serializer_canonical_pyg_por_mes_mas_rico_que_evolucion(run_engine, canonical_input):
    """pyg_por_mes serializado tiene mas campos que EvolucionMensual del builder."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-pyg")

    vi = resultado.vision_imprimible
    assert vi is not None

    # EvolucionMensual del builder tiene 5 arrays de escalares
    # El serializer produce objetos PyGMensual completos (muchos campos por mes)
    assert len(doc["pyg_por_mes"]) == len(vi.evolucion_mensual.meses), (
        "Conteo de meses difiere entre EvolucionMensual del builder y pyg_por_mes serializado"
    )
    if doc["pyg_por_mes"] and vi.evolucion_mensual.meses:
        mes0_doc = doc["pyg_por_mes"][0]
        # El doc tiene muchos campos por mes (mas que los 5 arrays del builder)
        assert len(mes0_doc) > 5, (
            "pyg_por_mes[0] debe tener mas de 5 campos (mas rico que EvolucionMensual)"
        )
        # ingreso_neto debe ser consistente entre builder y serializer
        assert abs(mes0_doc["ingreso_neto"] - vi.evolucion_mensual.ingresos_neto[0]) < 1e-9, (
            "ingreso_neto mes 1 difiere entre EvolucionMensual del builder y pyg_por_mes serializado"
        )
        # costo_total debe ser consistente
        assert abs(mes0_doc["costo_total"] - vi.evolucion_mensual.costos_total[0]) < 1e-9, (
            "costo_total mes 1 difiere entre EvolucionMensual del builder y pyg_por_mes serializado"
        )


# ---------------------------------------------------------------------------
# TAREA 5.4 - Regresion GAP-VIS-1: comparativo_escenarios sigue persistido
# ---------------------------------------------------------------------------

def test_comparativo_escenarios_en_doc_y_en_visions_response(run_engine, canonical_input):
    """GAP-VIS-1 regresion: comparativo_escenarios presente en doc y en POST response."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-comp2")
    response = pricing_result_to_visions_response(resultado, result_id="test-ownership-comp2r")

    assert "comparativo_escenarios" in doc, "GAP-VIS-1 regresion: ausente en doc persistido"
    assert isinstance(doc["comparativo_escenarios"], list)

    vi_response = response["vision_imprimible"]
    assert "comparativo_escenarios" in vi_response, "GAP-VIS-1 regresion: ausente en POST response"
    assert isinstance(vi_response["comparativo_escenarios"], list)


# ---------------------------------------------------------------------------
# TAREA 5.5 - Configuracion comercial: divergencia de seleccion de canal
# ---------------------------------------------------------------------------

def test_configuracion_comercial_serializer_tiene_mas_campos(run_engine, canonical_input):
    """configuracion_comercial serializado tiene mas campos que ConfiguracionComercial del builder.

    DIVERGENCIAS DOCUMENTADAS:
      - Builder selecciona canal: primer canal con ingreso_bruto > 0
      - Serializer selecciona canal: canal con mayor facturacion (_select_principal_channel)
    """
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-ownership-cc")

    vi = resultado.vision_imprimible
    assert vi is not None

    # ConfiguracionComercial del builder tiene 4 campos: modelo_cobro, tarifa_fija, tarifa_variable, canales
    # El serializer produce 12+ campos incluyendo descuento, margen_objetivo, volumen_base_mensual, etc.
    doc_cc = doc["configuracion_comercial"]
    assert "descuento" in doc_cc, "configuracion_comercial serializado debe tener 'descuento'"
    assert "margen_objetivo" in doc_cc, "configuracion_comercial serializado debe tener 'margen_objetivo'"
    assert "volumen_base_mensual" in doc_cc, "configuracion_comercial serializado debe tener 'volumen_base_mensual'"
    # Estos campos NO existen en ConfiguracionComercial del builder
    assert len(doc_cc) > 4, (
        "configuracion_comercial serializado debe tener MAS campos que ConfiguracionComercial del builder (4 campos)"
    )
    # El modelo_cobro SI debe ser el mismo (mismo canal de referencia en este caso de prueba)
    assert "modelo_cobro_principal" in doc_cc, "serializer debe tener 'modelo_cobro_principal'"


# ---------------------------------------------------------------------------
# TAREA 6 — aprobaciones_requeridas removido del backend (BLOCK_25)
# ---------------------------------------------------------------------------

def test_formula_ownership_aprobaciones_removido():
    """FORMULA_OWNERSHIP_1: aprobaciones_requeridas helper fue removido (BLOCK_25).

    Product decision: Excel "aprobaciones" is only a manual signature section
    after printing. Backend no longer computes the 3-level COP table.
    API field returns [].
    """
    import importlib.util
    spec = importlib.util.find_spec("nexa_engine.modules.vision_imprimible.helpers.aprobaciones")
    assert spec is None, (
        "BLOCK_25: modules/vision_imprimible/helpers/aprobaciones.py debe haber sido eliminado. "
        "El helper ya no es necesario."
    )


def test_formula_ownership_serializer_sin_aprobaciones():
    """Serializer_helpers ya no tiene _aprobaciones_requeridas ni UMBRAL_* constantes."""
    import inspect
    from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
    sh_src = inspect.getsource(serializer_helpers)
    assert "UMBRAL_GERENCIA_FINANCIERA_COP" not in sh_src, (
        "BLOCK_25: UMBRAL_GERENCIA_FINANCIERA_COP no debe estar en serializer_helpers"
    )
    assert "UMBRAL_GERENCIA_GENERAL_COP" not in sh_src, (
        "BLOCK_25: UMBRAL_GERENCIA_GENERAL_COP no debe estar en serializer_helpers"
    )
    assert "UMBRAL_ALTA_DIRECCION_COP" not in sh_src, (
        "BLOCK_25: UMBRAL_ALTA_DIRECCION_COP no debe estar en serializer_helpers"
    )
    assert "_aprobaciones_requeridas" not in sh_src, (
        "BLOCK_25: _aprobaciones_requeridas wrapper no debe estar en serializer_helpers"
    )


# ---------------------------------------------------------------------------
# FORMULA_OWNERSHIP_2 — F-01: ficha_deal_to_dict vive en modules/vision_imprimible
# ---------------------------------------------------------------------------

def test_formula_ownership_2_ficha_vive_en_vision_imprimible(run_engine, canonical_input):
    """FORMULA_OWNERSHIP_2: ficha_deal_to_dict pertenece a modules/vision_imprimible.

    Verifica:
    1. Helper importable desde modules/vision_imprimible.helpers.ficha.
    2. Output idéntico al del serializer (contrato público sin cambio).
    3. Serializer solo contiene wrapper — no duplica la lógica de fechas.
    4. fecha_fin, duracion_contrato, mes_finalizacion están presentes y son coherentes.
    """
    import inspect
    from nexa_engine.modules.vision_imprimible.helpers.ficha import ficha_deal_to_dict

    resultado = run_engine(canonical_input)
    panel = resultado.panel

    # 1. Output del helper directo
    ficha = ficha_deal_to_dict(panel)
    assert isinstance(ficha, dict)

    # 2. Campos canónicos presentes
    for campo in ("cliente", "fecha_inicio", "fecha_fin", "duracion_contrato",
                  "meses_contrato", "mes_finalizacion", "linea_negocio", "divisa",
                  "tasa_ica", "tasa_gmf", "cadenas_activas"):
        assert campo in ficha, f"FORMULA_OWNERSHIP_2: campo '{campo}' ausente de ficha_deal_to_dict"

    # 3. Coherencia de fecha_fin con fecha_inicio + meses_contrato
    from datetime import datetime
    fi = datetime.strptime(panel.fecha_inicio, "%Y-%m-%d")
    ff = datetime.strptime(ficha["fecha_fin"], "%Y-%m-%d")
    # fecha_fin debe estar en el rango [meses-1, meses+1] meses después del inicio
    delta_meses = (ff.year - fi.year) * 12 + (ff.month - fi.month)
    assert abs(delta_meses - (panel.meses_contrato - 1)) <= 1, (
        f"FORMULA_OWNERSHIP_2: fecha_fin ({ficha['fecha_fin']}) no coherente con "
        f"fecha_inicio ({panel.fecha_inicio}) + {panel.meses_contrato} meses"
    )

    # 4. duracion_contrato contiene el rango formateado
    assert " a " in ficha["duracion_contrato"], (
        "duracion_contrato debe ser rango 'DD/MM/YYYY a DD/MM/YYYY'"
    )
    assert ficha["divisa"] == "COP"

    # 5. Serializer NO contiene la lógica de derivación de fechas (delegó)
    from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
    src = inspect.getsource(serializer_helpers)
    assert "datetime.strptime" not in src, (
        "FORMULA_OWNERSHIP_2: serializer_helpers no debe contener datetime.strptime. "
        "La lógica de fechas debe vivir en modules/vision_imprimible/helpers/ficha.py"
    )
    assert "calendar.monthrange" not in src, (
        "FORMULA_OWNERSHIP_2: serializer_helpers no debe contener calendar.monthrange"
    )

    # 6. Output del helper == output del serializer (contrato sin cambio)
    from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
    doc = pricing_result_to_dict(resultado, result_id="test-fo2-ficha")
    doc_ficha = doc["ficha_deal"]
    assert doc_ficha["fecha_fin"]         == ficha["fecha_fin"]
    assert doc_ficha["duracion_contrato"] == ficha["duracion_contrato"]
    assert doc_ficha["mes_finalizacion"]  == ficha["mes_finalizacion"]
    assert doc_ficha["cliente"]           == ficha["cliente"]


def test_formula_ownership_2_fecha_fin_parse_falla_devuelve_none():
    """_derivar_fechas con fecha_inicio inválida devuelve (None, None, None) sin crash."""
    from nexa_engine.modules.vision_imprimible.helpers.ficha import _derivar_fechas

    fecha_fin, duracion, mes_fin = _derivar_fechas("INVALID-DATE", 12)
    assert fecha_fin is None,  "fecha inválida → fecha_fin=None (no crash)"
    assert duracion is None,   "fecha inválida → duracion_contrato=None"
    assert mes_fin is None,    "fecha inválida → mes_finalizacion=None"


# ---------------------------------------------------------------------------
# FORMULA_OWNERSHIP_3 — F-03+F-04: configuracion_comercial vive en modules/vision_imprimible
# ---------------------------------------------------------------------------

def test_formula_ownership_3_select_principal_channel_vive_en_vision_imprimible():
    """FORMULA_OWNERSHIP_3/F-03: select_principal_channel pertenece a modules/vision_imprimible.

    Verifica:
    1. Importable desde modules/vision_imprimible.helpers.configuracion_comercial.
    2. Selecciona el canal con mayor facturación (max).
    3. Lanza ValueError en lista vacía — no default silencioso.
    """
    import pytest as _pytest
    from nexa_engine.modules.vision_imprimible.helpers.configuracion_comercial import (
        select_principal_channel,
    )

    class _Canal:
        def __init__(self, nombre, facturacion):
            self.nombre = nombre
            self.facturacion = facturacion

    canales = [_Canal("A", 100.0), _Canal("B", 300.0), _Canal("C", 200.0)]
    principal = select_principal_channel(canales)
    assert principal.nombre == "B", (
        "F-03: select_principal_channel debe retornar el canal con mayor facturación"
    )

    with _pytest.raises(ValueError, match="CONFIGURACIÓN COMERCIAL INCOMPLETA"):
        select_principal_channel([])


def test_formula_ownership_3_configuracion_comercial_vive_en_vision_imprimible(
    run_engine, canonical_input
):
    """FORMULA_OWNERSHIP_3/F-04: configuracion_comercial_to_dict pertenece a modules/vision_imprimible.

    Verifica:
    1. Helper importable desde modules/vision_imprimible.helpers.configuracion_comercial.
    2. Output idéntico al del serializer (contrato público sin cambio).
    3. Serializer no contiene la fórmula tarifa_fija inline.
    4. Los 12 campos canónicos de sección 03 están presentes.
    """
    import inspect
    from nexa_engine.modules.vision_imprimible.helpers.configuracion_comercial import (
        configuracion_comercial_to_dict,
    )

    resultado = run_engine(canonical_input)

    # 1. Output del helper directo
    cc = configuracion_comercial_to_dict(resultado)
    assert isinstance(cc, dict), "configuracion_comercial_to_dict debe retornar dict"

    # 2. Los 12 campos canónicos de VI sección 03
    campos_esperados = [
        "modelo_cobro_principal", "pct_fijo_global", "pct_variable_global",
        "tarifa_fija", "tarifa_variable", "descuento", "margen_objetivo",
        "volumen_base_mensual", "ingreso_mensual", "costo_mensual_total",
        "valor_total_deal",
    ]
    for campo in campos_esperados:
        assert campo in cc, (
            f"FORMULA_OWNERSHIP_3: campo '{campo}' ausente de configuracion_comercial_to_dict"
        )

    # 3. Output del helper == output del serializer (contrato sin cambio)
    from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
    doc = pricing_result_to_dict(resultado, result_id="test-fo3-cc")
    doc_cc = doc["configuracion_comercial"]
    for campo in campos_esperados:
        assert doc_cc[campo] == cc[campo], (
            f"FORMULA_OWNERSHIP_3: campo '{campo}' difiere entre helper directo y serializer. "
            "La delegación debe producir output idéntico."
        )

    # 4. Serializer NO contiene la fórmula tarifa_fija inline (delegó)
    from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
    src = inspect.getsource(serializer_helpers)
    # La fórmula inline "facturacion * pct_fijo" no debe estar en serializer_helpers
    assert "facturacion * pct_fijo" not in src, (
        "FORMULA_OWNERSHIP_3: serializer_helpers no debe contener 'facturacion * pct_fijo' inline. "
        "La fórmula tarifa_fija debe vivir en modules/vision_imprimible/helpers/configuracion_comercial.py"
    )
    # La lógica de selección max() también debe haber delegado
    assert "max(canales, key=lambda c: c.facturacion)" not in src, (
        "FORMULA_OWNERSHIP_3: serializer_helpers no debe contener max(canales) inline. "
        "F-03 debe vivir en modules/vision_imprimible/helpers/configuracion_comercial.py"
    )


# ---------------------------------------------------------------------------
# FORMULA_OWNERSHIP_4 — F-02: reglas_negocio_to_dict vive en modules/vision_imprimible
# ---------------------------------------------------------------------------

def test_formula_ownership_4_reglas_negocio_vive_en_vision_imprimible(
    run_engine, canonical_input
):
    """FORMULA_OWNERSHIP_4/F-02: reglas_negocio_to_dict pertenece a modules/vision_imprimible.

    Verifica:
    1. Helper importable desde modules/vision_imprimible.helpers.reglas_negocio.
    2. Output idéntico al del serializer (contrato público sin cambio).
    3. Campos canónicos presentes: alerta.activa, alerta.mensaje, costo_total, valor_total_deal, reglas.
    4. Serializer no contiene la lógica de alerta inline.
    """
    import inspect
    from nexa_engine.modules.vision_imprimible.helpers.reglas_negocio import (
        reglas_negocio_to_dict,
    )

    resultado = run_engine(canonical_input)
    reglas = resultado.reglas_negocio or []

    # 1. Output del helper directo
    rn = reglas_negocio_to_dict(reglas, resultado)
    assert isinstance(rn, dict)

    # 2. Campos canónicos presentes
    assert "alerta" in rn, "F-02: campo 'alerta' ausente"
    assert "activa" in rn["alerta"], "F-02: campo 'alerta.activa' ausente"
    assert "mensaje" in rn["alerta"], "F-02: campo 'alerta.mensaje' ausente"
    assert "costo_total" in rn, "F-02: campo 'costo_total' ausente"
    assert "valor_total_deal" in rn, "F-02: campo 'valor_total_deal' ausente"
    assert "reglas" in rn, "F-02: campo 'reglas' ausente"
    assert isinstance(rn["reglas"], list), "F-02: 'reglas' debe ser lista"

    # 3. Output del helper == output del serializer (contrato sin cambio)
    from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
    doc = pricing_result_to_dict(resultado, result_id="test-fo4-rn")
    doc_rn = doc["reglas_negocio"]
    assert doc_rn["alerta"]["activa"]  == rn["alerta"]["activa"],  "alerta.activa difiere"
    assert doc_rn["alerta"]["mensaje"] == rn["alerta"]["mensaje"], "alerta.mensaje difiere"
    assert doc_rn["costo_total"]       == rn["costo_total"],       "costo_total difiere"
    assert doc_rn["valor_total_deal"]  == rn["valor_total_deal"],  "valor_total_deal difiere"
    assert len(doc_rn["reglas"])       == len(rn["reglas"]),       "conteo de reglas difiere"

    # 4. Serializer NO contiene la lógica de alerta inline (delegó)
    from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
    src = inspect.getsource(serializer_helpers)
    assert "alerta_activa = requiere_aprobacion" not in src, (
        "FORMULA_OWNERSHIP_4: serializer_helpers no debe contener 'alerta_activa = requiere_aprobacion'. "
        "La lógica de alerta debe vivir en modules/vision_imprimible/helpers/reglas_negocio.py"
    )
    assert "reglas_fuera_rango = [r for r in reglas" not in src, (
        "FORMULA_OWNERSHIP_4: serializer_helpers no debe contener el filtro de reglas_fuera_rango inline. "
        "F-02 debe vivir en modules/vision_imprimible/helpers/reglas_negocio.py"
    )


def test_formula_ownership_4_alerta_mensaje_usa_alta_direccion():
    """F-02 BP-01: alerta_mensaje para aprobación requerida usa 'Alta Dirección' (Excel V2-7)."""
    from dataclasses import dataclass, field

    from nexa_engine.modules.vision_imprimible.helpers.reglas_negocio import (
        reglas_negocio_to_dict,
    )
    from nexa_engine.modules.shared.models import ReglaNegocios

    @dataclass
    class _MockKpis:
        costo_total_contrato: float = 1_000_000.0
        valor_total_deal: float     = 2_000_000.0

    @dataclass
    class _MockEv:
        requiere_aprobacion: bool = True

    @dataclass
    class _MockResultado:
        evaluacion_riesgo: _MockEv = field(default_factory=_MockEv)
        kpis: _MockKpis            = field(default_factory=_MockKpis)

    resultado = _MockResultado()
    rn = reglas_negocio_to_dict([], resultado)

    assert rn["alerta"]["activa"] is True, "alerta debe estar activa si requiere_aprobacion=True"
    assert "Alta Dirección" in rn["alerta"]["mensaje"], (
        "BP-01: alerta_mensaje debe contener 'Alta Dirección' (no 'GERENCIA GENERAL')"
    )
    assert "GERENCIA GENERAL" not in rn["alerta"]["mensaje"], (
        "BP-01: 'GERENCIA GENERAL' es nomenclatura obsoleta — debe ser 'Alta Dirección'"
    )


def test_formula_ownership_4_alerta_inactiva_si_todo_dentro_rango():
    """F-02: alerta.activa=False cuando todas las reglas están dentro_rango y no requiere aprobación."""
    from dataclasses import dataclass, field

    from nexa_engine.modules.vision_imprimible.helpers.reglas_negocio import (
        reglas_negocio_to_dict,
    )
    from nexa_engine.modules.shared.models import ReglaNegocios

    @dataclass
    class _MockKpis:
        costo_total_contrato: float = 500_000.0
        valor_total_deal: float     = 900_000.0

    @dataclass
    class _MockEv:
        requiere_aprobacion: bool = False

    @dataclass
    class _MockResultado:
        evaluacion_riesgo: _MockEv = field(default_factory=_MockEv)
        kpis: _MockKpis            = field(default_factory=_MockKpis)

    resultado = _MockResultado()
    # Todas las reglas "dentro_rango"
    reglas = [
        ReglaNegocios(
            nombre="margen_minimo", label="Margen mínimo", status="dentro_rango",
            aplicado=0.30, min_valor=0.20, max_valor=None, monto=0.0,
        ),
    ]
    rn = reglas_negocio_to_dict(reglas, resultado)

    assert rn["alerta"]["activa"]  is False, "alerta debe ser inactiva cuando todo está dentro_rango"
    assert rn["alerta"]["mensaje"] == "",    "mensaje debe ser vacío cuando no hay alerta"
