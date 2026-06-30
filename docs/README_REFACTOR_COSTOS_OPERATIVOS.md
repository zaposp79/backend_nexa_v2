# 📘 REFACTOR COSTOS_OPERATIVOS — ÍNDICE MAESTRO

**Versión:** 2.0 Final  
**Fecha:** 2026-05-27  
**Estado:** ✅ READY FOR IMPLEMENTATION

---

## 🎯 RESUMEN DEL REFACTOR

El motor financiero NEXA tiene **ambigüedad en las fuentes de datos** del módulo `costos_operativos`. Este refactor **elimina `HR-costos_operativos` por completo** y reclasifica cada campo según su naturaleza funcional:

| **Tipo** | **Campos** | **Acción** |
|----------|-----------|-----------|
| **INPUT** | `tarifa_dia_cap` | Mapear desde JSON usuario |
| **PARAMETRIZACIÓN** | `pct_aumento_tecnologico` | Obtener desde `OP-Componente` (IPC) |
| **CALCULADO** | `opex_ti`, `capex_recurrente`, `capex_inicial` | Calcular dinámicamente en runtime |
| **CONSTANTE** | `mes_inicio_ajuste` | Definir como constante backend |

**Resultado:**  
✅ Single source of truth  
✅ Motor 100% determinístico  
✅ Trazabilidad completa  
✅ 6 tests desbloqueados

**Tiempo:** 6 horas

---

## 📚 DOCUMENTACIÓN COMPLETA

### 1. 📄 [REFACTOR_SUMMARY.md](REFACTOR_SUMMARY.md)
**Audiencia:** Product Owner, Arquitectos, Lead Developers  
**Tiempo de lectura:** 10 minutos

**Contenido:**
- ✅ Problema vs Solución (60 segundos)
- ✅ ANTES vs DESPUÉS (diagramas visuales)
- ✅ Transformación por campo (6 campos)
- ✅ Impacto en archivos (16 archivos)
- ✅ Plan de implementación (6 horas)
- ✅ Beneficios (métricas antes/después)

**Lee este documento PRIMERO** para entender el refactor completo en 10 minutos.

---

### 2. 📊 [COSTOS_OPERATIVOS_OWNERSHIP_MAP.md](COSTOS_OPERATIVOS_OWNERSHIP_MAP.md)
**Audiencia:** Arquitectos, Desarrolladores  
**Tiempo de lectura:** 5 minutos

**Contenido:**
- ✅ Tabla maestra de reclasificación
- ✅ Flujo ANTES vs DESPUÉS
- ✅ Mapa de ownership definitivo
- ✅ Plan de implementación (timeline)
- ✅ Archivos a modificar (resumen ejecutivo)

**Documento visual** con tablas claras para referencia rápida.

---

### 3. 💻 [COSTOS_OPERATIVOS_CODE_EXAMPLES.md](COSTOS_OPERATIVOS_CODE_EXAMPLES.md)
**Audiencia:** Desarrolladores implementando el refactor  
**Tiempo de lectura:** 30 minutos (referencia durante implementación)

**Contenido:**
- ✅ Crear `domain/constants.py` (código completo)
- ✅ Agregar DTOs (antes/después)
- ✅ Métodos de cálculo (`_calcular_opex_ti_total`, etc.)
- ✅ Parametrización IPC (nuevo método)
- ✅ Adapters (mapeo input)
- ✅ Reemplazar constante en 5 ubicaciones
- ✅ Eliminar código legacy

**Código listo para copiar/pegar** con explicaciones detalladas.

---

### 4. 🏗️ [ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md](ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md)
**Audiencia:** Arquitectos, Tech Leads  
**Tiempo de lectura:** 60 minutos (documento técnico completo)

**Contenido:**
- ✅ Análisis de dependencias actuales
- ✅ Arquitectura objetivo (capas)
- ✅ Plan de implementación detallado (7 fases)
- ✅ Lista completa de archivos (16 archivos)
- ✅ Criterios de aceptación
- ✅ Riesgos y mitigaciones
- ✅ Rollback plan

**Documento maestro** con diseño arquitectónico completo.

---

### 5. 📝 [REFACTOR_COSTOS_OPERATIVOS.md](REFACTOR_COSTOS_OPERATIVOS.md) (DRAFT)
**Audiencia:** Referencia histórica  
**Estado:** DRAFT (obsoleto, reemplazado por documentos 1-4)

Este documento fue el borrador inicial. **NO usar** — los documentos 1-4 son la versión final.

---

## 🚀 GUÍA DE INICIO RÁPIDO

### Para Product Owner / Arquitecto
1. Lee **[REFACTOR_SUMMARY.md](REFACTOR_SUMMARY.md)** (10 min)
2. Aprueba el diseño si estás de acuerdo
3. Asigna 6 horas de desarrollo

### Para Lead Developer
1. Lee **[REFACTOR_SUMMARY.md](REFACTOR_SUMMARY.md)** (10 min)
2. Revisa **[COSTOS_OPERATIVOS_OWNERSHIP_MAP.md](COSTOS_OPERATIVOS_OWNERSHIP_MAP.md)** (5 min)
3. Asigna desarrollador(es)

### Para Desarrollador Implementando
1. Lee **[REFACTOR_SUMMARY.md](REFACTOR_SUMMARY.md)** (10 min)
2. Abre **[COSTOS_OPERATIVOS_CODE_EXAMPLES.md](COSTOS_OPERATIVOS_CODE_EXAMPLES.md)** (referencia durante implementación)
3. Sigue FASE 1-7 del plan (6 horas)
4. Ejecuta tests de certificación

### Para QA Lead
1. Lee **[REFACTOR_SUMMARY.md](REFACTOR_SUMMARY.md)** (10 min)
2. Revisa **Criterios de Aceptación** en **[ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md](ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md)**
3. Prepara plan de testing

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### FASE 1: Preparación (30 min)
- [ ] Crear `domain/constants.py`
- [ ] Agregar `tarifa_diaria_capacitacion` a DTOs (3 archivos)
- [ ] Crear tests unitarios vacíos

### FASE 2: Cálculos Derivados (2 horas)
- [ ] Implementar `_calcular_opex_ti_total()`
- [ ] Implementar `_calcular_capex_recurrente()`
- [ ] Implementar `_calcular_capex_inicial()`
- [ ] Integrar en `_construir_no_payroll()`

### FASE 3: Parametrización IPC (1 hora)
- [ ] Agregar `get_economic_component()` a `FinancialParametrizationRepository`
- [ ] Agregar facade `get_componente_indexacion()` a `ParametrizationProvider`
- [ ] Usar en `_construir_cadena_c()`

### FASE 4: Adapters (30 min)
- [ ] Mapear `tarifaCap` en `UnifiedInputAdapter`
- [ ] Actualizar `JsonCaseLoader` (legacy)

### FASE 5: Constantes (15 min)
- [ ] Reemplazar en línea ~287 (`_construir_panel`)
- [ ] Reemplazar en línea ~424 (`_construir_perfiles_soporte`)
- [ ] Reemplazar en línea ~644 (`_construir_parametros_nomina`)
- [ ] Reemplazar en línea ~792 (`_construir_cadena_b`)
- [ ] Reemplazar en línea ~860 (`_construir_cadena_c`)

### FASE 6: Eliminar Legacy (30 min)
- [ ] Eliminar `get_costo_operativo()` en `PayrollParametrizationRepository`
- [ ] Eliminar facade en `ParametrizationProvider`
- [ ] Actualizar `ParametrizationCompletenessValidator`

### FASE 7: Tests (1.5 horas)
- [ ] Implementar tests unitarios nuevos
- [ ] Actualizar fixtures (eliminar `costos_operativos`)
- [ ] Ejecutar suite completa
- [ ] Ejecutar certificación (L1, L2, L3)

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Funcional
- [ ] Motor ejecuta sin `ParametrizationError`
- [ ] `tarifa_dia_cap` desde `panel.tarifa_diaria_capacitacion`
- [ ] OPEX TI calculado desde `opex_fijo[]`
- [ ] CAPEX calculado desde `inversiones[]`
- [ ] IPC desde `OP-Componente`
- [ ] Constante `MES_INICIO_AJUSTE_ANUAL = 1`

### Arquitectónico
- [ ] Single source of truth por campo
- [ ] Separación: INPUT | PARAMETRIZATION | DERIVED | CONSTANT
- [ ] Cero hardcodes en parametrización
- [ ] Trazabilidad completa

### Tests
- [ ] 100% certificación pasa
- [ ] Nuevos tests unitarios
- [ ] Fixtures actualizados

---

## 📊 MÉTRICAS DE ÉXITO

| Métrica | Antes | Después | Meta |
|---------|-------|---------|------|
| Tests bloqueados | 6 | 0 | ✅ 0 |
| Fuentes por campo | 1-4 | 1 | ✅ 1 |
| Hardcodes | 6 | 0 | ✅ 0 |
| Trazabilidad | 0% | 100% | ✅ 100% |
| Archivos modificados | - | 16 | ✅ <20 |
| Tiempo implementación | - | 6h | ✅ <8h |

---

## 🆘 SOPORTE

### Preguntas Frecuentes

**P: ¿Por qué no crear `HR-costos_operativos` en lugar de eliminarlo?**  
**R:** Porque cada campo en `costos_operativos` NO pertenece a HR según su naturaleza funcional. Crear la sección sería perpetuar la arquitectura incorrecta.

**P: ¿Qué pasa si el usuario NO envía `tarifa_diaria_capacitacion`?**  
**R:** El motor falla con error explícito en validación early (antes de ejecutar cálculos). Esto es correcto — es un campo REQUERIDO del input.

**P: ¿Cómo manejo backwards compatibility con JSONs legacy?**  
**R:** Los JSONs legacy deben actualizarse para incluir `tarifa_diaria_capacitacion`. Si es imposible, agregar un adapter temporal que mapee desde donde esté el valor actualmente.

**P: ¿Qué pasa si OP-Componente no tiene el IPC del año solicitado?**  
**R:** El motor lanza `ParametrizationError` con mensaje claro: "Agregar año X a Excel OP → sheet Componente". Esto es correcto — el usuario debe actualizar parametrización.

**P: ¿Por qué calcular OPEX/CAPEX en cada simulación en lugar de cachear?**  
**R:** Porque el cálculo es O(n) lineal y trivial (<1ms). Cachear agregaría complejidad innecesaria. Si en futuro es bottleneck, se puede optimizar.

### Contacto

**Arquitecto Backend:** darwin.minota.quinto@accenture.com  
**Branch:** `refactor/engine-v2`  
**Issue Tracker:** (agregar URL si existe)

---

## 📅 CHANGELOG

### 2026-05-27 - v2.0 (ACTUAL)
- ✅ Documentación completa (4 documentos)
- ✅ Plan de implementación detallado
- ✅ Código de ejemplo listo
- ✅ READY FOR IMPLEMENTATION

### 2026-05-27 - v1.0 (DRAFT)
- 📝 Borrador inicial (`REFACTOR_COSTOS_OPERATIVOS.md`)
- 📝 Análisis preliminar

---

## 📜 LICENCIA Y APROBACIÓN

Este refactor fue diseñado por el equipo de Arquitectura Backend NEXA y requiere aprobación formal antes de implementación.

**Aprobadores requeridos:**
- [ ] Product Owner / Arquitecto Backend
- [ ] Lead Developer
- [ ] QA Lead

**Firma de aprobación:**
```
Aprobado por: _______________________
Fecha: _______________________
Cargo: _______________________
```

---

**FIN DEL ÍNDICE MAESTRO**

---

## 🔗 NAVEGACIÓN RÁPIDA

- [← Volver a Documentación Principal](../README.md)
- [📄 Resumen Ejecutivo](REFACTOR_SUMMARY.md)
- [📊 Mapa de Ownership](COSTOS_OPERATIVOS_OWNERSHIP_MAP.md)
- [💻 Ejemplos de Código](COSTOS_OPERATIVOS_CODE_EXAMPLES.md)
- [🏗️ Arquitectura Completa](ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md)
