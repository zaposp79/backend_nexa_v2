# ✅ REFACTOR costos_operativos — RESUMEN EJECUTIVO

**Fecha:** 2026-05-27  
**Estado:** READY FOR IMPLEMENTATION

---

## 🎯 EN 60 SEGUNDOS

### Problema
El motor tiene **6 campos en `costos_operativos`** que mezclan 4 tipos de datos distintos sin separación clara, causando:
- ❌ 6 tests bloqueados
- ❌ Ambigüedad de fuentes
- ❌ Validación imposible

### Solución
**Eliminar `HR-costos_operativos` por completo** y reclasificar cada campo según su naturaleza:

| Campo | ❌ Antes | ✅ Después |
|-------|---------|-----------|
| `tarifa_dia_cap` | Storage HR | JSON usuario |
| `opex_ti_por_estacion` | Storage HR | **Calculado** desde `opex_fijo[]` |
| `capex_recurrente` | Storage HR | **Calculado** desde `inversiones[]` |
| `capex_inicial` | Storage HR | **Calculado** desde `inversiones[]` |
| `pct_aumento_tecnologico` | Storage HR | `OP-Componente` (IPC) |
| `mes_inicio_ajuste` | Storage HR | **Constante** `=1` |

### Resultado
✅ Single source of truth  
✅ Motor 100% determinístico  
✅ Trazabilidad completa

**Tiempo estimado:** 6 horas

---

## 📊 ANTES vs DESPUÉS

### ❌ ARQUITECTURA ACTUAL (INCORRECTA)

```
┌─────────────────────────────────────────────────┐
│ Usuario envía JSON                              │
│ {                                               │
│   "tarifa_diaria_capacitacion": 20000 ← IGNORA │
│ }                                               │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ Motor busca en HR-costos_operativos             │
│ └─ ParametrizationError: sección no existe     │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
        ❌ MOTOR BLOQUEADO
        ❌ 6 TESTS FALLAN
```

**Problemas:**
1. **Duplicación**: `tarifa_dia_cap` existe en JSON (ignorado) y HR (falta)
2. **Hardcodes**: `opex_ti_por_estacion = 180,400` (¿de dónde sale?)
3. **Cálculos persistidos**: `capex_recurrente = 58,471` (es 3.5M / 60 meses)
4. **Constante disfrazada**: `mes_inicio_ajuste = 1` (siempre enero)

---

### ✅ ARQUITECTURA OBJETIVO (CORRECTA)

```
┌─────────────────────────────────────────────────┐
│ Usuario envía JSON                              │
│ {                                               │
│   "tarifa_diaria_capacitacion": 20000,  ✓      │
│   "opex_fijo": [{...}],                 ✓      │
│   "inversiones": [{...}]                ✓      │
│ }                                               │
└───────────────────┬─────────────────────────────┘
                    │
       ┌────────────┼────────────┐
       │            │            │
       ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ tarifa   │ │ CALCULA  │ │ CALCULA  │
│ (DIRECTO)│ │ OPEX TI  │ │ CAPEX    │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     └────────────┼────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│ Parametrización: IPC desde OP-Componente        │
│ Constante: MES_INICIO = 1                       │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
        ✅ MOTOR FUNCIONA
        ✅ TESTS PASAN
```

**Ventajas:**
1. **Single source**: Cada campo tiene exactamente 1 fuente
2. **Dinámico**: Cambios en JSON → reflejados inmediatamente
3. **Auditable**: Cada valor trazable hasta origen
4. **Determinista**: Mismo input → mismo output siempre

---

## 🔄 TRANSFORMACIÓN POR CAMPO

### 1. `tarifa_dia_cap`

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Fuente** | `HR-costos_operativos` (no existe) | `datos_operativos.tarifa_diaria_capacitacion` |
| **Tipo** | Parametrización (❌ incorrecto) | User Input (✅ correcto) |
| **Código** | `self._prov.get_costo_operativo("tarifa_dia_cap")` | `panel.tarifa_diaria_capacitacion` |
| **Validación** | Falla si falta HR | Falla si falta JSON (early) |

---

### 2. `opex_ti_por_estacion`

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Fuente** | `HR-costos_operativos` (valor fijo: 180,400) | Calculado desde `opex_fijo.items[]` |
| **Tipo** | Parametrización (❌ incorrecto) | Derived (✅ correcto) |
| **Código** | `self._prov.get_costo_operativo("opex_ti_por_estacion")` | `self._calcular_opex_ti_total(perfiles)` |
| **Fórmula** | ❓ (hardcoded, origen desconocido) | `Σ(Internet + Licencias + ...) / estaciones` |

**Ejemplo real Excel V2-6:**
```
Inbound Voz:
  - Internet: 450,000 / 10 estaciones = 45,000
  - Licencias CX1: 1,200,000 / 10 = 120,000
  TOTAL: 165,000 COP/estación
```

---

### 3. `capex_recurrente_por_estacion`

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Fuente** | `HR-costos_operativos` (valor fijo: 58,471) | Calculado desde `inversiones[]` |
| **Tipo** | Parametrización (❌ incorrecto) | Derived (✅ correcto) |
| **Código** | `self._prov.get_costo_operativo("capex_recurrente_por_estacion")` | `self._calcular_capex_recurrente(perfiles)` |
| **Fórmula** | ❓ (resultado persistido) | `Σ(precio / meses_amortización) / estaciones` |

**Ejemplo real Excel V2-6:**
```
PC Desktop: 3,508,260 / 60 meses = 58,471 COP/mes/estación
```

---

### 4. `capex_inicial_por_estacion`

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Fuente** | `HR-costos_operativos` (valor fijo: 3,628,212) | Calculado desde `inversiones[]` |
| **Tipo** | Parametrización (❌ incorrecto) | Derived (✅ correcto) |
| **Código** | `self._prov.get_costo_operativo("capex_inicial_por_estacion")` | `self._calcular_capex_inicial(perfiles)` |
| **Fórmula** | ❓ (suma desconocida) | `Σ(precio_total_inversión) / estaciones` |

---

### 5. `pct_aumento_tecnologico_anual`

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Fuente** | `HR-costos_operativos` (valor fijo: 0.0527) | `OP-Componente` → IPC del año |
| **Tipo** | Parametrización HR (❌ módulo incorrecto) | Parametrización OP (✅ módulo correcto) |
| **Código** | `self._prov.get_costo_operativo("pct_aumento_tecnologico_anual")` | `self._prov.get_componente_indexacion("IPC", año)` |
| **Actualización** | Manual en HR (no versionado) | Automático desde Excel OP |

---

### 6. `mes_inicio_ajuste_anual`

| Aspecto | ANTES | DESPUÉS |
|---------|-------|---------|
| **Fuente** | `HR-costos_operativos` (valor fijo: 1) | Constante backend |
| **Tipo** | Parametrización (❌ incorrecto) | Constant (✅ correcto) |
| **Código** | `int(self._prov.get_costo_operativo("mes_inicio_ajuste_anual"))` | `MES_INICIO_AJUSTE_ANUAL` |
| **Ubicación** | Storage JSON | `domain/constants.py` |

**Justificación:** Es una constante fiscal de Colombia (enero = mes 1). NO varía por deal ni parametrización.

---

## 📂 IMPACTO EN ARCHIVOS

### Resumen

| Acción | Cantidad | Descripción |
|--------|----------|-------------|
| ✅ **CREAR** | 3 | `constants.py`, tests, docs |
| 🔧 **MODIFICAR** | 11 | DTOs, adapters, context_builder, repos, validator |
| 🗑️ **ELIMINAR** | 2 métodos | `get_costo_operativo()` en 2 repos |

**Total archivos impactados:** 16

---

## ⏱️ PLAN DE IMPLEMENTACIÓN

| # | Fase | Duración | Descripción |
|---|------|----------|-------------|
| 1 | Preparación | 30 min | Crear `constants.py`, agregar DTOs |
| 2 | Cálculos Derivados | 2 horas | Implementar 3 métodos de cálculo |
| 3 | Parametrización IPC | 1 hora | `get_componente_indexacion()` |
| 4 | Adapters | 30 min | Mapear input usuario |
| 5 | Constantes | 15 min | Reemplazar en 5 ubicaciones |
| 6 | Eliminar Legacy | 30 min | Borrar código obsoleto |
| 7 | Tests | 1.5 horas | Nuevos tests + fixtures |

**TOTAL:** 6 horas

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Funcional
- [ ] Motor ejecuta sin `ParametrizationError`
- [ ] `tarifa_dia_cap` proviene de `panel.tarifa_diaria_capacitacion`
- [ ] OPEX TI calculado desde `opex_fijo[]`
- [ ] CAPEX calculado desde `inversiones[]`
- [ ] IPC desde `OP-Componente`
- [ ] `MES_INICIO_AJUSTE_ANUAL` constante

### Arquitectónico
- [ ] Single source of truth por campo
- [ ] Separación: INPUT | PARAMETRIZATION | DERIVED | CONSTANT
- [ ] Cero hardcodes en parametrización
- [ ] Trazabilidad completa (cada valor auditable)

### Tests
- [ ] 100% certificación pasa (L1, L2, L3)
- [ ] Nuevos tests unitarios para cálculos
- [ ] Fixtures actualizados (sin `costos_operativos`)

---

## 📈 BENEFICIOS

### Antes del Refactor

| Métrica | Valor |
|---------|-------|
| Fuentes por campo | 1-4 (ambiguo) |
| Valores hardcodeados | 6 |
| Tests bloqueados | 6 |
| Trazabilidad | ❌ Imposible |
| Validación parametrización | ❌ Incompleta |
| Mantenibilidad | ⚠️ Baja |

### Después del Refactor

| Métrica | Valor |
|---------|-------|
| Fuentes por campo | **1 (único)** ✅ |
| Valores hardcodeados | **0** ✅ |
| Tests bloqueados | **0** ✅ |
| Trazabilidad | **100%** ✅ |
| Validación parametrización | **100%** ✅ |
| Mantenibilidad | **Alta** ✅ |

---

## 🚀 PRÓXIMOS PASOS

1. **Aprobar este diseño** (Product Owner + Lead Dev)
2. **Ejecutar FASE 1-7** (6 horas desarrollo)
3. **Ejecutar suite de tests** (certificación L1-L3)
4. **Merge a main** (después de code review)
5. **Documentar en changelog**

---

## 📚 DOCUMENTOS RELACIONADOS

1. **[ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md](ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md)** — Documento técnico completo (60 páginas)
2. **[COSTOS_OPERATIVOS_OWNERSHIP_MAP.md](COSTOS_OPERATIVOS_OWNERSHIP_MAP.md)** — Mapa de ownership visual
3. **[COSTOS_OPERATIVOS_CODE_EXAMPLES.md](COSTOS_OPERATIVOS_CODE_EXAMPLES.md)** — Ejemplos de código antes/después

---

## ✍️ APROBACIÓN

- [ ] **Product Owner / Arquitecto Backend**  
- [ ] **Lead Developer**  
- [ ] **QA Lead**

**Firma:**  
```
Aprobado por: _______________________
Fecha: _______________________
```

---

**FIN DEL RESUMEN EJECUTIVO**
