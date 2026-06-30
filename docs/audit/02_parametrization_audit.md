# Auditoría de Parametrización — config/ vs storage/

**Versión**: 2026-05-21  
**Estado**: Auditoría Fase 2  
**Objetivo**: Identificar duplicados, hardcodes, y definir plan de migración a single source of truth (`storage/`).

---

## 1. Resumen Ejecutivo

### Hallazgos Críticos

| # | Duplicado/Hardcode | Ubicación 1 | Ubicación 2 | Severidad | Acción |
|---|---|---|---|---|---|
| 1 | **Criterios de Riesgo** | `config/business_rules/riesgo_config.json` | `calculators/riesgo.py:73-84` | CRÍTICA | Centralizar en storage |
| 2 | **Umbrales de Riesgo** | `config/business_rules/riesgo_config.json:29-42` | `calculators/riesgo.py:86-105` | CRÍTICA | Centralizar en storage |
| 3 | **SMMLV (Salario Mínimo)** | `config/business_rules/riesgo_config.json:6` (1,423,500) | `calculators/riesgo.py:88` (hardcode) | ALTA | Sincronizar anualmente |
| 4 | **Reglas de Negocio** | `config/business_rules/reglas_negocio.json` | (estático) | MEDIA | Migrar a storage |
| 5 | **Versiones Antiguas** | `storage/parametrization/hr/` | (múltiples sin activación) | BAJA | Implementar política de retención |

### Impacto

- **Descalibración Silenciosa**: Si RiesgoCalculator lee hardcode en lugar de JSON, cambios a políticas no se aplican
- **Mantenibilidad**: Cambios anuales a SMMLV deben tocarse en 2 lugares (riesgo.py + riesgo_config.json)
- **Versionado**: Reglas de negocio no tienen versiones ni auditoría de cambios

### Recomendación

✓ **Decisión arquitectónica**: Migrar TODO a `storage/parametrization/business_rules/` con versionado, eliminando:
- `config/business_rules/` (directorio entero)
- Hardcodes en `calculators/riesgo.py`
- Fallbacks en `engine.py:_calcular_reglas_negocio()`

---

## 2. Inventario de Parametrización

### 2.1 Estructura Actual

```
backend_nexa/
├── config/
│   └── business_rules/
│       ├── reglas_negocio.json       ← ESTÁTICO, nunca versionado
│       └── riesgo_config.json        ← ESTÁTICO, nunca versionado
│
└── storage/
    └── parametrization/
        ├── hr/
        │   ├── versions.json         ✓ Versionado
        │   ├── 26ad1692-....json     ✓ Activo
        │   └── 386b6188-....json     (inactivo, fallback disponible)
        ├── op/
        │   ├── versions.json         ✓ Versionado
        │   └── a6824e05-....json     ✓ Activo
        └── gn/
            ├── versions.json         ✓ Versionado
            └── 11dac468-....json     ✓ Activo
```

### 2.2 Estado de Versiones

| Módulo | Versión Activa | Historial | Última Activación | Actualización |
|--------|---|---|---|---|
| HR | `26ad1692-...` | 2 versiones | 2026-05-19 16:50 | Puede cargarse nuevo Excel |
| OP | `a6824e05-...` | 1 versión | (fecha) | Puede cargarse nuevo Excel |
| GN | `11dac468-...` | 1 versión | (fecha) | Puede cargarse nuevo Excel |
| **business_rules** | (no existe) | NO VERSIONADO | (never) | ❌ Solo edición manual JSON |
| **riesgo_config** | (no existe) | NO VERSIONADO | (never) | ❌ Solo edición manual JSON |

---

## 3. Duplicados Confirmados

### 3.1 Duplicado #1: Criterios de Riesgo (10 criterios)

#### Ubicación A: JSON (`config/business_rules/riesgo_config.json`)

```json
{
  "criterios": [
    {"id": 1, "factor": "Clasificación de oportunidad", "categoria": "Cliente", "peso": 0.30},
    {"id": 2, "factor": "Tipo de cliente", "categoria": "Cliente", "peso": 0.25},
    {"id": 3, "factor": "Antigüedad del cliente", "categoria": "Cliente", "peso": 0.15},
    {"id": 4, "factor": "Volumen de contactos", "categoria": "Cliente", "peso": 0.10},
    {"id": 5, "factor": "Volatilidad de volumen", "categoria": "Operativo", "peso": 0.05},
    {"id": 6, "factor": "Madurez del proceso", "categoria": "Operativo", "peso": 0.10},
    {"id": 7, "factor": "Disponibilidad de talento", "categoria": "Operativo", "peso": 0.08},
    {"id": 8, "factor": "Costo de atracción y retención", "categoria": "Operativo", "peso": 0.07},
    {"id": 9, "factor": "Dependencia de tecnología", "categoria": "Tecnológico", "peso": 0.05},
    {"id": 10, "factor": "Dependencia de terceros", "categoria": "Operativo", "peso": 0.10}
  ]
}
```

#### Ubicación B: Python hardcodeado (`calculators/riesgo.py:73-84`)

```python
_DEFAULT_CRITERIOS_META = [
    (1,  "Clasificación de oportunidad", "Cliente",   0.30),
    (2,  "Tipo de cliente",              "Cliente",   0.25),
    (3,  "Antigüedad del cliente",       "Cliente",   0.15),
    (4,  "Volumen de contactos",         "Cliente",   0.10),
    (5,  "Volatilidad de volumen",       "Operativo", 0.05),
    (6,  "Madurez del proceso",          "Operativo", 0.10),
    (7,  "Disponibilidad de talento",    "Operativo", 0.08),
    (8,  "Costo de atracción y retención","Operativo", 0.07),
    (9,  "Dependencia de tecnología",    "Tecnológico", 0.05),
    (10, "Dependencia de terceros",      "Operativo", 0.10),
]
```

**Problema**: Exactamente idénticos. Si se actualiza JSON pero no el hardcode, hay inconsistencia silenciosa.

**Resolución actual** (línea 169 de riesgo.py):
```python
criterios = riesgo_config.get("criterios", _DEFAULT_CRITERIOS_META)
```
→ Lee JSON por defecto; si falta, usa hardcode (fallback).

**Riesgo**: Fallback silencioso es confuso. ¿Cuál es la fuente de verdad?

---

### 3.2 Duplicado #2: Umbrales de Riesgo (11 valores)

#### Ubicación A: JSON (`config/business_rules/riesgo_config.json:29-42`)

```json
{
  "umbrales": {
    "periodo_pago_alto": 60,
    "periodo_pago_bajo": 30,
    "alertas_alto": 3,
    "alertas_medio": 1,
    "margen_minimo": 0.10,
    "margen_objetivo": 0.15,
    "costo_fte_alto": 1500000,
    "costo_fte_bajo": 500000,
    "utilidad_minima_pct": 0.05,
    "volatilidad_max": 0.30,
    "antiguedad_minima_meses": 12
  }
}
```

#### Ubicación B: Python hardcodeado (`calculators/riesgo.py:93-102`)

```python
"umbrales": {
    "periodo_pago_alto": 60,
    "periodo_pago_bajo": 30,
    "alertas_alto": 3,
    "alertas_medio": 1,
    "margen_minimo": 0.10,
    "margen_objetivo": 0.15,
    "costo_fte_alto": 1500000,
    "costo_fte_bajo": 500000,
    "utilidad_minima_pct": 0.05,
    "volatilidad_max": 0.30,
    "antiguedad_minima_meses": 12
}
```

**Problema**: Duplicados exactos. Cambios deben tocar 2 archivos.

**Impacto**: Si el JSON se actualiza para un cambio de política, el código sigue usando hardcode (fallback).

---

### 3.3 Duplicado #3: SMMLV (Salario Mínimo Mensual Legal)

#### Ubicación A: JSON (`config/business_rules/riesgo_config.json:6`)

```json
{
  "constantes_regulatorias": {
    "smmlv": 1423500.0
  }
}
```

#### Ubicación B: Python hardcodeado (`calculators/riesgo.py:88`)

```python
"constantes_regulatorias": {
    "smmlv": 1_423_500.0,  # HARDCODE: backward compat
    ...
}
```

**Problema**: SMMLV es modificado anualmente por el gobierno colombiano (típicamente en enero).
- 2025: COP 1,423,500
- 2026: (pendiente de fijación)
- 2027: (pendiente de fijación)

Ambos lugares deben actualizarse cada año, o habrá descalibración en evaluación de riesgo.

**Cronograma típico**:
- Diciembre N: Gobierno anuncia SMMLV para año N+1
- Enero N+1: Entra en vigencia
- Marzo N+1: Nuestra actualización debe estar lista

---

### 3.4 Duplicado #4: Reglas de Negocio (5 políticas comerciales)

#### Ubicación A: JSON (`config/business_rules/reglas_negocio.json`)

```json
{
  "politicas": [
    {
      "nombre": "margen_objetivo",
      "label": "Margen objetivo",
      "min": null,
      "max": null
    },
    {
      "nombre": "contingencia_operativa",
      "label": "Contingencia Operativa",
      "min": 0.05,
      "max": 0.08
    },
    {
      "nombre": "contingencia_comercial",
      "label": "Contingencia Comercial",
      "min": 0.04,
      "max": 0.07
    },
    {
      "nombre": "markup",
      "label": "Markup",
      "min": 0.02,
      "max": 0.08
    },
    {
      "nombre": "descuento",
      "label": "Descuento volumen",
      "min": 0.0,
      "max": 0.08
    }
  ]
}
```

#### Ubicación B: Fallback en Python (`engine.py:278-283`)

```python
if parametrizacion is not None:
    politicas_config = parametrizacion.get_politicas_comerciales()
else:
    # Fallback for backward compat (tests without provider)
    politicas_config = [
        {"nombre": "margen_objetivo",        "label": "Margen objetivo",        "min": None, "max": None},
        {"nombre": "contingencia_operativa", "label": "Contingencia Operativa", "min": 0.05, "max": 0.08},
        {"nombre": "contingencia_comercial", "label": "Contingencia Comercial", "min": 0.04, "max": 0.07},
        {"nombre": "markup",                 "label": "Markup",                 "min": 0.02, "max": 0.08},
        {"nombre": "descuento",              "label": "Descuento volumen",      "min": 0.0,  "max": 0.08},
    ]
```

**Problema**: Si JSON se actualiza, fallback en código no se refleja (salvo que se actualice a mano).

**Riesgo**: Tests sin provider usan políticas anticuadas si JSON cambia.

---

## 4. Hardcodes Implícitos (No Documentados)

### 4.1 En Calculadoras

| Valor | Ubicación | Descripción | Debe Estar en | Decisión |
|-------|-----------|-------------|---|---|
| `10.0 × SMMLV` | `domain/services/nomina_cargada.py` | Factor corrector salarios altos (Ley 1819) | `storage` | Migrar a storage |
| `2.0 × SMMLV` | `domain/services/nomina_cargada.py` | Umbral auxilio transporte (Ley trabajo) | `storage` | Migrar a storage |
| `"70SMMLV_30IPC"`, `"80SMMLV_20IPC"` | `repositories/parametrization_provider.py:280-283` | Componentes indexación standard | `storage/op/ComponenteAcumulado` | ✓ Ya en storage |
| `0.0088` | `repositories/parametrization_provider.py` (comentario) | Tasa default financiación | `storage/op/Config` | ✓ Ya en storage |

### 4.2 Análisis de nomina_cargada.py

**Archivo**: `domain/services/nomina_cargada.py`

```python
def calcular(self, salario_base: float, comision_pct: float) -> float:
    """
    Calcula salario cargado aplicando aportes, prestaciones y correcciones legales.
    
    Constantes hardcodeadas:
    - 10.0 × SMMLV = umbral máximo para indexación salarial (Ley 1819)
    - 2.0 × SMMLV = umbral mínimo para auxilio transporte
    - 1.0, 0.3, 0.12, etc. = Porcentajes de aportes (pensión, SENA, ARL)
    """
```

**Problema**: Constantes derivadas de la ley colombiana (Ley 1819), pero algunos valores pueden cambiar anualmente.

**Recomendación**: Mover a `storage/parametrization/hr/costos_operativos/` con nombres explícitos:
```json
{
  "constantes_legales": {
    "umbral_indexacion_ley1819_smmlv": 10.0,
    "umbral_auxilio_transporte_smmlv": 2.0
  }
}
```

---

## 5. Acceso Actual a Parametrización

### 5.1 Ruta de Lectura: config/ (Estática)

```
ParametrizationProvider.get_politicas_comerciales()
  └─ Lee: config/business_rules/reglas_negocio.json (directamente)

ParametrizationProvider.get_riesgo_config()
  └─ Lee: config/business_rules/riesgo_config.json (directamente)
```

**Problema**: No hay versionado, sin auditoría de cambios, sin fallback a versión anterior.

### 5.2 Ruta de Lectura: storage/ (Versionada)

```
ParametrizationProvider.get_salario_rol(rol)
  └─ Lee: storage/parametrization/hr/{version_id_activa}/nomina

ParametrizationProvider.get_ratios_staff(linea)
  └─ Lee: storage/parametrization/hr/{version_id_activa}/ratios
  └─ Si es_activa=false, intenta fallback a versión anterior
```

**Ventaja**: Versionado completo, auditoría integrada.

---

## 6. Plan de Migración: config/ → storage/

### Fase A: Crear Estructura en storage/ (SIN ELIMINAR config/ AÚN)

```json
storage/parametrization/business_rules/
├── versions.json  ← Nuevo
│   [
│     {
│       "version_id": "xyz-2026-05-21",
│       "filename": "business_rules_2026-05-21.json",
│       "uploaded_at": "2026-05-21T09:00:00Z",
│       "is_active": true,
│       "sheet_count": 2,
│       "total_rows": 17,
│       "changed_by": "admin",
│       "change_reason": "Migración inicial desde config/"
│     }
│   ]
│
└── xyz-2026-05-21.json  ← Nuevo
    {
      "version_id": "xyz-2026-05-21",
      "reglas_negocio": [... políticas ...],
      "riesgo_config": {
        "constantes_regulatorias": {...},
        "umbrales": {...},
        "criterios": [...],
        "pesos": {...}
      }
    }
```

### Fase B: Actualizar ParametrizationProvider

**Archivo**: `repositories/parametrization_provider.py`

Cambiar:
```python
def get_riesgo_config(self) -> dict:
    # Antes: lee de config/business_rules/riesgo_config.json
    # Después: lee de storage/parametrization/business_rules/{version_id}/riesgo_config
```

### Fase C: Eliminar Hardcodes de Calculadoras

**Archivo**: `calculators/riesgo.py`

Cambiar:
```python
# Antes:
_DEFAULT_CRITERIOS_META = [...]  # ← ELIMINAR
_DEFAULT_RIESGO_CONFIG = {...}   # ← ELIMINAR

def __init__(self, riesgo_config: dict | None = None):
    if riesgo_config is None:
        riesgo_config = _DEFAULT_RIESGO_CONFIG  # ← ELIMINAR fallback

# Después:
def __init__(self, riesgo_config: dict):  # ← REQUERIDO, no optional
    self._config = riesgo_config
```

### Fase D: Crear Endpoints para Upload/Activate

**Ubicación**: `api/v1/parametrization/` (crear nuevos routers si es necesario)

```python
POST /api/v1/parametrization/business_rules/upload
  └─ Carga archivo JSON con reglas_negocio + riesgo_config
  └─ Valida estructura
  └─ Guarda en storage/parametrization/business_rules/{version_id}.json
  └─ Actualiza versions.json con is_active=false

POST /api/v1/parametrization/business_rules/{version_id}/activate
  └─ Establece is_active=true para esa versión
  └─ Setea is_active=false para la versión anterior
```

### Fase E: Eliminar config/business_rules/

Solo después de:
1. ✓ Todos los datos están en storage/
2. ✓ Endpoints están funcionando
3. ✓ Tests pasan
4. ✓ Admin ha activado versión en storage (no en config/)

```bash
rm -rf config/business_rules/
```

---

## 7. Timeline de Migración

| Hito | Fecha | Responsable | Validación |
|------|-------|-------------|-----------|
| Crear estructura storage/business_rules/ | 2026-05-22 | Dev | Schema validado |
| Migrar datos de config/ | 2026-05-22 | Dev | Contenidos idénticos |
| Actualizar ParametrizationProvider | 2026-05-22 | Dev | Tests pasan |
| Eliminar hardcodes de riesgo.py | 2026-05-23 | Dev | Tests pasan, sin fallbacks |
| Crear endpoints de upload/activate | 2026-05-23 | Dev | Smoke test en admin panel |
| Tests de reproducibilidad | 2026-05-24 | QA | Same input → Same output |
| Eliminar config/business_rules/ | 2026-05-25 | Dev | Backup en git |
| Auditoría final | 2026-05-26 | Admin | Confirmar storage es única fuente |

---

## 8. Validación de Migración

### 8.1 Checklist Técnico

- [ ] `storage/parametrization/business_rules/versions.json` exists y es readable
- [ ] First version in storage has is_active=true
- [ ] `ParametrizationProvider.get_riesgo_config()` reads from storage (not config/)
- [ ] `ParametrizationProvider.get_politicas_comerciales()` reads from storage (not config/)
- [ ] `RiesgoCalculator` no tiene hardcodes `_DEFAULT_*`
- [ ] `engine.py:_calcular_reglas_negocio()` no tiene fallback hardcodeado
- [ ] All tests pass with new source
- [ ] Sample deal calculates identically (before and after migration)

### 8.2 Prueba de Reproducibilidad

```python
# Test: Migración no rompe cálculos
def test_business_rules_migration():
    # Antes: config/ active
    before = engine.calcular(request_muestra)
    
    # Después: storage/ active
    after = engine.calcular(request_muestra)
    
    assert before.kpis.margen == after.kpis.margen
    assert before.reglas_negocio == after.reglas_negocio
    assert before.evaluacion_riesgo.score == after.evaluacion_riesgo.score
```

---

## 9. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|---|---|---|
| Desincronización JSON-Python durante transición | MEDIA | ALTO | Fase A: crear estructura sin eliminar config/ |
| Fallback silencioso a código antiguo | MEDIA | ALTO | Fase C: eliminar fallbacks + required params |
| Admin sigue modificando config/ en lugar de storage/ | ALTA | MEDIO | Fase E: eliminar directorio + documentación |
| Tests fallan por tipos de datos | BAJA | BAJO | Phase D: validar schema JSON en upload |

---

## 10. Conclusiones

### Estado Actual: ⚠️ Crítico

- 3 duplicados confirmados (criterios, umbrales, SMMLV)
- 1 fallback silencioso (reglas_negocio)
- Descalibración potencial si JSON y hardcodes no se sincronizan

### Recomendación: ✓ Migrar TODO a storage/

**Por qué**:
- ✓ Versionado integrado
- ✓ Auditoría de cambios
- ✓ Fallback a versiones anteriores
- ✓ Admin puede cambiar sin código
- ✓ Single source of truth

**Impacto**: 
- Esfuerzo: 2-3 días (dev + QA)
- Riesgo: Bajo (bien testeable)
- Beneficio: Alto (elimina duplicados, gana versionado)

---

## 11. Archivos Afectados (Resumen)

| Archivo | Cambio | Fase |
|---------|--------|------|
| `storage/parametrization/business_rules/` | Crear estructura | A |
| `repositories/parametrization_provider.py` | Leer de storage | B |
| `calculators/riesgo.py` | Eliminar hardcodes | C |
| `api/v1/parametrization/business_rules_router.py` | Crear endpoints | D |
| `config/business_rules/` | Eliminar (archivo) | E |
| `tests/` | Actualizar tests | A-D |

---

**Siguiente**: Fase 3 — Auditoría de Consistencia Nomenclatural
