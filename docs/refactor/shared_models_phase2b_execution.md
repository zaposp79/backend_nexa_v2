# SHARED_MODELS_PHASE2B — EXECUTION REPORT

**Status:** COMPLETADO  
**Veredicto:** `PHASE_2B_COMPLETED`  
**Fecha:** 2026-06-10  
**Rama:** `refactor/modular-pure`  
**Riesgo ejecutado:** BAJO

---

## 1. Resumen ejecutivo

Se migraron exitosamente los 8 DTOs puros de CTS y PyG desde `modules/shared/models/` a sus módulos propietarios. `visions.py` fue convertido en adapter temporal de compatibilidad. No hubo regresiones en tests ni cambios funcionales.

---

## 2. DTOs migrados

### visions_cts.py → `modules/vision_cost_to_serve/dto/models.py`

| Clase | Campos | @property | Cambios |
|---|---|---|---|
| `DesgloseCTSCadenaA` | 13 | `total()` | Ninguno — contenido idéntico |
| `DesgloseCTSCadenaB` | 9 | `total()` | Ninguno — contenido idéntico |
| `CanalCTSDetalle` | 18 | 0 | Ninguno — contenido idéntico |
| `ResultadoCostToServe` | 15 | 0 | Ninguno — contenido idéntico |

### visions_pyg.py → `modules/pyg/dto/models.py`

| Clase | Campos | @property | Cambios |
|---|---|---|---|
| `VisionPyGRow` | 10 | 0 | Ninguno — contenido idéntico |
| `VisionPyGRowDetalle` | 11 | 0 | Ninguno — contenido idéntico |
| `ResumenEjecutivoPyG` | 19 | 0 | Ninguno — contenido idéntico |
| `VisionPyG` | 7 | 0 | Ninguno — contenido idéntico |

---

## 3. Nuevas ubicaciones

```
modules/vision_cost_to_serve/dto/
  __init__.py   ← re-exporta los 4 modelos CTS
  models.py     ← contenido de visions_cts.py (idéntico)

modules/pyg/dto/
  __init__.py   ← re-exporta los 4 modelos PyG
  models.py     ← contenido de visions_pyg.py (idéntico)
```

Verificado con:
```python
from nexa_engine.modules.vision_cost_to_serve.dto.models import ResultadoCostToServe
from nexa_engine.modules.pyg.dto.models import VisionPyG
# Adapter check: CTS_via_adapter is ResultadoCostToServe → True
# Adapter check: PyG_via_adapter is VisionPyG → True
```

---

## 4. Cambios en `visions.py`

`modules/shared/models/visions.py` fue actualizado para re-exportar los modelos migrados desde sus nuevas ubicaciones canónicas. Actúa como **adapter temporal de compatibilidad**.

**Antes:**
```python
from nexa_engine.modules.shared.models.visions_cts import (
    DesgloseCTSCadenaA, DesgloseCTSCadenaB, CanalCTSDetalle, ResultadoCostToServe,
)
from nexa_engine.modules.shared.models.visions_pyg import (
    VisionPyGRow, VisionPyGRowDetalle, ResumenEjecutivoPyG, VisionPyG,
)
```

**Después:**
```python
from nexa_engine.modules.vision_cost_to_serve.dto.models import (
    DesgloseCTSCadenaA, DesgloseCTSCadenaB, CanalCTSDetalle, ResultadoCostToServe,
)
from nexa_engine.modules.pyg.dto.models import (
    VisionPyGRow, VisionPyGRowDetalle, ResumenEjecutivoPyG, VisionPyG,
)
```

Los archivos fuente `visions_cts.py` y `visions_pyg.py` permanecen en `shared/models/` sin cambios — los consumidores que los usen directamente seguirán funcionando. Sin embargo, **ya no son la fuente canónica** — la fuente canónica son los nuevos módulos.

---

## 5. Cambios en `results.py`

**Ninguno.** Las forward references en `PricingResult` usan el patrón `Optional["ResultadoCostToServe"]` con `# type: ignore[name-defined]` y `from __future__ import annotations`. Este mecanismo no resuelve en runtime — son strings literales evaluados lazily. No requieren actualización para que la migración funcione.

Los forward refs se pueden actualizar a imports reales en una fase posterior cuando `results.py` sea redistribuido a su módulo propietario.

---

## 6. Consumidores validados

| Consumidor | Verificación | Estado |
|---|---|---|
| `vision_cost_to_serve/services/cost_to_serve_calculator.py` | Import directo OK | ✅ |
| `pyg/builders/vision_pyg_builder.py` | Import directo OK | ✅ |
| `calculator_motor/serializers/pricing_result_serializer.py` | Módulo importa OK | ✅ |
| `shared/models/visions.py` (adapter) | Mismo objeto verificado (`is True`) | ✅ |
| `shared/models/__init__.py` (wildcard) | Hereda del adapter — no cambió | ✅ |

Búsqueda confirmada — **0 imports directos** a `visions_cts.py` o `visions_pyg.py` fuera del adapter:
```bash
grep -r "shared\.models\.visions_cts\|shared\.models\.visions_pyg" modules/ --include="*.py"
# → sin resultados (fuera de visions.py)
```

---

## 7. Riesgos detectados

| Riesgo | Severidad | Estado |
|---|---|---|
| Forward refs en `results.py` | BAJO | No aplicó — mecanismo de string lazy es válido |
| Adapter `is` check fallido | BAJO | Confirmado: `CTS_via_adapter is ResultadoCostToServe → True` |
| Archivos fuente `visions_cts/pyg.py` aún en shared | BAJO | Intencional — se eliminan en fase posterior cuando todos los consumidores sean migrados |
| `__pycache__` de módulos viejos | NINGUNO | Python reconstruye automáticamente |

---

## 8. Validaciones ejecutadas

### Pre-migración (baseline)
```
2125 passed, 94 failed, 73 skipped, 17 errors — baseline estable
```

### Post-migración
```
2125 passed, 94 failed, 73 skipped, 17 errors — IDÉNTICO
```

**Resultado: 0 regresiones.**

### Verificaciones estructurales
```bash
# Sin imports directos a archivos fuente viejos fuera del adapter
grep -r "shared\.models\.visions_cts\|shared\.models\.visions_pyg" modules/ → sin resultados

# Adapter es el mismo objeto
CTS_via_adapter is ResultadoCostToServe → True
PyG_via_adapter is VisionPyG → True
```

---

## 9. Resultado final

| Criterio | Estado |
|---|---|
| DTOs CTS migrados a `vision_cost_to_serve/dto/models.py` | ✅ |
| DTOs PyG migrados a `pyg/dto/models.py` | ✅ |
| `visions.py` preservado como adapter temporal | ✅ |
| `results.py` no modificado (forward refs intactos) | ✅ |
| `panel.py` no tocado | ✅ |
| Consumidores no rotos | ✅ |
| 0 regresiones en tests | ✅ |
| Paridad funcional intacta | ✅ |
| Sin imports directos a archivos fuente viejos (fuera del adapter) | ✅ |

---

## 10. Próximo paso recomendado

1. **No mover `panel.py` todavía** — tiene 26 consumidores con ~210 imports distribuidos. Requiere pre-auditoría completa propia.
2. **Fase 2C — Migrar `visions_tarifas.py` y `visions_imprimible.py`** — misma estrategia: crear `modules/vision_tarifas/dto/models.py` y `modules/vision_imprimible/dto/models.py`, actualizar adapter en `visions.py`.
3. **Eliminar `visions_cts.py` y `visions_pyg.py` de `shared/models/`** — solo después de confirmar que ningún consumidor los referencia directamente (actualmente 0 fuera del adapter).
4. **Pre-auditoría de `results.py`** — clasificar las 9 clases antes de planificar Fase 3 (migración de outputs del pipeline).
