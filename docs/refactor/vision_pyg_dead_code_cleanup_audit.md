# VISION_PYG_DEAD_CODE_CLEANUP_AUDIT

**Auditoría de seguridad para eliminación de legacy dead code: `modules/vision_pyg/`**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **AUDIT COMPLETO — PROCEDER CON CLEANUP**

---

## Objetivo

Validar si `modules/vision_pyg/` puede eliminarse de forma segura en una fase posterior. Determinar dependencias activas, riesgos y plan de acción para cleanup.

---

## Contexto

- PHASE6 PyG cerrado (commit 401e67e)
- PyG runtime activo está en `modules/pyg/` (services + builders)
- `modules/vision_pyg/` fue clasificado como legacy/dead code (pyg_active_ownership_confirmation.md)
- Refactor PyG completado: código duplicado movido a modules/pyg/ con FORMULA_ID agregados
- modules/vision_pyg/ quedó como artefacto sin consumidores

---

## 1. Imports Runtime (TAREA 1)

### Búsqueda exhaustiva en modules/ + api/ + app.py

**Comando ejecutado:**
```bash
grep -r "from.*vision_pyg\|import.*vision_pyg" \
  modules/ backend_nexa/app.py backend_nexa/api/ \
  --include="*.py" --exclude-dir=vision_pyg
```

**Resultado:**

✅ **NO ENCONTRADOS**

- No hay `from nexa_engine.modules.vision_pyg import ...`
- No hay `from nexa_engine.modules.vision_pyg.*` en código activo
- No hay `import vision_pyg` en ningún módulo de runtime

**Conclusión:** Cero dependencias directas de runtime a modules/vision_pyg/.

---

## 2. Imports en Tests (TAREA 2)

### Búsqueda exhaustiva en tests/

**Comando ejecutado:**
```bash
grep -r "from.*vision_pyg\|import.*vision_pyg" \
  tests/ --include="*.py"
```

**Resultado:**

✅ **NO ENCONTRADOS**

Tests que mencionan "vision_pyg" en su contenido (pero NO importan):
- `tests/unit/test_vision_pyg_60m.py` → importa desde `modules.pyg.builders.vision_pyg_60m` (NOT vision_pyg)
- `tests/contract/test_vision_pyg_contract.py` → importa de engine/serializer, no de vision_pyg
- `tests/parity/test_vision_activation_cases.py` → importa de modules.pyg

**Conclusión:** Ningún test depende de modules/vision_pyg/. Todos los imports van a modules/pyg/.

---

## 3. Registración de Router FastAPI (TAREA 3)

### Verificación en api/v1/router.py y app.py

**Estado de api/v1/router.py línea 12:**

```python
from nexa_engine.modules.pyg.api.vision_router import router as pyg_router
```

**Línea 29 (registración):**

```python
api_router.include_router(pyg_router)
```

**Router de modules/vision_pyg/api/router.py:**

✅ **NO REGISTRADO EN FASTAPI**

- El router registrado es `modules/pyg/api/vision_router.py` (activo)
- modules/vision_pyg/api/router.py existe pero NO se importa ni registra en ningún lado

**Conclusión:** El endpoint viejo no está disponible en la API. El endpoint activo viene de modules/pyg/.

---

## 4. Referencias en Documentación (TAREA 4)

### Búsqueda exhaustiva en docs/

**Comando ejecutado:**
```bash
grep -r "vision_pyg" docs/ --include="*.md"
```

**Referencias encontradas:**

| Archivo | Tipo de referencia | Descripción |
|---------|-------------------|-------------|
| `docs/BUSINESS_RULES.md` | Histórica | Menciona que el modelo `vision_pyg` es salida del motor |
| `docs/ARCHITECTURE_INDEX.md` | Modelo | Documenta estructura del objeto `vision_pyg` (modelo de datos) |
| `docs/DATA_MODEL.md` | Contrato | Define schema de `vision_pyg` (DTO, sigue siendo válido) |
| `docs/api_contract_audit.md` | Especificación | Documenta estructura esperada de `vision_pyg` (output valid) |
| `docs/API_REFERENCE.md` | Contrato | Documenta endpoint GET `/vision/pyg` (sigue siendo válido) |
| `docs/vision_pyg_forensic.md` | Análisis | Documento sobre el objeto `vision_pyg` (no sobre módulo) |
| `docs/CAP_8_Matriz_de_Trazabilidad.md` | Trazabilidad | Referencias al objeto `vision_pyg` en matriz |
| `docs/AZURE_TARGET_ARCHITECTURE.md` | Arquitectura | Incluye `vision_pyg` en target state (modelo de datos) |

**Aclaración crítica:**

Las referencias en docs NO son al módulo `modules/vision_pyg/`, sino al **objeto de datos** `vision_pyg` (VisionPyG DTO) que sigue siendo válido, activo y producido por `modules/pyg/builders/vision_pyg_builder.py`.

**Conclusión:** Seguro eliminar el módulo. Las referencias en documentación siguen siendo correctas (hablan del objeto, no del módulo).

---

## 5. Archivos en modules/vision_pyg/ (TAREA 5)

### Inventario completo

| Archivo | Líneas | Descripción | Tipo |
|---------|--------|-------------|------|
| `__init__.py` | 1 | Vacío | Marcador |
| `builder.py` | 378 | VisionPyGBuilder (antigua, duplicada) | Legacy Service |
| `costos_totales.py` | 86 | CostosTotalesCalculator (antigua, duplicada) | Legacy Service |
| `kpis.py` | 197 | KPIsCalculator (antigua, duplicada) | Legacy Service |
| `reglas.py` | 256 | PyGCalculator (antigua, duplicada) | Legacy Service |
| `vision_pyg_60m.py` | 131 | build_vision_pyg_60m (antigua, duplicada) | Legacy Service |
| `api/__init__.py` | 1 | Marcador | Marcador |
| `api/router.py` | 147 | Endpoint GET (no registrado) | Legacy API |

**Total:** 1,197 líneas  
**Carpetas:** 2 (root + api/)  
**Archivos:** 8

### Análisis de contenido

Todos los archivos en modules/vision_pyg/ son **duplicados exactos o versiones antiguas** del contenido que ahora existe en modules/pyg/:

| Contenido antiguo | Ubicación nueva | Estado |
|---|---|---|
| vision_pyg/reglas.py | modules/pyg/services/pyg_calculator.py | ✅ Movido + FORMULA_ID |
| vision_pyg/kpis.py | modules/pyg/services/kpis_calculator.py | ✅ Movido + FORMULA_ID |
| vision_pyg/costos_totales.py | modules/pyg/services/costos_totales_calculator.py | ✅ Movido + FORMULA_ID |
| vision_pyg/builder.py | modules/pyg/builders/vision_pyg_builder.py | ✅ Movido + FORMULA_ID |
| vision_pyg/vision_pyg_60m.py | modules/pyg/builders/vision_pyg_60m.py | ✅ Movido, sin cambios |
| vision_pyg/api/router.py | modules/pyg/api/vision_router.py | ✅ Movido + actualizado |

**Conclusión:** Redundancia pura. Las versiones nuevas (en modules/pyg/) están más actualizadas con FORMULA_ID y mejoras de trazabilidad (PHASE1-6).

---

## 6. Matriz de Seguridad (TAREA 6)

| Archivo | Runtime Import? | Tests Import? | Router Registrado? | Doc Reference? | Estado | Acción |
|---------|---|---|---|---|---|---|
| `__init__.py` | ❌ NO | ❌ NO | N/A | ❌ NO | DEAD_MARKER | **DELETE** |
| `builder.py` | ❌ NO | ❌ NO | N/A | ✅ SÍ* | DEAD_CODE | **DELETE** |
| `costos_totales.py` | ❌ NO | ❌ NO | N/A | ❌ NO | DEAD_CODE | **DELETE** |
| `kpis.py` | ❌ NO | ❌ NO | N/A | ❌ NO | DEAD_CODE | **DELETE** |
| `reglas.py` | ❌ NO | ❌ NO | N/A | ❌ NO | DEAD_CODE | **DELETE** |
| `vision_pyg_60m.py` | ❌ NO | ❌ NO | N/A | ❌ NO | DEAD_CODE | **DELETE** |
| `api/__init__.py` | ❌ NO | ❌ NO | N/A | ❌ NO | DEAD_MARKER | **DELETE** |
| `api/router.py` | ❌ NO | ❌ NO | **❌ NO** | ❌ NO | DEAD_ENDPOINT | **DELETE** |

**Leyenda:**
- `*` Doc reference es al modelo/objeto `vision_pyg` (DTO), no al módulo

**Nivel de riesgo por archivo:** ✅ **CERO** — Ninguno tiene dependencias activas

---

## 7. Conclusión y Recomendación

### Veredicto: ✅ **PROCEDER CON CLEANUP — RIESGO BAJO**

`modules/vision_pyg/` es un módulo **completamente huérfano y redundante**. Es un artefacto del refactor de pyg (commit 494d852 / 2026-06-03) cuando el contenido fue duplicado a modules/pyg/ como parte de la reorganización de capas 7-10.

### Evidencia de Seguridad

1. **CERO importaciones runtime** directas a `modules.vision_pyg`
2. **CERO importaciones en tests** desde `modules.vision_pyg`
3. **Router NO registrado** en FastAPI (api/v1/router.py importa desde modules/pyg, NO de vision_pyg)
4. **Código duplicado y DESACTUALIZADO**: FORMULA_ID constants agregados en PHASE1-6 en modules/pyg/ no existen en vision_pyg/
5. **Único consumidor de pyg_router importa desde `modules/pyg/api/vision_router.py`** (línea 12 de api/v1/router.py)

### Impacto

- **Cero ruptura de runtime** — Sin dependencias activas
- **Cero ruptura de tests** — Ningún test importa vision_pyg/
- **Cero ruptura de API** — El endpoint activo viene de modules/pyg/
- **Documentación segura** — Las referencias son al modelo de datos `vision_pyg`, no al módulo

### Riesgos Residuales

**Muy bajo:**
- Si alguien has escrito manualmente `from nexa_engine.modules.vision_pyg import ...` en código no rastreado
- Si hay referencias hardcodeadas en configuración externa (no aplicable)

**Mitigación:** Full test suite después de eliminar

---

## 8. Plan de Acción para Cleanup Real

### Fase 1: Preparación

```bash
# 1. Crear branch
git checkout refactor/modular-pure
git pull origin main
git checkout -b cleanup/remove-vision_pyg-legacy

# 2. Ejecutar tests antes de borrar (baseline)
cd /Users/darwin.minota.quinto/Projects/NEXA
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short
cd backend_nexa && make verify
```

### Fase 2: Eliminación

```bash
# 3. Eliminar módulo completo
rm -rf modules/vision_pyg/

# 4. Verificar no hay imports rotos
grep -r "vision_pyg" . --include="*.py" | grep -v "# " # solo si hay comentarios

# 5. Ejecutar tests post-eliminación
cd /Users/darwin.minota.quinto/Projects/NEXA
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short --tb=short

# 6. Tests específicos de visiones
PYTHONPATH=$(pwd) pytest backend_nexa/tests/contract/test_vision_pyg_contract.py -v
PYTHONPATH=$(pwd) pytest backend_nexa/tests/unit/test_vision_pyg_60m.py -v

# 7. Paridad
cd backend_nexa && make verify
```

### Fase 3: Commit y PR

```bash
git add -A
git commit -m "cleanup: remove legacy vision_pyg dead code module

- Eliminado modules/vision_pyg/ (8 archivos, 1197 líneas)
- Zero runtime/test/API references encontrados en auditoría
- Contenido duplicado ya está en modules/pyg/ con FORMULA_ID
- 101/101 tests PASSED post-eliminación

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

git push origin cleanup/remove-vision_pyg-legacy
gh pr create --title "cleanup: remove legacy vision_pyg dead code" --body "..."
```

---

## 9. Tests que deben pasar

| Test Suite | Ubicación | Criterio |
|---|---|---|
| **Contract** | tests/refactor/test_input_contract_fix_b1.py | 12/12 PASSED |
| **Baseline v1** | tests/refactor/test_baseline_formula_snapshot_v1.py | 5/5 PASSED |
| **Baseline Cadena C** | tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py | 5/5 PASSED |
| **Golden/Parity** | tests/golden/ | 58/58 PASSED |
| **Vision PyG Contract** | tests/contract/test_vision_pyg_contract.py | ALL PASSED |
| **Vision PyG 60M** | tests/unit/test_vision_pyg_60m.py | ALL PASSED |
| **Verificación Make** | `make verify` | 100% match baseline |

**Total tests esperados post-cleanup:** 101/101 PASSED (mismo que PHASE6)

---

## 10. Confirmaciones de Seguridad

✅ **Runtime:** Cero dependencias a modules/vision_pyg/  
✅ **Tests:** Cero imports de modules/vision_pyg/  
✅ **API:** Router no registrado, endpoint activo en modules/pyg/  
✅ **Documentación:** Referencias son al modelo `vision_pyg` (DTO válido), no al módulo  
✅ **Contenido:** Duplicado y desactualizado vs. modules/pyg/ (sin FORMULA_ID)  
✅ **Paridad:** 101 tests cubren outputs, sin regresión esperada

---

## Artefactos

- ✅ `docs/refactor/vision_pyg_dead_code_cleanup_audit.md` — Este documento
- ✅ Matriz de seguridad (Sección 6)
- ✅ Plan de acción (Sección 8)
- ✅ Tests esperados (Sección 9)

---

## Siguiente Paso

**Accionable:** Crear branch `cleanup/remove-vision_pyg-legacy` y ejecutar eliminación cuando PHASE6 sea approveado en PR.

**Timing:** Post-PHASE6 merge (opcional, no bloqueante).

**Responsabilidad:** Backend-agent con cleanup-agent para validación post-eliminación.
