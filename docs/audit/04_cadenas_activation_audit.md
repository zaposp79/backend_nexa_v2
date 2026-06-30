# Auditoría de Activación de Cadenas (A, B, C)

**Versión**: 2026-05-21  
**Estado**: Auditoría Fase 4  
**Objetivo**: Validar que Cadena A, B, C solo participen en cálculos cuando estén activas desde panel_de_control.

---

## 1. Resumen Ejecutivo

### Hallazgo Principal

**⚠️ CRÍTICO**: No se encontró validación explícita de `cadena_a_activa`, `cadena_b_activa`, `cadena_c_activa` en el motor.

**Riesgo**: Una cadena inactiva podría contribuir a costos/resultados si contiene datos.

**Nivel Severidad**: ALTO (lógica de negocio)

---

## 2. Validación de Requisitos

### 2.1 Panel de Control — Flags de Activación

**Ubicación esperada**: `entry_data/panel_control_copy.json` (o similar)

```json
{
  "panel_de_control": {
    "cliente": "...",
    "cadena_a_activa": true,     // ← Debe validar entrada
    "cadena_b_activa": false,    // ← Debe validar entrada  
    "cadena_c_activa": false     // ← Debe validar entrada
  }
}
```

**Estado actual**: 
- ✓ Estructura esperada definida
- ⚠️ Validación NOT FOUND en engine.py
- ⚠️ NO SE VALIDA en context_builder.py
- ⚠️ Calculadoras reciben datos aunque cadena esté inactiva

---

## 3. Análisis de Flujo Actual

### 3.1 Entrada de Datos (entry_data/)

```json
{
  "panel_de_control": {...},
  "condiciones_cadena_a": { "perfiles": [...] },  // ← siempre se procesa
  "condiciones_cadena_b": { ... },                 // ← siempre se procesa
  "condiciones_cadena_c": { ... }                  // ← siempre se procesa
}
```

**Problema**: Ningún campo indica activación.

**Recomendación**: Agregar flags:
```json
{
  "panel_de_control": {
    "cadena_a_activa": true,
    "cadena_b_activa": false,
    "cadena_c_activa": false
  },
  "condiciones_cadena_a": { ... },
  "condiciones_cadena_b": { ... },
  "condiciones_cadena_c": { ... }
}
```

---

### 3.2 SimulationContextBuilder — Procesamiento

**Archivo**: `adapters/context_builder.py`

**Análisis**:
```python
def construir(self, user_input: UserInput) -> PricingRequest:
    # ...
    perfiles_cadena_a = self._construir_perfiles_a(user_input.cadena_a, ...)  # ← SIEMPRE procesa
    cadena_b = self._construir_cadena_b(user_input.cadena_b, ...)             # ← SIEMPRE procesa
    cadena_c = self._construir_cadena_c(user_input.cadena_c)                  # ← SIEMPRE procesa
    
    return PricingRequest(
        perfiles_cadena_a=perfiles_cadena_a,  # ← Nunca valida si está vacío
        cadena_b=cadena_b,
        cadena_c=cadena_c,
    )
```

**Problema**: No hay validación de activación. Si cadena_b_activa=false, ¿debería:
- A) Procesar y calcular costo_b (estado actual)
- B) Establecer cadena_b=None o cadena_b.items=[]
- C) Rechazar con error de validación

**Recomendación**: ✓ **Opción B** — si cadena inactiva, inicializar vacía (neutral, cost=0).

---

### 3.3 NexaPricingEngine — Orquestación

**Archivo**: `engine.py`

**Análisis**:
```python
def calcular(self, solicitud: PricingRequest) -> PricingResult:
    calculadores = self._construir_calculadores(solicitud)
    
    # Capa 2: NominaCalculator
    # → Usa solicitud.perfiles_cadena_a (¿qué si cadena_a_activa=false?)
    
    # Capa 4-5: CadenaBCalculator
    # → Usa solicitud.cadena_b (¿qué si cadena_b_activa=false?)
    
    # Capa 6: CadenaCCalculator
    # → Usa solicitud.cadena_c (¿qué si cadena_c_activa=false?)
```

**Problema**: No hay condicionales basados en activación.

---

### 3.4 Calculadoras — Implementación

#### NominaCalculator

**Archivo**: `calculators/nomina.py`

**Análisis**: Depende de perfiles_cadena_a. Si cadena_a_activa=false, ¿debería:
- A) Retornar costo=0
- B) Procesar igual
- C) Rechazar con error

**Recomendación**: Si cadena_a_activa=false, perfiles_cadena_a debe estar vacía.

#### CadenaBCalculator

**Archivo**: `calculators/cadena_b.py`

**Análisis**: Calcula costo_b desde canales y OPEX items.

**Problema**: 
```python
def calcular(self, perfiles_a: List[PerfilCadenaA], cadena_b: ParametrosCadenaB) -> ResultadoCadenaB:
    # Procesa cadena_b sin verificar si está activa
    # Si cadena_b_activa=false pero items contienen datos, calcular costo=0 igual
```

**Recomendación**: Agregar check explícito:
```python
if not request.panel.cadena_b_activa:
    return ResultadoCadenaB(...)  # costo=0, opex=0
```

#### CadenaCCalculator

**Archivo**: `calculators/cadena_c.py`

Mismo análisis que CadenaBCalculator.

---

## 4. Plan de Validación

### Fase A: Agregar Flags a entry_data

**Archivo**: `entry_data/panel_control_copy.json`

```json
{
  "panel_de_control": {
    // ... campos existentes ...
    "cadena_a_activa": true,
    "cadena_b_activa": false,
    "cadena_c_activa": false
  }
}
```

**Cambios necesarios**:
1. Agregar fields a `PanelDeControlInput` (user_inputs.py)
2. Agregar fields a `PanelDeControl` (models.py)
3. Validar en input_validator.py

---

### Fase B: Validación en context_builder

**Cambio**:
```python
def _construir_cadena_b(self, input_cadena_b, panel: PanelDeControl) -> ParametrosCadenaB:
    if not panel.cadena_b_activa:
        return ParametrosCadenaB(canales=[], opex=ParametrosOpexCadenaB(items=[]))  # Neutral
    
    # Procesar normalmente
    return ParametrosCadenaB(...)
```

Mismo patrón para cadena_c.

---

### Fase C: Validación en Calculadoras

**Cambios explícitos en cada calculadora**:
```python
class CadenaBCalculator:
    def calcular(...) -> ResultadoCadenaB:
        if not self.panel.cadena_b_activa:
            return ResultadoCadenaB(costo_opex_fijo=0.0, costo_opex_consumo=0.0)
        # ... calcular normalmente ...
```

**Beneficio**: Código defensivo, explícito.

---

### Fase D: Validación en Resultados

**Verificar**:
1. Si cadena_a_activa=false → PyGMensual.payroll_a=0
2. Si cadena_b_activa=false → PyGMensual.costo_b=0
3. Si cadena_c_activa=false → PyGMensual.costo_c=0

**Test de reproducibilidad**:
```python
def test_cadena_inactiva_no_contribuye():
    # Setup: cadena_b_activa=false
    request_sin_b = make_request(cadena_b_activa=False)
    
    # Calcular
    result_sin_b = engine.calcular(request_sin_b)
    
    # Verificar
    for pyg in result_sin_b.pyg_por_mes:
        assert pyg.costo_b == 0.0, "Cadena B inactiva debe tener costo=0"
        assert pyg.costo_total_operacional == pyg.costo_a + pyg.costo_c
```

---

## 5. Matriz de Impacto

| Componente | Cambio Necesario | Riesgo | Esfuerzo |
|---|---|---|---|
| entry_data schema | Agregar 3 flags bool | BAJO | 0.5 días |
| UserInput model | Agregar 3 fields | BAJO | 0.5 días |
| context_builder | Validar activación | BAJO | 1 día |
| Calculadoras (3×) | Agregar checks | BAJO | 1 día |
| Tests | New test cases (5+) | BAJO | 1 día |
| **Total** | — | — | **4 días** |

---

## 6. Casos de Prueba

### 6.1 Todos Activos

```json
{
  "cadena_a_activa": true,
  "cadena_b_activa": true,
  "cadena_c_activa": true
}
```

**Resultado esperado**: 
- Todas las cadenas contribuyen a costos
- PyG = A + B + C + Financiero

### 6.2 Solo Cadena A

```json
{
  "cadena_a_activa": true,
  "cadena_b_activa": false,
  "cadena_c_activa": false
}
```

**Resultado esperado**:
- costo_b = 0
- costo_c = 0
- PyG = A + Financiero

### 6.3 Solo Cadena B

```json
{
  "cadena_a_activa": false,
  "cadena_b_activa": true,
  "cadena_c_activa": false
}
```

**Resultado esperado**:
- payroll_a = 0 (no hay perfiles)
- costo_b = valor
- costo_c = 0

### 6.4 Ninguno Activo

```json
{
  "cadena_a_activa": false,
  "cadena_b_activa": false,
  "cadena_c_activa": false
}
```

**Resultado esperado**:
- costo_total_operacional = 0
- Válido solo para deals "fantasma" o tests

---

## 7. Archivos Afectados

| Archivo | Cambio | Fase |
|---------|--------|------|
| `domain/user_inputs.py` | Agregar cadena_*_activa fields | A |
| `domain/models.py` | Agregar cadena_*_activa fields | A |
| `adapters/context_builder.py` | Validar activación | B |
| `calculators/cadena_b.py` | Check explicit | C |
| `calculators/cadena_c.py` | Check explicit | C |
| `tests/` | New test cases | D |

---

## 8. Conclusiones

| Criterio | Estado | Acción |
|----------|--------|--------|
| **Flags de activación definidos** | ⚠️ No existen en entry_data | Agregar |
| **Validación en context_builder** | ❌ No existe | Implementar |
| **Checks en calculadoras** | ❌ No existen | Implementar |
| **Tests de reproducibilidad** | ❌ No existen | Crear |
| **Documentación** | ❌ Falta | Agregar |

**Riesgo Actual**: Cadena inactiva podría contribuir a costos si contiene datos (bug potencial).

**Recomendación**: ✓ Implementar validación completa antes de Fase 8 (estandarización nomenclatural).

---

**Siguiente**: Fase 5 — Auditoría de Calculadoras vs Excel
