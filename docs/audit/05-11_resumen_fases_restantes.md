# Resumen de Fases 5-11 — Plan de Auditoría e Implementación

**Versión**: 2026-05-21  
**Objetivo**: Resumen consolidado de fases restantes basado en hallazgos de Fases 1-4.

---

## Fase 5: Auditoría de Calculadoras vs Excel

### Objetivo
Confirmar que cada fórmula en Excel se reproduce exactamente en Python.

### Método
1. Mapear cada sheet del Excel de referencia a calculadora Python
2. Validar: redondeos, orden de operaciones, aplicación de condicionales
3. Crear matriz: Fórmula Excel → Implementación Python → Test de reproducibilidad

### Hallazgos Esperados
- ✓ NominaCalculator reproduce exactamente salarios y cargas
- ✓ CostosFinancierosCalculator aplica gross-up correctamente
- ✓ PyGCalculator acumula mes a mes sin errores de redondeo
- ⚠️ Posibles discrepancias en orden de aplicación de impuestos/descuentos

### Archivos a Auditar
- Excel de referencia (docs/ o reports/)
- `calculators/nomina.py`
- `calculators/costos_financieros.py`
- `calculators/pyg.py`
- `calculators/kpis.py`
- `domain/services/nomina_cargada.py`

### Salida Esperada
Matriz de trazabilidad: 1 fila por fórmula Excel
- Cell reference Excel
- Fórmula original
- Implementación Python (archivo:línea)
- Test case que valida
- ¿Resultado coincide?

### Esfuerzo Estimado
3-4 días (20+ fórmulas)

---

## Fase 6: Auditoría de Visiones (Reports, Desgloses)

### Objetivo
Confirmar que visiones no tienen lógica desacoplada y solo consumen de calculadoras oficiales.

### Hallazgos Esperados
- ✓ VisionPyGBuilder: Simplemente serializa PyGMensual
- ⚠️ VisionTarifasCalculator: Calcula nomina_loaded_ch sin modelo base
- ⚠️ VisionTarifasCalculator: Usa alias innecesarios (producto, salario_variable)
- ⚠️ CostToServeCalculator: Recalcula FTE en lugar de referencia consolidada
- ✓ RiesgoCalculator: Inputs vienen de domain, no hardcodes

### Matriz de Visiones

| Visión | Entrada | Operación | Salida | Problema |
|--------|---------|-----------|--------|----------|
| VisionPyGBuilder | PyGMensual, KPIsDeal | Serialización estructurada | VisionPyG | ✓ OK |
| VisionTarifasCalculator | PyGMensual, Perfiles | Mapeo y cálculo de CTS por canal | TarifaCanal[] | ⚠️ nomina_loaded recalculada |
| CostToServeCalculator | PyGMensual, Perfiles | Desglose FTE y CTS | ResultadoCostToServe | ⚠️ FTE recalculado |
| RiesgoCalculator | Panel, KPIs, PyG, Perfiles | Evaluación de criterios | EvaluacionRiesgo | ✓ OK |

### Archivos a Auditar
- `calculators/vision_tarifas.py` (problema: nomina_loaded)
- `calculators/vision_pyg.py`
- `calculators/cost_to_serve.py`
- `calculators/riesgo.py`

### Salida Esperada
Lista de inconsistencias lógicas + plan de corrección

### Esfuerzo Estimado
2 días

---

## Fase 7: Auditoría de Endpoints y Contratos

### Objetivo
Confirmar que endpoints responden con datos recalculados, consistentes, y alineados con domain models.

### Hallazgos Esperados
- ✓ GET /simulation/{result_id}/results → PricingResult completo
- ✓ Todos los fields son derivados de cálculos (no precalculados)
- ⚠️ Nombres inconsistentes (canal vs producto)
- ⚠️ Campos faltantes (vol_cadena_a_mensual no expuesto)
- ⚠️ Campos ignorados de entry_data no documentados

### Endpoints a Auditar

| Endpoint | Responsabilidad | Fields Expuestos | Fuente | Status |
|----------|---|---|---|---|
| GET /results | Resultado completo | 15+ tipos | PricingResult | ✓ OK |
| GET /results/kpis | KPIs del deal | tarifa, facturación, etc. | KPIsDeal | ✓ OK |
| GET /results/pyg | PyG mes a mes | ingreso, costo, utilidad | PyGMensual[] | ✓ OK |
| GET /results/cost-to-serve | CTS por cadena | fte, payroll, cts | ResultadoCostToServe | ✓ OK |
| GET /results/vision-tarifas | Tarifas por canal | payroll_ch, vol, tarifa | VisionTarifas | ⚠️ Alias campos |

### Validación de Contrato

Para cada endpoint:
1. ¿Fields coinciden con domain models?
2. ¿Son derivados o precalculados?
3. ¿Nomenclatura alineada con entry_data?
4. ¿Documentados?

### Archivos a Auditar
- `api/v1/simulation/results_router.py`
- `api/v1/simulation/calculate_router.py`
- `adapters/pricing_serializer.py`
- Domain models (para comparar fields)

### Salida Esperada
Matriz de endpoints: 1 fila por endpoint
- Ruta
- Fields expuestos
- Origen (calculadora/visión)
- Nombre correcto
- Documentado

### Esfuerzo Estimado
1-2 días

---

## Fase 8: Estandarización Nomenclatural (Implementación)

### Objetivo
Corregir inconsistencias de nombres identificadas en Fase 3.

### Cambios Prioritarios

| Cambio | Severidad | Archivos | Tests |
|--------|---|---|---|
| Agregar `nomina_loaded` a ResultadoNomina | CRÍTICA | domain, calculators, vision_tarifas | +2 |
| Renombrar `seguridad` → `estudios_seguridad` | CRÍTICA | domain, calculators | +1 |
| Cambiar endpoint `producto` → `canal` | CRÍTICA | endpoints, serializer | +1 |
| Agregar campos perdidos (rubro, tipo_de_cobro, tipo_de_gasto) | ALTA | domain, context_builder | +1 |
| Estandarizar suffix documentation | MEDIA | docs | 0 |
| Decidir vol_cadena_a_mensual exposure | BAJA | endpoint | 0 |

### Esfuerzo Estimado
2-3 días (cambios de código + tests)

---

## Fase 9: Migración de Parametrización (config/ → storage/)

### Objetivo
Centralizar toda parametrización en storage/, eliminar hardcodes, lograr single source of truth.

### Plan Detallado en: 02_parametrization_audit.md

### Resumen
- **Fase A**: Crear estructura storage/business_rules/ (0.5 días)
- **Fase B**: Actualizar ParametrizationProvider (0.5 días)
- **Fase C**: Eliminar hardcodes de riesgo.py (1 día)
- **Fase D**: Crear endpoints upload/activate (1 día)
- **Fase E**: Eliminar config/ (1 día)
- **Tests**: Reproducibilidad (1 día)

### Esfuerzo Estimado
5 días totales

---

## Fase 10: Documentación de Trazabilidad Completa

### Objetivo
Generar matriz final que muestre trazabilidad 100% de cada fórmula.

### Salidas Esperadas

**10.1 Fórmulas Auditadas**
- 1 documento por fórmula Excel importante
- Cell reference, descripción, variables, implementación Python, test

**10.2 Campos Entrada → Salida**
- Matriz: campo entry_data → transformación → campo endpoint
- 1 fila por campo importante (40+)

**10.3 Arquitectura de Cálculo**
- Diagramas Mermaid (flujo, dependencias)
- Descripción de pipeline
- Referencias a archivos

### Ubicación
Crear directorio `/docs/traceability/` con archivos:
```
docs/traceability/
├── README.md (índice y guía)
├── formulas_auditadas/
│   ├── nomina_calculada.md
│   ├── costo_financiero_ica.md
│   ├── costo_financiero_gmf.md
│   └── ... (20+ fórmulas)
├── campos_entrada_salida.md (matriz)
└── arquitectura_calculo.md (diagramas)
```

### Esfuerzo Estimado
3-4 días (documentación exhaustiva)

---

## Fase 11: Validación de Single Source of Truth

### Objetivo
Confirmar que sistema es 100% reproducible usando SOLO entry_data + storage + calculadoras.

### Validaciones

**11.1 Eliminación de Precálculos**
- ✓ No existen valores constantes en responses
- ✓ Todo se recalcula dinámicamente

**11.2 Eliminación de Hardcodes**
- ✓ Todos los valores están en parametrización (storage/)
- ✓ No existen constantes sin documentar

**11.3 Reproducibilidad**
- ✓ Same input → Same output (siempre)
- ✓ Resultados no dependen de estado externo

**11.4 Trazabilidad**
- ✓ Cada valor en resultado puede remontarse a entrada y fórmula
- ✓ Documentación completa

### Tests de Reproducibilidad

```python
# Test suite: reproducibility_tests.py

def test_identical_input_produces_identical_output():
    """Same deal → Same result every time"""
    request = load_test_case("bancamia_canonical_k50.json")
    
    result1 = engine.calcular(request)
    result2 = engine.calcular(request)
    
    assert result1 == result2  # Bit-for-bit identical

def test_parametrization_versioning():
    """Changing active version changes results predictably"""
    request = load_test_case(...)
    
    # Use version A
    provider.activate_hr_version("version_a")
    result_a = engine.calcular(request)
    
    # Use version B
    provider.activate_hr_version("version_b")
    result_b = engine.calcular(request)
    
    # Results are different (expected), but reproducible
    assert result_a.kpis.tarifa != result_b.kpis.tarifa
    
def test_traceability_chain():
    """Can trace every value from input to output"""
    request = load_test_case(...)
    result = engine.calcular(request)
    
    # Pick a random value in result
    value = result.pyg_por_mes[0].payroll_a
    
    # Trace back to entry_data and formula
    tracer = Tracer()
    origin = tracer.trace(value)
    
    assert origin.input_field == "condiciones_cadena_a.perfiles[0].fte"
    assert origin.formula == "NominaCalculator.calcular() línea 42"
    assert origin.calculation_step == "salario_base × (1 + aportes)"
```

### Esfuerzo Estimado
2 días (tests + validación)

---

## Resumen Ejecutivo: Fases 5-11

### Total de Esfuerzo
- Fase 5 (Calculadoras vs Excel): 3-4 días
- Fase 6 (Visiones): 2 días
- Fase 7 (Endpoints): 1-2 días
- Fase 8 (Estandarización nomenclatural): 2-3 días
- Fase 9 (Migración parametrización): 5 días
- Fase 10 (Documentación trazabilidad): 3-4 días
- Fase 11 (Validación SSoT): 2 días

**TOTAL**: 18-23 días de trabajo

### Prioridad de Implementación

1. **CRÍTICA** (hacer primero):
   - Fase 8: Estandarización nomenclatural (arregla codebase inmediatamente)
   - Fase 9: Migración parametrización (elimina duplicados críticos)

2. **ALTA** (hacer segundo):
   - Fase 5: Auditoría vs Excel (valida correctness)
   - Fase 4: Validación cadenas (fix bugs potenciales)

3. **MEDIA** (hacer tercero):
   - Fase 6: Visiones (claridad)
   - Fase 7: Endpoints (contrato frontend)

4. **BAJA** (documentación):
   - Fase 10: Trazabilidad (auditoría externa)
   - Fase 11: Validación SSoT (confirmación final)

---

## Conclusión

Las Fases 1-4 han completado la auditoría de:
- ✓ Flujo completo y arquitectura
- ✓ Parametrización (duplicados, hardcodes)
- ✓ Nomenclatura (inconsistencias)
- ✓ Activación de cadenas (validación)

Las Fases 5-11 cubren:
- ✓ Validación de fórmulas contra Excel
- ✓ Auditoría de lógica en visiones y endpoints
- ✓ Estandarización de nombres (implementación)
- ✓ Migración a single source of truth
- ✓ Documentación exhaustiva de trazabilidad
- ✓ Validación final de reproducibilidad

**Recomendación Final**: Proceder con Fase 8 (Estandarización) y Fase 9 (Migración) de forma paralela, seguidas por Fase 4 (Validación de Cadenas) como fixes críticos.
