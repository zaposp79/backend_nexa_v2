# MAPA DE OWNERSHIP: costos_operativos

**Versión:** 2.0 Final  
**Fecha:** 2026-05-27  
**Estado:** READY FOR IMPLEMENTATION

---

## 🎯 PROBLEMA

El motor tiene **ambigüedad en fuentes de datos** porque `costos_operativos` mezcla:
- INPUT del usuario (debería venir en JSON)
- PARAMETRIZACIÓN (debería estar en storage versionado)
- CÁLCULOS DERIVADOS (debería calcularse en runtime)
- CONSTANTES (debería estar en código fuente)

**Resultado:** 6 tests fallan, motor bloqueado, validación imposible.

---

## 📊 MAPA DE OWNERSHIP FINAL

### Tabla Maestra de Reclasificación

| **Campo** | **❌ Fuente Actual** | **✅ Fuente Correcta** | **Tipo** | **Acción** |
|-----------|---------------------|------------------------|----------|-----------|
| `tarifa_dia_cap` | `HR-costos_operativos` | `datos_operativos.tarifa_diaria_capacitacion` | **INPUT** | Mapear desde JSON usuario |
| `opex_ti_por_estacion` | `HR-costos_operativos` | Calcular desde `opex_fijo.items[]` | **DERIVED** | Método `_calcular_opex_ti_total()` |
| `capex_recurrente_por_estacion` | `HR-costos_operativos` | Calcular desde `inversiones[]` | **DERIVED** | Método `_calcular_capex_recurrente()` |
| `capex_inicial_por_estacion` | `HR-costos_operativos` | Calcular desde `inversiones[]` | **DERIVED** | Método `_calcular_capex_inicial()` |
| `pct_aumento_tecnologico_anual` | `HR-costos_operativos` | `OP-Componente` → IPC del año | **PARAMETRIZATION** | Nuevo método `get_componente_indexacion()` |
| `mes_inicio_ajuste_anual` | `HR-costos_operativos` | `MES_INICIO_AJUSTE_ANUAL = 1` | **CONSTANT** | Constante en `domain/constants.py` |

---

## 🔄 FLUJO ANTES vs DESPUÉS

### ❌ ANTES (INCORRECTO)

```
Usuario (JSON)
     │
     ▼
Backend busca en HR-costos_operativos
     │
     ▼
ParametrizationError: sección no existe
     │
     ▼
❌ MOTOR BLOQUEADO
```

### ✅ DESPUÉS (CORRECTO)

```
┌─────────────────────────────────────────┐
│  USER INPUT (JSON)                      │
│  ✓ tarifa_diaria_capacitacion           │
│  ✓ opex_fijo.items[]                    │
│  ✓ inversiones[]                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  CONTEXT BUILDER                        │
│  ✓ Mapea tarifa_dia_cap directamente   │
│  ✓ Calcula OPEX TI desde items         │
│  ✓ Calcula CAPEX desde inversiones     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  PARAMETRIZATION PROVIDER               │
│  ✓ Obtiene IPC desde OP-Componente     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  CONSTANTS                              │
│  ✓ MES_INICIO_AJUSTE_ANUAL = 1         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  ✅ MOTOR FUNCIONA                      │
└─────────────────────────────────────────┘
```

---

## 📂 ARCHIVOS A MODIFICAR

### ✅ CREAR (3 archivos)

| Archivo | Propósito |
|---------|-----------|
| `domain/constants.py` | Constantes backend |
| `tests/unit/test_context_builder_calculations.py` | Tests para cálculos |
| `docs/ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md` | Documento técnico completo |

### 🔧 MODIFICAR (11 archivos)

| Archivo | Cambio Principal | Impacto |
|---------|-----------------|---------|
| `domain/models/panel.py` | `+ tarifa_diaria_capacitacion: float` | Bajo |
| `domain/user_inputs.py` | `+ tarifa_diaria_capacitacion: float` | Bajo |
| `simulation/panel/dto.py` | `+ tarifa_cap: float` | Bajo |
| `adapters/unified_input_adapter.py` | Mapear `tarifaCap` → campo | Bajo |
| `adapters/json_loader.py` | Leer desde panel | Bajo |
| `input/context_builder.py` | **6 CAMBIOS PRINCIPALES** | **ALTO** |
| `repositories/financial_parametrization_repository.py` | `+ get_economic_component()` | Medio |
| `repositories/parametrization_provider.py` | `+ get_componente_indexacion()` | Medio |
| `validators/parametrization_completeness_validator.py` | Eliminar `costos_operativos` | Medio |
| `tests/unit/test_calculators_nomina.py` | Fixtures | Bajo |
| `tests/integration/test_payroll_components.py` | Fixtures | Bajo |

### 🗑️ ELIMINAR (2 métodos)

| Archivo | Método | Razón |
|---------|--------|-------|
| `repositories/payroll_parametrization_repository.py` | `get_costo_operativo()` | Ya no se necesita |
| `repositories/parametrization_provider.py` | `get_costo_operativo()` wrapper | Ya no se necesita |

---

## 📈 IMPACTO POR TIPO DE FUENTE

### INPUT USUARIO

| Campo | JSON Path | Validación |
|-------|-----------|-----------|
| `tarifa_dia_cap` | `datos_operativos.tarifa_diaria_capacitacion` | REQUERIDO |
| `opex_ti` (items) | `condiciones_cadena_a[].opex_fijo.items[]` | OPCIONAL (0.0 si vacío) |
| `capex` (inversiones) | `condiciones_cadena_a[].inversiones[]` | OPCIONAL (0.0 si vacío) |

### PARAMETRIZACIÓN

| Campo | Fuente Storage | Sección |
|-------|---------------|---------|
| `pct_aumento_tecnologico` | `storage/parametrization/op/{version}.json` | `componente` |

### CALCULADO BACKEND

| Campo | Fórmula | Método |
|-------|---------|--------|
| `opex_ti_por_estacion` | `Σ(opex_fijo[tipo='TI']) / estaciones` | `_calcular_opex_ti_total()` |
| `capex_recurrente` | `Σ(precio / meses_amort) / estaciones` | `_calcular_capex_recurrente()` |
| `capex_inicial` | `Σ(precio_total) / estaciones` | `_calcular_capex_inicial()` |

### CONSTANTE BACKEND

| Constante | Valor | Ubicación |
|-----------|-------|-----------|
| `MES_INICIO_AJUSTE_ANUAL` | `1` (enero) | `domain/constants.py` |

---

## ⏱️ PLAN DE IMPLEMENTACIÓN (6 horas)

| Fase | Duración | Tareas |
|------|----------|--------|
| **FASE 1:** Preparación | 30 min | Crear `constants.py`, agregar DTOs |
| **FASE 2:** Cálculos | 2 horas | Implementar 3 métodos de cálculo |
| **FASE 3:** Parametrización IPC | 1 hora | `get_componente_indexacion()` |
| **FASE 4:** Adapters | 30 min | Mapear input usuario |
| **FASE 5:** Constantes | 15 min | Reemplazar en 5 ubicaciones |
| **FASE 6:** Eliminar Legacy | 30 min | Borrar `get_costo_operativo()` |
| **FASE 7:** Tests | 1.5 horas | Nuevos tests + fixtures |

**TOTAL:** 6 horas

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Funcional
- [ ] Motor ejecuta sin `ParametrizationError`
- [ ] `tarifa_dia_cap` desde `panel.tarifa_diaria_capacitacion`
- [ ] OPEX TI calculado desde `opex_fijo[]`
- [ ] CAPEX calculado desde `inversiones[]`
- [ ] IPC desde `OP-Componente`
- [ ] `MES_INICIO_AJUSTE_ANUAL` constante

### Arquitectónico
- [ ] Single source of truth por campo
- [ ] Separación: INPUT | PARAMETRIZATION | DERIVED | CONSTANT
- [ ] Cero hardcodes en parametrización
- [ ] Trazabilidad completa

### Tests
- [ ] 100% certificación pasa (L1, L2, L3)
- [ ] Nuevos tests unitarios para cálculos
- [ ] Fixtures actualizados

---

## 🔥 RESULTADO FINAL

### ✅ VENTAJAS

1. **Single Source of Truth** — cada campo exactamente una fuente
2. **Trazabilidad** — cada valor auditable hasta origen
3. **Validación Early** — errores detectados inmediatamente
4. **Mantenibilidad** — cambios en input reflejados automáticamente
5. **Determinismo** — motor 100% reproducible

### ❌ ANTES vs ✅ DESPUÉS

| Característica | ANTES | DESPUÉS |
|----------------|-------|---------|
| Fuentes de `tarifa_dia_cap` | 4 (ambiguo) | 1 (clara) |
| Valores hardcodeados | 6 | 0 |
| Secciones parametrización | `costos_operativos` (ficticia) | Solo reales |
| Tests bloqueados | 6 | 0 |
| Motor determinístico | ❌ | ✅ |

---

## 📝 NOTAS IMPORTANTES

1. **NO crear `HR-costos_operativos`** — eliminarlo completamente es la solución correcta
2. **Validar payload usuario** — debe incluir `tarifa_diaria_capacitacion` SIEMPRE
3. **IPC debe existir en OP-Componente** — agregar años futuros en Excel OP
4. **Backwards compatibility** — legacy JSONs deben actualizarse

---

**FIN DEL MAPA DE OWNERSHIP**
