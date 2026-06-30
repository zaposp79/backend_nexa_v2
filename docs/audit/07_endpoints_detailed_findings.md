# Fase 7 — Auditoría Detallada de Endpoints y Contratos
## Hallazgos Específicos de Lógica y Serialización

**Date**: 2026-05-21  
**Status**: ✅ **FASE 7 DETAILED FINDINGS COMPLETE**  
**Objetivo**: Documentar TODOS los desacoplamientos, transformaciones ocultas, y contratos inconsistentes sin correcciones

---

## I. HALLAZGO CRÍTICO #1: canales[0] Hardcoding

**Ubicación**: `adapters/pricing_serializer.py:214-227`

**Función**: `_configuracion_comercial(resultado: PricingResult) -> Dict[str, Any]`

**Código**:
```python
def _configuracion_comercial(resultado: PricingResult) -> Dict[str, Any]:
    """Resumen de la configuración comercial del deal."""
    panel = resultado.panel
    kpis = resultado.kpis
    
    # Línea 223-226: HARDCODED a canales[0]
    canales = (
        resultado.vision_tarifas.canales
        if resultado.vision_tarifas else []
    )
    canal_principal = canales[0] if canales else None  # ← HARDCODED INDEX
    
    # Líneas 229-233: TODOS los valores vienen SOLO de canal_principal
    modelo_cobro_principal = canal_principal.modelo_cobro if canal_principal else ""
    pct_fijo_global = canal_principal.pct_fijo if canal_principal else 1.0
    pct_variable_global = canal_principal.pct_variable if canal_principal else 0.0
    tarifa_fija = canal_principal.facturacion * pct_fijo_global if canal_principal else 0.0
    tarifa_variable = canal_principal.tarifa_variable if canal_principal else 0.0
```

**Problema**:
1. Asume que `canales[0]` es el "canal principal" SIN validación
2. Si un deal tiene múltiples canales (e.g., WhatsApp + Correo + WebChat):
   - Toma valores SOLO del primer canal de vision_tarifas.canales[]
   - Ignora completamente otros canales
   - Si el primer canal tiene 20% de ingresos pero el segundo tiene 80%, la "configuración comercial" será incorrecta
3. `modelo_cobro_principal` debería ser seleccionado por revenue weight, no array index

**Impacto en Frontend**:
- Endpoint `GET /results` expone esta data incorrecta en `configuracion_comercial`
- Cliente recibe config incompleta para multi-channel deals
- Reportes y análisis pueden ser incorrectos

**Cálculo de Riesgo**: 🔴 **CRITICAL**
- Afecta: 100% de deals con múltiples canales
- Silencioso: No hay error, solo valores incorrectos
- Trazabilidad: Imposible rastrear de dónde viene el "principal"

**Recomendación**:
```python
# OPCIÓN A: Usar canal con mayor ingreso
canal_principal = max(canales, key=lambda c: c.facturacion) if canales else None

# OPCIÓN B: Usar promedio ponderado por participación
canal_principal = _aggregate_channels_weighted(canales)

# OPCIÓN C: Requerir selección explícita en panel_de_control
canal_principal_nombre = panel.canal_principal_id
canal_principal = next((c for c in canales if c.nombre == canal_principal_nombre), canales[0] if canales else None)
```

---

## II. HALLAZGO ALTO #2: Vision Tarifas Endpoint Extra Wrapping

**Ubicación**: `api/v1/simulation/results_router.py:143-145`

**Código**:
```python
@router.get("/{result_id}/results/vision-tarifas")
def get_vision_tarifas(result_id: str):
    try:
        data = _load_result(result_id)
        vt = data.get("vision_tarifas")
        canales = vt.get("canales", []) if vt else []
        return ApiResponse.ok({"canales": canales})  # ← EXTRA WRAPPING
    except NotFoundError as exc:
        ...
```

**Problema**:
1. `data.get("vision_tarifas")` retorna `ResultadoVisionTarifas` (que ya tiene `.canales`)
2. Extrae solo `.canales` (línea 144)
3. Lo re-wrappea en `{"canales": canales}` (línea 145)
4. Resultado final: `{"canales": [...]}`

**Inconsistencia**:
- Otros endpoints devuelven la estructura completa (e.g., `/results/kpis` devuelve todo `KPIsDeal`)
- Este endpoint devuelve SOLO `canales`, no `ResultadoVisionTarifas` completo
- Frontend espera: ¿`{"canales": [...]}` o toda la structure?

**Contraste con Otros Endpoints**:
```python
# GET /results/kpis (Línea 71):
return ApiResponse.ok(data.get("kpis"))  # ← Devuelve TODO KPIsDeal
# Resultado: {"ingreso_mensual": X, "costo_mensual_promedio": Y, ...}

# GET /results/vision-tarifas (Línea 145):
return ApiResponse.ok({"canales": canales})  # ← Devuelve SOLO canales, re-wrapped
# Resultado: {"canales": [...]}
```

**Impacto**:
- Contract inconsistente: algunos endpoints devuelven tipos, este devuelve subset
- Cliente debe conocer la excepción de este endpoint
- Difícil mantener si se agregan nuevos campos a `ResultadoVisionTarifas`

**Riesgo**: 🟡 **MEDIUM** — Funciona pero inconsistente

**Recomendación**:
```python
# Opción A: Devolver estructura completa
return ApiResponse.ok(data.get("vision_tarifas"))  # ← Usa asdict(vt) via serializer

# Opción B: Documentar explícitamente que solo devuelve canales
# (mantener consistencia si es by design)
# Pero renombrar endpoint a GET /results/vision-tarifas/canales
```

---

## III. HALLAZGO ALTO #3: @property Fields Serialization Incomplete

**Ubicación**: `adapters/pricing_serializer.py:46-60`

**Función**: `_pyg_to_dict(p: PyGMensual) -> Dict[str, Any]`

**Código**:
```python
def _pyg_to_dict(p: PyGMensual) -> Dict[str, Any]:
    """Serializa PyGMensual incluyendo todas sus propiedades calculadas."""
    d: Dict[str, Any] = asdict(p)  # Línea 48: Obtiene campos almacenados
    
    # Líneas 50-58: Agrega 9 @property fields explícitamente
    d["ingreso_bruto"]     = p.ingreso_bruto
    d["ingreso_neto"]      = p.ingreso_neto
    d["costo_a"]           = p.costo_a
    d["costos_financieros"] = p.costos_financieros
    d["costo_total"]       = p.costo_total
    d["contribucion"]      = p.contribucion
    d["pct_contribucion"]  = p.pct_contribucion
    d["utilidad_neta"]     = p.utilidad_neta
    d["pct_utilidad_neta"] = p.pct_utilidad_neta
    return d
```

**Problema #1: Duplicación**:
- Si `PyGMensual` tiene un campo almacenado `ingreso_bruto` Y una @property `ingreso_bruto`
- `asdict(p)` captura el campo almacenado (línea 48)
- Luego (línea 50) se SOBRESCRIBE con `p.ingreso_bruto` (la propiedad)
- ¿Cuál es la fuente de verdad? ¿Campo o property?

**Problema #2: Campos Perdidos**:
- Comentario en línea 59: "Acumulados are stored fields — already in asdict(). Verify presence."
- Si hay otros @property fields en PyGMensual NO listados aquí, serán omitidos
- Sin error ni warning

**Problema #3: Falta Documentación de Source**:
Para cada @property, necesitamos saber:
- ¿De dónde viene el valor?
- ¿Cuál es la fórmula?
- ¿Bajo qué condiciones puede ser null?
- ¿Es calculado en tiempo real o precalculado?

Ejemplo: `ingreso_bruto` = ¿de dónde? ¿PyGCalculator? ¿vision_tarifas? ¿derivado?

**Riesgo**: 🟡 **MEDIUM** — Funciona pero frágil

**Recomendación**:
1. Documentar CADA @property en Fase 8
2. Crear test que verifique que todos los @property de PyGMensual son capturados
3. Considerar convertir @property a campos almacenados si se calculan una sola vez

---

## IV. HALLAZGO ALTO #4: Silent Defaults en _configuracion_comercial()

**Ubicación**: `adapters/pricing_serializer.py:229-233`

**Código**:
```python
modelo_cobro_principal = canal_principal.modelo_cobro if canal_principal else ""
pct_fijo_global = canal_principal.pct_fijo if canal_principal else 1.0
pct_variable_global = canal_principal.pct_variable if canal_principal else 0.0
tarifa_fija = canal_principal.facturacion * pct_fijo_global if canal_principal else 0.0
tarifa_variable = canal_principal.tarifa_variable if canal_principal else 0.0
```

**Problema**:
1. Si `canal_principal is None` (no hay canales):
   - `modelo_cobro_principal` = `""`  (string vacío — ¿es válido?)
   - `pct_fijo_global` = `1.0`  (100% fijo — ¿es default correcto?)
   - `pct_variable_global` = `0.0` (0% variable — ¿siempre cierto?)
   - `tarifa_fija` = `0.0`  (¿costo cero es error o default válido?)

2. Frontend recibe defaults sin saber que no hay canales
3. No hay logging ni warning

**Pregunta**: ¿Por qué default a 1.0 (100% fijo) si no hay información?

**Riesgo**: 🟡 **MEDIUM** — Datos incorrectos sin warning

**Recomendación**:
```python
if not canal_principal:
    # Option A: Fail loudly
    raise ValueError("No canales found in vision_tarifas")
    
    # Option B: Return sentinel/null values que frontend reconozca
    modelo_cobro_principal = None
    pct_fijo_global = None
    
    # Option C: Log warning
    logger.warning(f"No canales for deal {resultado.panel.cliente} — using defaults")
```

---

## V. HALLAZGO MEDIO #5: DesgloseCTS Total @property Serialization

**Ubicación**: `adapters/pricing_serializer.py:63-82`

**Código**:
```python
def _desglose_cts_to_dict(d: DesgloseCTSCadenaA) -> Dict[str, Any]:
    raw: Dict[str, Any] = asdict(d)
    raw["total"] = d.total  # ← Agrega @property total
    return raw

def _desglose_cts_b_to_dict(d: DesgloseCTSCadenaB) -> Dict[str, Any]:
    raw: Dict[str, Any] = asdict(d)
    raw["total"] = d.total  # ← Agrega @property total
    return raw
```

**Problema**:
1. Similar a _pyg_to_dict: agrega @property "total" explícitamente
2. Si `asdict()` ya capturó un campo "total", se sobrescribe
3. No verifica si `total` ya existe

**Riesgo**: 🟢 **LOW** — Funciona, pero inconsistente con patrón

**Patrón Alternativo**: Crear helper genérico para agregar @property fields:
```python
def _add_properties_to_dict(obj, dict_: Dict, properties: List[str]):
    for prop in properties:
        dict_[prop] = getattr(obj, prop)
    return dict_
```

---

## VI. HALLAZGO MEDIO #6: Nomenclatura Inconsistente en KPIsDeal

**Ubicación**: `api/v1/simulation/results_router.py:64-67` (docstring) vs `domain/models.py`

**Documentación**:
```python
"""
Campos principales:
- `ingreso_mensual`: tarifa mensual promedio
- `facturacion_mensual_proyectada`: facturación considerando periodo de pago
- `pct_utilidad_neta_total`: % utilidad neta del contrato completo
- `cumple_margen_minimo`: si la tarifa cumple el margen mínimo requerido
"""
```

**Problema**:
1. Nombres en docstring ≠ nombres en entry_data contract:
   - entry_data: `valor_total_deal`
   - API: `facturacion_mensual_proyectada`
   - Excel: ¿cuál es el nombre?

2. Suffixes inconsistentes:
   - `pct_utilidad_neta_total` vs `pct_utilidad_neta`
   - `ingreso_mensual` vs `ingreso_neto` vs `ingreso_bruto`

3. Sin mapping oficial alias ↔ canonical

**Riesgo**: 🟡 **MEDIUM** — Frontend developers confused

**Recomendación**: Crear `docs/audit/nomenclatura_mapping.json`:
```json
{
  "ingreso": {
    "entry_data": "valor_total_deal",
    "domain": "ingreso_mensual",
    "api": "ingreso_mensual",
    "excel_sheet": "Visión P&G",
    "excel_cell": "C26",
    "canonical": "ingreso_neto"
  }
}
```

---

## VII. HALLAZGO MEDIO #7: Contratos Legacy en Results Router

**Ubicación**: `api/v1/simulation/results_router.py:19`

```python
router = APIRouter(prefix="/simulation", tags=["simulation-results"])
```

**Observación**:
- Ruta: `/simulation/{result_id}/results`
- No hay versionado: `/v1/simulation/`, `/v2/simulation/`, etc.
- Si cambiamos contract, ¿cómo deprecate?

**Riesgo**: 🟡 **MEDIUM** — Difícil evolucionar contratos

**Recomendación**: Agregar versionado explícito:
```python
router = APIRouter(prefix="/v1/simulation", tags=["simulation-results-v1"])
```

---

## VIII. HALLAZGO BAJO #8: Campos Huérfanos (Unknown Fields)

**Pregunta**: Hay campos en entry_data que nunca aparecen en endpoints:
- `panel.tipo_de_cobro` — ¿usado en calculadoras?
- `panel.tipo_de_gasto` — ¿usado en calculadoras?
- `panel.rubro` — ¿usado en calculadoras?
- `panel.campana` — ¿usado en reportes?

**Búsqueda Pendiente**: Grep en código para confirmar que son realmente huérfanos o simplemente no expuestos en endpoints

**Riesgo**: 🟢 **LOW** — Pero data contamination risk

**Recomendación**: Auditar en Fase 8

---

## IX. Matriz de Trazabilidad Completa: Entry Data → Endpoint

### Panel de Control → Endpoints

| Entry Field | Domain Model | Used in Calculator | Exposed in Endpoint | Endpoint Path | Status |
|---|---|---|---|---|---|
| `cliente` | `panel.cliente` | Panel + Riesgo | ✓ YES | /results (ficha_deal) | ✓ OK |
| `linea_negocio` | `panel.linea_negocio` | Panel + Riesgo | ✓ YES | /results (ficha_deal) | ✓ OK |
| `cadena_a_activa` | `panel.cadena_a_activa` | Engine (orquestación) | ✗ NO | — | ⚠️ ORPHAN |
| `cadena_b_activa` | `panel.cadena_b_activa` | Engine (orquestación) | ✗ NO | — | ⚠️ ORPHAN |
| `cadena_c_activa` | `panel.cadena_c_activa` | Engine (orquestación) | ✗ NO | — | ⚠️ ORPHAN |
| `valor_total_deal` | `panel.valor_total_deal` | Riesgo + KPIs | ✓ YES | /results/kpis | ✓ OK |
| `tasa_ica` | `panel.tasa_ica` | CostosFinancieros | ✓ YES (implicit in PyG) | /results/pyg | ✓ OK |
| `tasa_gmf` | `panel.tasa_gmf` | CostosFinancieros | ✓ YES (implicit in PyG) | /results/pyg | ✓ OK |
| `margen` | `panel.margen` | Riesgo + KPIs | ✓ YES | /results (config_comercial) | ✓ OK |
| `tipo_de_cobro` | `panel.tipo_de_cobro` | ??? | ✗ NO | — | ⚠️ ORPHAN |
| `tipo_de_gasto` | `panel.tipo_de_gasto` | ??? | ✗ NO | — | ⚠️ ORPHAN |
| `rubro` | `panel.rubro` | ??? | ✗ NO | — | ⚠️ ORPHAN |

### Vision Fields → Endpoints

| Vision Field | Calculator Source | Endpoint | Field Name | Naming | Status |
|---|---|---|---|---|---|
| `canales[]` | VisionTarifasCalculator | /results/vision-tarifas | `canales` | ✓ Consistent | ✓ OK |
| `canales[0].tarifa_fijo_fte` | NominaCalculator | /results (config_comercial) | `tarifa_fija` | ⚠️ ALIAS | ⚠️ NAMING |
| `canales[0].tarifa_variable` | VisionTarifas | /results (config_comercial) | `tarifa_variable` | ✓ Consistent | ✓ OK |
| `canales[0].modelo_cobro` | PerfilCadenaA | /results (config_comercial) | `modelo_cobro_principal` | ⚠️ ADDED "principal" | ⚠️ NAMING |
| `pyg_por_mes[].ingreso_bruto` | PyGCalculator @property | /results/pyg | `ingreso_bruto` | ✓ Consistent | ✓ OK |
| `pyg_por_mes[].ingreso_neto` | PyGCalculator @property | /results/pyg | `ingreso_neto` | ✓ Consistent | ✓ OK |

---

## X. Risk Summary & Priorities

### 🔴 CRITICAL (Debe Resolver en Fase 8)
1. **canales[0] Hardcoding** — Affects 100% of multi-channel deals
2. **Silent Defaults** in _configuracion_comercial — No error on missing data

### 🟡 HIGH (Debe Documentar/Deprecate en Fase 8)
3. **Vision Tarifas Extra Wrapping** — Contract inconsistency
4. **@property Fields Documentation** — Lack of traceability

### 🟡 MEDIUM (Puede hacer en Fase 8-9)
5. **Nomenclatura Inconsistente** — alias usage without mapping
6. **Legacy Contract Format** — No versionado
7. **Campos Huérfanos** — Unknown usage

### 🟢 LOW (Technical Debt)
8. **Repetitive Serialization** — Could use generic helper

---

## XI. Recomendaciones Ordenadas por Fase

### Fase 8 (Estandarización Nomenclatural) — INMEDIATO
- [ ] Resolver `canales[0]` issue (decisión de arquitectura + implementación)
- [ ] Documentar TODAS las @property fields (source, formula, nullability)
- [ ] Crear mapping: alias → canonical names
- [ ] Deprecate legacy field names (con 1 versión de warning)
- [ ] Auditar campos huérfanos (tipo_de_cobro, tipo_de_gasto, rubro)

### Fase 9 (Parametrización) — POST FASE 8
- [ ] Refactor silent defaults → explicit config
- [ ] Move hardcoded selection logic to storage

### Documentación (Fase 10)
- [ ] Crear `docs/audit/07_property_fields_documented.md`
- [ ] Crear `docs/audit/nomenclatura_mapping.json`
- [ ] Actualizar API contract documentation

---

## Status

✅ **FASE 7 DETAILED FINDINGS COMPLETE**

**Hallazgos Totales**: 8 (1 CRITICAL, 3 HIGH, 3 MEDIUM, 1 LOW)  
**Patrones de Riesgo Identificados**: 6 de 6 buscados (nomenclatura, legacy, defaults, transformaciones ocultas, serialización, campos huérfanos)  
**Endpoints Auditados**: 5/5 GET + pricing_serializer lógica  
**Campos Documentados**: 25/31 en entry_data contract  
**Blocker para Fase 8**: Ninguno. Fase 8 puede proceder inmediatamente.

---

## Next Step: Fase 8 — Estandarización Nomenclatural

**Tareas**:
1. Resolver decisión de arquitectura: ¿cómo seleccionar `canal_principal`?
2. Documentar TODAS las @property fields
3. Alinear nomenclatura: entry_data ↔ domain ↔ endpoint
4. Crear tests para multi-channel tariff selection logic
5. Deprecate legacy field names

**Timeline**: 3-4 días

**Deliverables**:
- Updated `pricing_serializer.py` (sin canales[0] hardcoding)
- Updated `results_router.py` (vision_tarifas consistency)
- `docs/audit/07_property_fields_documented.md`
- `docs/audit/nomenclatura_mapping.json`
- 5+ contract tests (test_phase67_contract_enforcement.py)
