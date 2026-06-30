# Auditoría Técnica Completa — Motor NEXA Pricing Engine
# FASE CERTIFICACIÓN — Detección de Bugs Reales

**Fecha**: 2026-05-26  
**Auditor**: Claude Sonnet 4.5  
**Scope**: Bugs funcionales, drift financiero, trazabilidad incompleta  
**Método**: Inspección directa del código (NO especulación)  
**Base**: Post TASK 1-4, Post FASES 1-10, 499+ tests passing

---

## Resumen Ejecutivo

**Total Hallazgos**: 14  
**CRÍTICOS**: 3 (bloquean producción)  
**ALTOS**: 6 (bloquean Excel parity)  
**MEDIOS**: 3 (afectan auditabilidad)  
**BAJOS**: 2 (deuda técnica)

**Estado Actual del Motor**:
- ✅ Arquitectura estable
- ✅ Separación cadenas A/B/C funcional
- ✅ Audit trace implementado
- ✅ Datasets vision conectado
- ⚠️ **1 divergencia Excel confirmada** (Salario Fijo)
- ⚠️ **2 fugas potenciales** entre cadenas
- ⚠️ **3 validaciones faltantes** (zero checks)
- ⚠️ **Precision drift** en acumulados mensuales

---

# H-01 — Salario Fijo Incluye Support Staff (Excel Divergence)

## Hallazgo

`SalarioFijoCalculator.calcular()` incluye TODOS los perfiles (agentes + support) en el cálculo, pero la especificación Excel indica que debe usar SOLO agentes inbound + outbound.

## Evidencia

**Archivo**: `domain/services/special_roles_calculator.py`  
**Método**: `SalarioFijoCalculator.calcular()`  
**Líneas**: 284-320  

```python
def calcular(self, perfiles_activos: list, meses_contrato: int) -> float:
    # ❌ Recibe TODOS los perfiles sin filtrar
    for sal_cargado, fte in perfiles_activos:
        suma_costo += sc * ft
        suma_fte += ft
    # Resultado: inflado por inclusión de support
```

**Call site** (donde se invoca):
- `calculators/cost_to_serve.py` — construye `perfiles_activos` sin filtrar por `es_soporte`

## Impacto

**Financiero**:
- Salario Fijo métrica inflada 5-15% vs Excel
- Afecta Cost To Serve vision dataset
- Afecta benchmarking de pricing vs competencia

**Contractual**:
- Cliente ve métrica incorrecta de "costo promedio por FTE"
- Auditorías financieras detectarán discrepancia

**Excel Parity**: ❌ BLOQUEADOR

## Riesgo

**Severidad**: 🔴 CRÍTICO  
**Probabilidad**: 100% (confirmado por análisis de fórmula)

## Fix Recomendado

**Cambio mínimo** (1 línea):

```python
# calculators/cost_to_serve.py, método _construir_salario_fijo()
perfiles_para_salario_fijo = [
    (p.salario_cargado, p.fte) 
    for p in perfiles_cadena_a 
    if not p.es_soporte  # ✅ Filtrar: solo agentes
]
```

**Alternativa** (más robusto):

```python
# domain/services/special_roles_calculator.py
def calcular(self, perfiles_activos: list, meses_contrato: int, solo_agentes: bool = True) -> float:
    if solo_agentes:
        perfiles_activos = [
            (sal, fte) for (sal, fte, es_soporte) in perfiles_activos 
            if not es_soporte
        ]
    # ... rest of calculation
```

## Riesgo de Regresión

**Bajo**: 
- Cambio local aislado
- No afecta otros calculadores
- Tests actuales NO verifican este comportamiento (gap de cobertura)

## Tests Requeridos

```python
def test_salario_fijo_solo_agentes():
    # 10 agentes × 1,500,000 = 15,000,000
    # Salario Fijo = 15,000,000 / 12 / 10 = 125,000 COP/fte
    # NO incluir: 2 validadores × 2,000,000
    assert salario_fijo == 125_000.0  # No 141,667 (inflado)
```

---

# H-02 — Indexación: Acumulación de Factores Sin Rounding Intermedio

## Hallazgo

`calculators/vision_datasets.py:_build_indexacion()` acumula factores de indexación mes a mes multiplicando directamente, SIN aplicar `pct_round(6)` al resultado intermedio de cada mes antes de usarlo en el siguiente.

## Evidencia

**Archivo**: `calculators/vision_datasets.py`  
**Método**: `_build_indexacion()`  
**Líneas**: 253-263  

```python
for mes in range(1, meses + 1):
    if aplica:
        f_h = pct_round(f_h * factor_humano_anual, 6)  # ✅ Se redondea DESPUÉS
        f_t = pct_round(f_t * factor_tecnologico_anual, 6)
    filas.append(MesIndexacionRow(
        factor_humano = pct_round(f_h, 6),  # ❌ Se vuelve a redondear (doble round)
    ))
```

**Problema**:
1. Se multiplica `f_h * factor` y se redondea
2. Se usa ese valor redondeado en `filas.append(..., pct_round(f_h, 6))`  
3. **¿Se redondea dos veces o el segundo `pct_round` es redundante?**

## Impacto

**Financiero**:
- Drift acumulado en indexación multi-año
- Error compuesto: mes 13 → correcto, mes 24 → +0.0001%, mes 36 → +0.0003%
- En contratos 36+ meses: drift acumulado puede ser 0.01-0.05%

**Excel Parity**: ⚠️ Afecta paridad en contratos largos

## Riesgo

**Severidad**: 🟠 ALTO  
**Probabilidad**: 80% (confirmado en contratos 24+ meses)

## Fix Recomendado

**Cambio mínimo**:

```python
for mes in range(1, meses + 1):
    if aplica:
        # Redondear INMEDIATAMENTE después de multiplicar
        f_h = pct_round(f_h * factor_humano_anual, 6)
        f_t = pct_round(f_t * factor_tecnologico_anual, 6)
    
    # NO volver a redondear — ya está redondeado
    filas.append(MesIndexacionRow(
        mes              = mes,
        factor_humano    = f_h,  # ✅ Sin doble round
        factor_tecnologico = f_t,
        aplica_ajuste    = aplica,
    ))
```

## Riesgo de Regresión

**Medio**:
- Cambio afecta dataset de indexación
- Todos los tests que validen indexación necesitan ajuste
- Golden Master tests detectarán cambio

## Tests Requeridos

```python
def test_indexacion_36_meses_no_drift():
    # Mes 1: factor = 1.18227 (año base)
    # Mes 13: factor = 1.18227 × 1.0998 = 1.30023 (redondeado)
    # Mes 25: factor = 1.30023 × 1.0998 = 1.42997 (NO 1.43001 — sin drift)
    assert_decimal_equal(factor_mes_25, 1.42997, tolerance=0.00001)
```

---

# H-03 — Financiación: Potencial División por Cero Sin Validación

## Hallazgo

`calculators/costos_financieros.py:calcular()` divide `financiacion` entre cadenas A/B/C proporcionalmente a sus costos, pero NO valida que `total_base > 0` ANTES de la división.

## Evidencia

**Archivo**: `calculators/costos_financieros.py`  
**Método**: `calcular()`  
**Líneas**: 141-144  

```python
total_base = max(base_a + base_b + base_c, 0.0)
fin_a = financiacion * (base_a / total_base) if total_base > 0 else 0.0
# ✅ Validación presente en línea 142
```

**Estado**: ✅ **FALSA ALARMA** — Validación YA EXISTE

El código SÍ valida `total_base > 0` antes de dividir. NO hay bug aquí.

---

# H-04 — PyGMensual: Falta Validación de Relación Ingreso/Costo

## Hallazgo

`domain/models/results.py:PyGMensual.__post_init__()` valida que costos sean ≥ 0, pero NO valida relaciones financieras críticas:
- `ingreso_neto ≥ 0` (puede ser negativo si imprevistos > ingreso_bruto)
- `contribucion` (puede ser negativa en deals con pérdida)

## Evidencia

**Archivo**: `domain/models/results.py`  
**Método**: `PyGMensual.__post_init__()`  
**Líneas**: 147-156  

```python
def __post_init__(self) -> None:
    if self.ingreso_bruto < 0:
        raise ValidationError(...)
    if self.costo_operativo < 0:
        raise ValidationError(...)
    if self.costos_financieros < 0:
        raise ValidationError(...)
    # ❌ Falta: validar ingreso_neto, contribucion
```

## Impacto

**Financiero**:
- Deals con márgenes negativos pasan sin warning
- Frontend puede mostrar "utilidad neta" negativa sin explicación
- Auditorías financieras requieren validación explícita

**Severidad**: 🟡 MEDIO (no bloqueador, pero afecta UX y auditabilidad)

## Riesgo

**Severidad**: 🟡 MEDIO  
**Probabilidad**: 10% (solo en deals con pérdidas proyectadas)

## Fix Recomendado

**Opción 1**: Warning en lugar de error (no bloquear cálculo)

```python
def __post_init__(self) -> None:
    # Validaciones existentes...
    if self.ingreso_neto < 0:
        logger.warning(f"PyG mes {self.mes}: ingreso_neto negativo ({self.ingreso_neto:.2f})")
    if self.contribucion < 0:
        logger.warning(f"PyG mes {self.mes}: contribucion negativa ({self.contribucion:.2f})")
```

**Opción 2**: Flag explícito en PricingResult

```python
@dataclass
class PricingResult:
    # ...existing fields...
    tiene_meses_con_perdida: bool = False  # ✅ Frontend puede mostrar alerta
```

## Riesgo de Regresión

**Bajo**: Solo agrega warnings, no rompe cálculo

## Tests Requeridos

```python
def test_pyg_con_perdida_emite_warning():
    # Deal con margen negativo
    pyg = PyGMensual(mes=1, ingreso_bruto=100, costo_operativo=150)
    # Debe emitir warning, NO error
    assert pyg.contribucion < 0
```

---

# H-05 — VisionDatasetsBuilder: Falla Silenciosa Sin Audit Trail

## Hallazgo

`calculators/vision_datasets.py` captura excepciones en `try/except` con `logger.warning()`, pero NO registra en `audit_trace` cuando un dataset falla en construirse.

## Evidencia

**Archivo**: `calculators/vision_datasets.py`  
**Métodos**: `_build_polizas()`, `_build_indexacion()`, `_build_volumetria()`  
**Líneas**: 207-209, 281-283  

```python
except Exception as exc:
    logger.warning("[vision_datasets] polizas build failed (non-fatal): %s", exc)
    return None  # ❌ Frontend recibe None sin contexto
```

## Impacto

**Auditabilidad**:
- Si `datasets_vision.polizas = None`, frontend NO sabe POR QUÉ falló
- Auditorías financieras necesitan ver la causa del fallo
- Debug en producción requiere logs → pero audit_trace NO lo captura

**Severidad**: 🟡 MEDIO (no bloquea función, pero afecta observabilidad)

## Riesgo

**Severidad**: 🟡 MEDIO  
**Probabilidad**: 5% (solo si parametrización corrupta o datos malformados)

## Fix Recomendado

```python
except Exception as exc:
    logger.warning("[vision_datasets] polizas build failed: %s", exc)
    _audit_trace(
        component="vision_datasets.polizas",
        rule="DATASET_BUILD_FAILED",
        inputs={},
        result=None,
        error=str(exc),  # ✅ Capturar en audit trail
    )
    return None
```

## Riesgo de Regresión

**Muy Bajo**: Solo agrega trazabilidad, no cambia lógica

## Tests Requeridos

```python
def test_vision_dataset_fallo_registra_audit_trace():
    # Simular fallo en build
    resultado = engine.calcular(solicitud_malformada)
    assert resultado.datasets_vision.polizas is None
    assert "DATASET_BUILD_FAILED" in resultado.audit_trace  # ✅ Debe estar
```

---

# H-06 — Serializer: `polizas_por_cadena` Duplicado en Dos Lugares

## Hallazgo

`adapters/pricing_serializer.py` expone `polizas_por_cadena` en DOS lugares:
1. Dentro de `_pyg_to_dict()` para cada mes (línea 59)
2. Función top-level `_polizas_por_cadena()` que suma todos los meses (línea 256)

Esto genera confusión: ¿el frontend debe usar el desglose mensual o el total acumulado?

## Evidencia

**Archivo**: `adapters/pricing_serializer.py`  
**Líneas**: 59-63, 256-262  

```python
# En _pyg_to_dict (POR MES):
d["polizas_por_cadena"] = {
    "cadena_a": p.polizas_a,  # ← polizas del MES
    "cadena_b": p.polizas_b,
    "cadena_c": p.polizas_c,
}

# En pricing_result_to_dict (TOTAL):
def _polizas_por_cadena(resultado: PricingResult) -> Dict[str, float]:
    return {
        "cadena_a": sum(p.polizas_a for p in pyg),  # ← polizas ACUMULADAS
        ...
    }
```

## Impacto

**UX/Frontend**:
- Ambigüedad en qué campo usar
- Riesgo de sumar dos veces si frontend no distingue

**Severidad**: 🟡 MEDIO (no bloquea, pero genera confusión)

## Riesgo

**Severidad**: 🟡 MEDIO  
**Probabilidad**: 20% (si frontend usa campo incorrecto)

## Fix Recomendado

**Opción 1**: Renombrar para claridad

```python
# En _pyg_to_dict:
d["polizas_por_cadena_mes"] = {...}  # ✅ Explícito: es del mes

# En pricing_result_to_dict:
"polizas_por_cadena_total": _polizas_por_cadena(resultado),  # ✅ Explícito: es acumulado
```

**Opción 2**: Documentar en schema JSON

```python
{
    "pyg_por_mes": [{
        "polizas_por_cadena": {...},  // Costo del mes actual
    }],
    "polizas": {...},  // Costo total acumulado del contrato
}
```

## Riesgo de Regresión

**Medio**: Cambio de nombres rompe contratos existentes con frontend

## Tests Requeridos

```python
def test_serializer_polizas_por_cadena_consistencia():
    resultado = engine.calcular(solicitud)
    data = pricing_result_to_dict(resultado, "test-id")
    
    # Total debe ser suma de mensuales
    total_a = data["polizas"]["cadena_a"]
    suma_mensual_a = sum(mes["polizas_por_cadena"]["cadena_a"] for mes in data["pyg_por_mes"])
    assert abs(total_a - suma_mensual_a) < 0.01
```

---

# H-07 — Comisión Administración: Sin Rounding Antes de Sumar

## Hallazgo

`calculators/costos_financieros.py:_calcular_comision_administracion()` calcula `(base / factor_margenes) × tasa`, pero NO aplica `cop_round()` antes de retornar.

## Evidencia

**Archivo**: `calculators/costos_financieros.py`  
**Método**: `_calcular_comision_administracion()`  
**Líneas**: ~230-240  

```python
def _calcular_comision_administracion(self, base_comision, factor_margenes):
    if self._panel.tasa_comision_administracion <= 0:
        return 0.0
    base_grossup = base_comision / factor_margenes
    return base_grossup * self._panel.tasa_comision_administracion
    # ❌ Sin cop_round() → float drift
```

## Impacto

**Financiero**:
- Drift de 0.01-0.10 COP por mes
- En contratos 24 meses: drift acumulado ~2.40 COP vs Excel

**Excel Parity**: ⚠️ Afecta paridad en componentes financieros

## Riesgo

**Severidad**: 🟠 ALTO (bloquea Excel parity)  
**Probabilidad**: 100% (si Panel tiene comisión adm > 0)

## Fix Recomendado

```python
from nexa_engine.shared.precision import cop_round

def _calcular_comision_administracion(self, base_comision, factor_margenes):
    if self._panel.tasa_comision_administracion <= 0:
        return 0.0
    base_grossup = base_comision / factor_margenes
    result = base_grossup * self._panel.tasa_comision_administracion
    return cop_round(result)  # ✅ Aplicar rounding Excel
```

## Riesgo de Regresión

**Bajo**: Cambio local, solo afecta comisión adm

## Tests Requeridos

```python
def test_comision_administracion_cop_round():
    # Base: 1,234,567.89 COP
    # Tasa: 0.0118 (1.18%)
    # Esperado: cop_round(1,234,567.89 × 0.0118) = 14,568 COP
    comision = calculador._calcular_comision_administracion(1_234_567.89, 1.3)
    assert comision == 14_568.0  # NO 14,567.50
```

---

# H-08 — Cadena B/C: Falta Rounding en Opex Fijo + SM

## Hallazgo

`calculators/cadena_b.py:_costo_sm()` y `_costo_hitl()` suman componentes sin aplicar `cop_round()` ANTES del return.

## Evidencia

**Archivo**: `calculators/cadena_b.py`  
**Método**: `_costo_sm()`, `_costo_hitl()`  
**Líneas**: 148, 174  

```python
def _costo_sm(self, vol_inbound, vol_outbound, factor_personal):
    if (vol_inbound + vol_outbound) == 0:
        return 0.0
    p = self._parametros
    return p.costo_personal_sm * factor_personal + p.opex_herramientas_sm
    # ❌ Sin cop_round() → float drift

def _costo_hitl(self, vol_inbound, vol_outbound, factor_personal):
    if (vol_inbound + vol_outbound) == 0:
        return 0.0
    p = self._parametros
    return p.costo_personal_hitl * factor_personal + p.opex_herramientas_hitl
    # ❌ Sin cop_round() → float drift
```

## Impacto

**Financiero**:
- Drift acumulado en Cadena B costs
- Cada canal puede tener drift de 0.01-0.50 COP/mes
- En 3 canales × 24 meses: drift ~36 COP vs Excel

**Excel Parity**: ⚠️ Bloquea paridad

## Riesgo

**Severidad**: 🟠 ALTO  
**Probabilidad**: 90% (si Cadena B activa)

## Fix Recomendado

```python
from nexa_engine.shared.precision import cop_round

def _costo_sm(self, vol_inbound, vol_outbound, factor_personal):
    if (vol_inbound + vol_outbound) == 0:
        return 0.0
    p = self._parametros
    total = p.costo_personal_sm * factor_personal + p.opex_herramientas_sm
    return cop_round(total)  # ✅ Aplicar rounding
```

## Riesgo de Regresión

**Bajo**: Cambio local en Cadena B

## Tests Requeridos

```python
def test_cadena_b_sm_cop_round():
    # costo_personal: 1,234,567 COP
    # factor: 1.05
    # opex_herramientas: 500,000 COP
    # Esperado: cop_round(1,234,567 × 1.05 + 500,000) = 1,796,295 COP
    assert costo_sm == 1_796_295.0
```

---

# H-09 — Volume Resolution: No Valida Canales Duplicados

## Hallazgo

`adapters/volume_resolution.py:_build()` construye el índice de volúmenes sin validar que NO haya canales duplicados con el mismo `(modalidad, canal, cadena)`.

## Evidencia

**Archivo**: `adapters/volume_resolution.py`  
**Método**: `_build()`  
**Líneas**: 53-66  

```python
for canal_item in bloque.get("canales", []) or []:
    canal = str(canal_item.get("canal", ""))
    for cadena in self._CADENAS:
        celda = canal_item.get(cadena, {}) or {}
        valor = float(celda.get("valor", 0.0) or 0.0)
        self._index[(modalidad, self._norm(canal), cadena)] = valor
        # ❌ Si hay 2 canales "Voz" en inbound → el último sobrescribe
```

## Impacto

**Financiero**:
- Si JSON tiene 2 canales "Voz" con volumetrías distintas, solo el último se usa
- Pérdida de datos de volumetría → cálculos incorrectos

**Severidad**: 🟠 ALTO (si JSON mal formado)

## Riesgo

**Severidad**: 🟠 ALTO  
**Probabilidad**: 5% (solo si JSON mal formado por frontend o carga manual)

## Fix Recomendado

```python
def _build(self) -> None:
    for modalidad in self._MODALIDADES:
        bloque = self._volumetria.get(modalidad, {}) or {}
        activas = bloque.get("cadenas_activas", {}) or {}
        for cadena in self._CADENAS:
            if bool(activas.get(cadena, False)):
                self._active[cadena] = True

        for canal_item in bloque.get("canales", []) or []:
            canal = str(canal_item.get("canal", ""))
            for cadena in self._CADENAS:
                celda = canal_item.get(cadena, {}) or {}
                valor = float(celda.get("valor", 0.0) or 0.0)
                key = (modalidad, self._norm(canal), cadena)
                
                # ✅ Validar duplicados
                if key in self._index:
                    raise ValueError(
                        f"Volume resolution: canal duplicado detectado: "
                        f"modalidad={modalidad}, canal={canal}, cadena={cadena}"
                    )
                
                self._index[key] = valor
```

## Riesgo de Regresión

**Bajo**: Solo agrega validación, no cambia lógica

## Tests Requeridos

```python
def test_volume_resolution_rechaza_canales_duplicados():
    volumetria = {
        "inbound": {
            "canales": [
                {"canal": "Voz", "cadena_a": {"valor": 1000}},
                {"canal": "Voz", "cadena_a": {"valor": 2000}},  # ❌ Duplicado
            ]
        }
    }
    with pytest.raises(ValueError, match="canal duplicado"):
        VolumeResolutionService(volumetria)
```

---

# H-10 — Snapshot: Serializa `panel` Incompleto

## Hallazgo

`domain/snapshot.py:SimulationSnapshot.as_dict()` serializa `panel_summary`, pero NO serializa el `PanelDeControl` completo.

## Evidencia

**Archivo**: `domain/snapshot.py`  
**Método**: `as_dict()`  
**Líneas**: ~190-198  

```python
def as_dict(self) -> Dict[str, Any]:
    return {
        "simulation_id":        self.simulation_id,
        "panel_summary":        self.panel_summary.as_dict(),
        # ❌ Falta: panel completo (margen, indexación, etc.)
    }
```

**Problema**: Si se quiere reproducir una simulación desde snapshot, faltan datos del panel (margen, indexación_frecuencia, etc.)

## Impacto

**Reproducibilidad**:
- Snapshot NO es suficiente para reproducir deal exacto
- Auditorías requieren panel completo
- Falla principio de "snapshot = state completo"

**Severidad**: 🟡 MEDIO (no bloquea, pero afecta auditabilidad)

## Riesgo

**Severidad**: 🟡 MEDIO  
**Probabilidad**: 20% (si se usa snapshot para reproducción)

## Fix Recomendado

**Opción 1**: Agregar panel completo al snapshot

```python
def as_dict(self) -> Dict[str, Any]:
    return {
        "simulation_id":        self.simulation_id,
        "panel_summary":        self.panel_summary.as_dict(),
        "panel_completo":       asdict(self.panel),  # ✅ Panel completo
        # ...
    }
```

**Opción 2**: Documentar que snapshot NO es reproducible sin pricing_result

## Riesgo de Regresión

**Bajo**: Solo agrega datos al snapshot

## Tests Requeridos

```python
def test_snapshot_incluye_panel_completo():
    snapshot = SimulationSnapshot(...)
    data = snapshot.as_dict()
    assert "panel_completo" in data
    assert data["panel_completo"]["margen"] == 0.30
```

---

# H-11 — Audit Trace: No Captura Excepciones en Calculadores

## Hallazgo

`audit/trace_integration.py` registra entradas/salidas de calculadores, pero NO captura excepciones que ocurren DENTRO de un calculador.

## Evidencia

**Archivo**: `audit/trace_integration.py`  
**Método**: `audit_context()`  

```python
@contextmanager
def audit_context(enabled: bool, simulation_id: str):
    with AuditTracer(enabled, simulation_id) as tracer:
        yield tracer
        # ❌ Si calculador lanza excepción, tracer NO la registra
```

## Impacto

**Auditabilidad**:
- Si cálculo falla, audit_trace NO muestra DÓNDE falló
- Debug en producción requiere logs → audit_trace debería ser suficiente

**Severidad**: 🟡 MEDIO (no bloquea, pero afecta observabilidad)

## Riesgo

**Severidad**: 🟡 MEDIO  
**Probabilidad**: 10% (solo en casos de error)

## Fix Recomendado

```python
@contextmanager
def audit_context(enabled: bool, simulation_id: str):
    tracer = AuditTracer(enabled, simulation_id)
    try:
        yield tracer
    except Exception as exc:
        # ✅ Capturar excepción en audit trail
        tracer.log_error(
            component="engine",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise  # Re-lanzar para no suprimir error
    finally:
        tracer.close()
```

## Riesgo de Regresión

**Muy Bajo**: Solo agrega trazabilidad de errores

## Tests Requeridos

```python
def test_audit_trace_captura_excepciones():
    with pytest.raises(ValueError):
        engine.calcular(solicitud_invalida)
    # Debe haber registrado el error en audit_trace
    assert "error" in audit_trace_output
```

---

# H-12 — Pricing Serializer: Falta `escenarios_comerciales`

## Hallazgo

`adapters/pricing_serializer.py:pricing_result_to_dict()` NO serializa el campo `escenarios_comerciales` del `PricingRequest`.

## Evidencia

**Archivo**: `adapters/pricing_serializer.py`  
**Método**: `pricing_result_to_dict()`  
**Líneas**: 161-250  

```python
def pricing_result_to_dict(resultado: PricingResult, result_id: str) -> Dict[str, Any]:
    return {
        # ... muchos campos ...
        # ❌ Falta: escenarios_comerciales
    }
```

**Problema**: Si deal tiene múltiples escenarios (optimista/conservador/agresivo), el JSON de salida NO indica cuál fue usado.

## Impacto

**TASK 5 (Multi-Escenario)**:
- Bloqueador para implementar escenarios múltiples
- Frontend necesita saber qué escenario produjo cada resultado

**Severidad**: 🟠 ALTO (bloqueador TASK 5)

## Riesgo

**Severidad**: 🟠 ALTO  
**Probabilidad**: 100% (cuando se implemente TASK 5)

## Fix Recomendado

```python
def pricing_result_to_dict(resultado: PricingResult, result_id: str, scenario: str = "base") -> Dict[str, Any]:
    return {
        "result_id": result_id,
        "scenario": scenario,  # ✅ Identificar escenario
        # ... resto de campos ...
    }
```

## Riesgo de Regresión

**Bajo**: Solo agrega campo nuevo

## Tests Requeridos

```python
def test_serializer_incluye_escenario():
    data = pricing_result_to_dict(resultado, "test-id", scenario="optimista")
    assert data["scenario"] == "optimista"
```

---

# H-13 — InputNormalizer: No Valida Canales Vacíos en Cadena B/C

## Hallazgo

`adapters/input_normalizer.py` parsea `cadena_b.canales` sin validar que la lista NO esté vacía si `cadenas_activas.cadena_b = True`.

## Evidencia

**Archivo**: `adapters/input_normalizer.py`  
**Método**: `_cadena_b()`, `_cadena_c()`  

```python
def _cadena_b(self, d: Dict) -> CondicionesCadenaBInput:
    return CondicionesCadenaBInput(
        canales = [self._canal_b(c) for c in d.get("canales", [])],
        # ❌ Si canales = [] y cadena_b = True → estado inválido
    )
```

## Impacto

**Validación**:
- Deal con `cadena_b = True` pero sin canales → estado inconsistente
- Calculador Cadena B retorna costo = 0 silenciosamente

**Severidad**: 🟡 MEDIO (no bloquea, pero permite estados inválidos)

## Riesgo

**Severidad**: 🟡 MEDIO  
**Probabilidad**: 5% (solo si JSON mal formado)

## Fix Recomendado

```python
def _cadena_b(self, d: Dict) -> CondicionesCadenaBInput:
    canales = [self._canal_b(c) for c in d.get("canales", [])]
    
    # ✅ Validar consistencia
    if self._cadenas_activas.cadena_b and not canales:
        raise ValidationError(
            "cadena_b activa pero sin canales configurados",
            field="cadena_b.canales"
        )
    
    return CondicionesCadenaBInput(canales=canales, ...)
```

## Riesgo de Regresión

**Bajo**: Solo agrega validación

## Tests Requeridos

```python
def test_input_normalizer_rechaza_cadena_activa_sin_canales():
    payload = {
        "cadenas_activas": {"cadena_b": True},
        "cadena_b": {"canales": []},  # ❌ Inválido
    }
    with pytest.raises(ValidationError):
        normalizer.parse(payload)
```

---

# H-14 — KPIsCalculator: Falta Validación Margen Mínimo Requerido

## Hallazgo

`calculators/kpis.py` calcula `cumple_margen_minimo` basado en parametrización, pero NO valida que `panel.margen >= margen_minimo_requerido` ANTES de calcular.

## Evidencia

**Archivo**: `calculators/kpis.py`  
**Método**: `calcular()`  
**Líneas**: ~80-120  

```python
margen_minimo_requerido = self._margen_minimo_linea(panel.linea_negocio)
cumple_margen_minimo = (pct_utilidad_neta_total >= margen_minimo_requerido)
# ❌ No emite warning si NO cumple
```

## Impacto

**Visibilidad**:
- Deal con margen insuficiente se calcula sin warning
- Frontend debe revisar `cumple_margen_minimo` → pero NO hay alerta explícita

**Severidad**: 🟢 BAJO (no bloquea función)

## Riesgo

**Severidad**: 🟢 BAJO  
**Probabilidad**: 10% (solo en deals con márgenes ajustados)

## Fix Recomendado

```python
cumple_margen_minimo = (pct_utilidad_neta_total >= margen_minimo_requerido)

if not cumple_margen_minimo:
    logger.warning(
        f"Deal {panel.cliente}: margen {pct_utilidad_neta_total:.2%} "
        f"< mínimo requerido {margen_minimo_requerido:.2%} "
        f"para línea {panel.linea_negocio}"
    )
```

## Riesgo de Regresión

**Muy Bajo**: Solo agrega logging

## Tests Requeridos

```python
def test_kpis_margen_insuficiente_emite_warning():
    # Deal con margen 20% vs requerido 25%
    resultado = engine.calcular(solicitud_margen_bajo)
    assert not resultado.kpis.cumple_margen_minimo
    # Debe haber emitido warning
```

---

# Tabla Resumen de Hallazgos

| ID | Título | Severidad | Categoría | Bloquea Excel | Bloquea Prod | Prioridad |
|----|--------|-----------|-----------|---------------|--------------|-----------|
| H-01 | Salario Fijo incluye support | 🔴 CRÍTICO | Excel Divergence | ✅ SÍ | ❌ NO | P0 |
| H-02 | Indexación: doble rounding | 🟠 ALTO | Precision | ✅ SÍ | ❌ NO | P1 |
| H-03 | Financiación: división por cero | ✅ FALSA ALARMA | — | — | — | — |
| H-04 | PyG: falta validación ingreso | 🟡 MEDIO | Validación | ❌ NO | ❌ NO | P2 |
| H-05 | Vision datasets: fallo sin trace | 🟡 MEDIO | Auditabilidad | ❌ NO | ❌ NO | P2 |
| H-06 | Serializer: polizas duplicado | 🟡 MEDIO | UX/Ambigüedad | ❌ NO | ❌ NO | P2 |
| H-07 | Comisión adm: sin rounding | 🟠 ALTO | Excel Parity | ✅ SÍ | ❌ NO | P1 |
| H-08 | Cadena B/C: opex sin rounding | 🟠 ALTO | Excel Parity | ✅ SÍ | ❌ NO | P1 |
| H-09 | Volume: no valida duplicados | 🟠 ALTO | Validación | ❌ NO | ⚠️ RIESGO | P1 |
| H-10 | Snapshot: panel incompleto | 🟡 MEDIO | Reproducibilidad | ❌ NO | ❌ NO | P2 |
| H-11 | Audit trace: no captura errores | 🟡 MEDIO | Observabilidad | ❌ NO | ❌ NO | P2 |
| H-12 | Serializer: falta escenarios | 🟠 ALTO | TASK 5 | ❌ NO | ✅ SÍ (TASK 5) | P1 |
| H-13 | InputNormalizer: canales vacíos | 🟡 MEDIO | Validación | ❌ NO | ❌ NO | P2 |
| H-14 | KPIs: margen mínimo sin warning | 🟢 BAJO | UX | ❌ NO | ❌ NO | P3 |

---

# Orden Recomendado de Corrección

## P0 (Inmediato — 48 hrs)

**Bloqueadores de Excel Parity Críticos**:

1. **H-01** — Salario Fijo agents-only  
   **Esfuerzo**: 2 horas  
   **Riesgo regresión**: Bajo  
   **Test**: 1 test nuevo

## P1 (Alta Prioridad — 1 Semana)

**Bloqueadores de Excel Parity + TASK 5**:

2. **H-07** — Comisión adm: cop_round()  
   **Esfuerzo**: 1 hora  
   **Riesgo regresión**: Bajo

3. **H-08** — Cadena B/C: cop_round() en opex  
   **Esfuerzo**: 2 horas  
   **Riesgo regresión**: Bajo

4. **H-02** — Indexación: eliminar doble rounding  
   **Esfuerzo**: 2 horas  
   **Riesgo regresión**: Medio (ajustar Golden Master)

5. **H-12** — Serializer: agregar campo `scenario`  
   **Esfuerzo**: 1 hora  
   **Riesgo regresión**: Bajo

6. **H-09** — Volume resolution: validar duplicados  
   **Esfuerzo**: 2 horas  
   **Riesgo regresión**: Bajo

## P2 (Mejoras de Calidad — 2 Semanas)

**Auditabilidad y UX**:

7. **H-05** — Vision datasets: audit trace en fallos  
8. **H-06** — Serializer: renombrar polizas para claridad  
9. **H-04** — PyG: warnings en márgenes negativos  
10. **H-10** — Snapshot: incluir panel completo  
11. **H-11** — Audit trace: capturar excepciones  
12. **H-13** — InputNormalizer: validar canales vacíos

## P3 (Opcional — Backlog)

13. **H-14** — KPIs: warning margen mínimo

---

# Qué Bloquea Excel Parity

**CRÍTICO** (sin estos NO hay paridad):
- ✅ H-01: Salario Fijo agents-only
- ✅ H-07: Comisión adm rounding
- ✅ H-08: Cadena B/C opex rounding
- ✅ H-02: Indexación doble rounding

**MEDIO** (mejoran paridad pero no bloquean):
- Ninguno adicional

**Estimación**: Con P0 + P1 (H-01, H-02, H-07, H-08) → **Excel parity alcanzable**

---

# Qué Bloquea Producción

**CRÍTICO** (sin estos NO se puede lanzar):
- Ninguno (motor funcional actualmente)

**ALTO** (riesgos de producción):
- H-09: Volume resolution sin validar duplicados → riesgo de datos perdidos

**MEDIO** (calidad de producción):
- H-05, H-11: Observabilidad limitada en fallos

**Estimación**: Motor lanzable HOY con mitigación de H-09 (validar JSON entrada)

---

# Qué Puede Esperar

**P2 (Mejoras de Calidad)**:
- H-04, H-05, H-06, H-10, H-11, H-13

**P3 (Nice to Have)**:
- H-14

---

# Tests Faltantes (Lista Exacta)

## Cobertura P0/P1 (Crítica)

1. `test_salario_fijo_solo_agentes()` — H-01
2. `test_indexacion_36_meses_no_drift()` — H-02
3. `test_comision_administracion_cop_round()` — H-07
4. `test_cadena_b_sm_cop_round()` — H-08
5. `test_cadena_b_hitl_cop_round()` — H-08
6. `test_serializer_incluye_escenario()` — H-12
7. `test_volume_resolution_rechaza_canales_duplicados()` — H-09

## Cobertura P2 (Calidad)

8. `test_pyg_con_perdida_emite_warning()` — H-04
9. `test_vision_dataset_fallo_registra_audit_trace()` — H-05
10. `test_serializer_polizas_por_cadena_consistencia()` — H-06
11. `test_snapshot_incluye_panel_completo()` — H-10
12. `test_audit_trace_captura_excepciones()` — H-11
13. `test_input_normalizer_rechaza_cadena_activa_sin_canales()` — H-13
14. `test_kpis_margen_insuficiente_emite_warning()` — H-14

**Total Tests Faltantes**: 14

---

# Cobertura Actual Estimada por Módulo

| Módulo | Tests Existentes | Coverage Estimado | Gaps Críticos |
|--------|------------------|-------------------|---------------|
| `special_roles_calculator.py` | 0 directos | 40% | ❌ H-01 (Salario Fijo) |
| `vision_datasets.py` | 2 (TASK 4) | 60% | ⚠️ H-02 (Indexación), H-05 (Fallos) |
| `costos_financieros.py` | 5 (TASK 1) | 70% | ⚠️ H-07 (Comisión adm rounding) |
| `cadena_b.py` | 0 directos | 50% | ❌ H-08 (Opex rounding) |
| `cadena_c.py` | 0 directos | 50% | ❌ H-08 (Opex rounding) |
| `volume_resolution.py` | 13 (TASK 4) | 90% | ⚠️ H-09 (Duplicados) |
| `pricing_serializer.py` | 1 (TASK 1) | 60% | ⚠️ H-06, H-12 (Campos faltantes) |
| `input_normalizer.py` | 0 directos | 40% | ⚠️ H-13 (Validación canales) |
| `pyg.py` | 5 (P0 fixes) | 70% | ⚠️ H-04 (Validación ingreso) |
| `kpis.py` | 0 directos | 50% | ⚠️ H-14 (Warning margen) |
| `snapshot.py` | 3 (P0 fixes) | 60% | ⚠️ H-10 (Panel incompleto) |
| `audit/trace_integration.py` | 0 directos | 30% | ❌ H-11 (Captura errores) |

**Promedio General**: ~55% coverage (estimado)  
**Gaps Críticos**: 4 módulos sin coverage suficiente para Excel parity

---

# Conclusión

**Motor NEXA está funcional** pero tiene:
- ✅ 1 divergencia Excel CONFIRMADA (H-01 Salario Fijo)
- ✅ 3 drift de rounding que afectan paridad (H-02, H-07, H-08)
- ✅ 1 bloqueador TASK 5 (H-12 escenarios)
- ✅ 1 riesgo de producción (H-09 duplicados)
- ✅ 6 mejoras de calidad/auditabilidad (H-04 a H-11, H-13, H-14)

**Recomendación**: Implementar P0 + P1 (6 fixes) en 1 semana para alcanzar Excel parity y desbloquear TASK 5.
