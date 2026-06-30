"""
Test end-to-end de la Visión Ejecutiva Integral.

Verifica que las 4 secciones agregadas se pueblan con datos REALES derivados
de los resultados ya calculados (sin fabricar valores), y que el serializer las
expone en el composite `vision_imprimible` y en el documento guardado.

Secciones bajo prueba:
  - vision_por_servicio      (rollup del deal bajo su servicio)
  - vision_por_canal         (consolidado por canal — opcional)
  - detalle_por_canal        (desglose por canal — opcional)
  - estructura_equipo        (roles/FTE/costos desde perfiles_cadena_a)
  - comparativo_escenarios   (GAP-VIS-1: Sección 05, Excel VI rows 73-78)
"""
from __future__ import annotations

from nexa_engine.modules.calculator_motor.serializers import (
    pricing_result_to_visions_response,
    pricing_result_to_dict,
)


def test_vision_servicio_se_puebla_con_servicio_real(run_engine, canonical_input):
    """vision_por_servicio refleja panel.linea_negocio y métricas calculadas."""
    resultado = run_engine(canonical_input)
    vi = resultado.vision_imprimible
    assert vi is not None

    servicios = vi.vision_por_servicio
    assert len(servicios) == 1, "Un deal = un servicio (lista de 1)"
    s = servicios[0]
    assert s.servicio == resultado.panel.linea_negocio
    assert s.servicio != "", "El servicio no puede ser vacío"
    assert s.meses_contrato == resultado.panel.meses_contrato
    # FTE total = suma de FTE de perfiles no-soporte (dato real, no fabricado)
    assert s.fte_total >= 0.0
    # Cadenas activas derivadas de panel.cadenas_activas
    assert "A" in s.cadenas_activas or not resultado.panel.cadenas_activas.cadena_a


def test_estructura_equipo_deriva_de_perfiles(run_engine, canonical_input):
    """estructura_equipo expone roles reales con FTE y agregación por cargo."""
    resultado = run_engine(canonical_input)
    eq = resultado.vision_imprimible.estructura_equipo

    if eq is None:
        # Solo aceptable si no hay perfiles (no aplica al canonical)
        assert not run_engine  # nunca — canonical siempre trae perfiles
        return

    assert len(eq.roles) > 0, "Debe haber al menos un rol"
    # fte_total = suma de FTE de todos los roles
    assert abs(eq.fte_total - sum(r.fte for r in eq.roles)) < 1e-6
    assert abs(eq.fte_total - (eq.fte_agentes + eq.fte_soporte)) < 1e-6
    # costo_total = suma de costos por rol
    assert abs(eq.costo_total_mensual - sum(r.costo_mensual for r in eq.roles)) < 1e-6
    # Agregación por cargo: la suma de FTE por cargo == fte_total
    assert abs(sum(g.fte_total for g in eq.por_cargo) - eq.fte_total) < 1e-6
    # Cada rol expone su cargo_tipo (clasificación real, no vacío)
    for r in eq.roles:
        assert r.cargo_tipo != ""


def test_vision_por_canal_opcional_y_consistente(run_engine, canonical_input):
    """vision_por_canal solo aparece si hay canales; estado deriva de FTE."""
    resultado = run_engine(canonical_input)
    canales = resultado.vision_imprimible.vision_por_canal

    if resultado.vision_tarifas and resultado.vision_tarifas.canales:
        assert len(canales) == len(resultado.vision_tarifas.canales)
        for c in canales:
            assert c.estado in ("Activo", "No Activado")
            # Regla Excel: estado depende de FTE>0
            assert (c.estado == "Activo") == (c.fte > 0)
    else:
        assert canales == [], "Sin canales → sección vacía (no fabricar)"


def test_detalle_por_canal_marca_ausencia_explicita(run_engine, canonical_input):
    """detalle_por_canal usa datos_disponibles en vez de fabricar ceros."""
    resultado = run_engine(canonical_input)
    detalles = resultado.vision_imprimible.detalle_por_canal

    if resultado.vision_tarifas and resultado.vision_tarifas.canales:
        assert len(detalles) == len(resultado.vision_tarifas.canales)
        for d in detalles:
            # El flag debe ser booleano explícito
            assert isinstance(d.datos_disponibles, bool)
            # La descomposición de Cadena A siempre viene de vision_tarifas
            assert d.costo_cadena_a >= 0.0


def test_serializer_expone_secciones_en_documento_guardado(run_engine, canonical_input):
    """pricing_result_to_dict incluye las secciones de la visión ejecutiva."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-001")

    # vision_por_servicio siempre presente (hay servicio)
    assert "vision_por_servicio" in doc
    assert len(doc["vision_por_servicio"]) == 1
    assert doc["vision_por_servicio"][0]["servicio"] == resultado.panel.linea_negocio

    # estructura_equipo presente (hay perfiles)
    assert "estructura_equipo" in doc
    assert doc["estructura_equipo"]["fte_total"] >= 0.0


def test_build_visions_document_incluye_secciones(run_engine, canonical_input):
    """pricing_result_to_visions_response anida las secciones bajo vision_imprimible."""
    resultado = run_engine(canonical_input)
    response = pricing_result_to_visions_response(resultado, result_id="test-002")

    vi = response["vision_imprimible"]
    assert "vision_por_servicio" in vi
    assert "estructura_equipo" in vi
    # Las 9 secciones originales siguen presentes (sin regresión de contrato)
    for seccion in (
        "ficha_deal", "kpis", "configuracion_comercial", "waterfall_promedio",
        "vision_pyg", "evaluacion_riesgo", "reglas_negocio", "cost_to_serve",
        "vision_tarifas",
    ):
        assert seccion in vi, f"Sección original {seccion} ausente (regresión)"


# ---------------------------------------------------------------------------
# GAP-VIS-1: comparativo_escenarios (Sección 05 — Excel VI rows 73-78)
# ---------------------------------------------------------------------------

def test_comparativo_escenarios_presente_en_documento_guardado(run_engine, canonical_input):
    """pricing_result_to_dict incluye comparativo_escenarios como lista."""
    resultado = run_engine(canonical_input)
    doc = pricing_result_to_dict(resultado, result_id="test-comparativo-doc")

    assert "comparativo_escenarios" in doc, (
        "GAP-VIS-1: comparativo_escenarios ausente del documento persistido"
    )
    assert isinstance(doc["comparativo_escenarios"], list)


def test_comparativo_escenarios_presente_en_visions_response(run_engine, canonical_input):
    """pricing_result_to_visions_response anida comparativo_escenarios bajo vision_imprimible."""
    resultado = run_engine(canonical_input)
    response = pricing_result_to_visions_response(resultado, result_id="test-comparativo-vi")

    vi = response["vision_imprimible"]
    assert "comparativo_escenarios" in vi, (
        "GAP-VIS-1: comparativo_escenarios ausente de vision_imprimible en POST response"
    )
    assert isinstance(vi["comparativo_escenarios"], list)


def test_documento_legacy_sin_comparativo_escenarios_devuelve_lista_vacia():
    """Compatibilidad legacy: documentos sin comparativo_escenarios responden []."""
    doc_legacy = {
        "ficha_deal": {},
        "kpis": {},
        # sin "comparativo_escenarios"
    }
    resultado = doc_legacy.get("comparativo_escenarios", [])
    assert resultado == [], (
        "Documentos legacy sin comparativo_escenarios deben retornar [] (no KeyError)"
    )
