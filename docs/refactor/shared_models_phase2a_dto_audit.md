# SHARED_MODELS_PHASE2A — DTO AUDIT: visions_cts + visions_pyg

**Status:** AUDITORÍA COMPLETA  
**Veredicto:** `PHASE_2A_READY_TO_MIGRATE`  
**Fecha:** 2026-06-10  
**Rama:** `refactor/modular-pure`  
**Worker:** scanner-agent (read-only) + architecture-agent (documento)  
**Riesgo:** BAJO

---

## 1. Resumen ejecutivo

`visions_cts.py` y `visions_pyg.py` contienen **8 clases puras sin lógica de negocio**. Todos los modelos son `@dataclass(slots=True)` con campos tipados y sin dependencias externas (solo `from __future__ import annotations` y `from dataclasses import dataclass, field`).

Las dos únicas propiedades encontradas (`DesgloseCTSCadenaA.total`, `DesgloseCTSCadenaB.total`) son sumatorias simples (`return self.a + self.b`) — no califican como lógica de negocio.

**No hay bloqueadores.** Ambos archivos son candidatos seguros para migración en la siguiente fase.

---

## 2. Archivos auditados

| Archivo | Líneas | Clases | Imports externos | Estado |
|---|---|---|---|---|
| `modules/shared/models/visions_cts.py` | 104 | 4 | Ninguno | ✅ Auditado |
| `modules/shared/models/visions_pyg.py` | 83 | 4 | Ninguno | ✅ Auditado |

---

## 3. Inventario de clases

### visions_cts.py

| Clase | Base | Campos | Métodos | @property | Validators | Imports internos | Imports externos |
|---|---|---|---|---|---|---|---|
| `DesgloseCTSCadenaA` | `@dataclass(slots=True)` | 13 (`nomina`, `no_payroll`, `nomina_loaded`, `salario_fijo`, `salario_variable`, `capacitacion_inicial`, `capacitacion_rotacion`, `examenes`, `estudios_seguridad`, `crucero`, `opex_fijo`, `inversiones`, `costos_fijos_estacion`) | 0 | `total()` → `self.nomina + self.no_payroll` | 0 | Ninguno | Ninguno |
| `DesgloseCTSCadenaB` | `@dataclass(slots=True)` | 9 (`componente_fijo`, `opex`, `inversiones`, `soporte_mantenimiento`, `componente_variable`, `tarifa`, `opex_variable`, `tasa_escalamiento`, `hitl`) | 0 | `total()` → `self.componente_fijo + self.componente_variable` | 0 | Ninguno | Ninguno |
| `CanalCTSDetalle` | `@dataclass(slots=True)` | 18 (`canal`, `modalidad`, `fte`, `participacion_cadena_a`, `cts`, `payroll`, `nomina_loaded`, `salario_fijo`, `salario_variable`, `capacitacion_inicial`, `capacitacion_rotacion`, `examenes`, `estudios_seguridad`, `crucero`, `no_payroll`, `opex_fijo`, `inversiones`, `costos_fijos`) | 0 | 0 | 0 | Ninguno | Ninguno |
| `ResultadoCostToServe` | `@dataclass(slots=True)` | 15 (`cts_cadena_a/b/c`, `cts_ponderado`, `participacion_a/b/c`, `fte_cadena_a`, `vol_cadena_b/c`, `costo_total_acumulado`, `desglose_a: DesgloseCTSCadenaA`, `desglose_b: DesgloseCTSCadenaB`, `canal_view_habilitado`, `canales_detalle: list[CanalCTSDetalle]`) | 0 | 0 | 0 | Ninguno | Ninguno |

### visions_pyg.py

| Clase | Base | Campos | Métodos | @property | Validators | Imports internos | Imports externos |
|---|---|---|---|---|---|---|---|
| `VisionPyGRow` | `@dataclass(slots=True)` | 10 (`key`, `label`, `seccion`, `tipo`, `signo`, `valores: list[float]`, `acumulado`, `promedio`, `excel_row`, `formula`) | 0 | 0 | 0 | Ninguno | Ninguno |
| `VisionPyGRowDetalle` | `@dataclass(slots=True)` | 11 (`key`, `label`, `parent`, `seccion`, `tipo`, `signo`, `valores: list[float]`, `acumulado`, `promedio`, `excel_row`, `formula`) | 0 | 0 | 0 | Ninguno | Ninguno |
| `ResumenEjecutivoPyG` | `@dataclass(slots=True)` | 19 (`meses_contrato`, `meses_activos`, `valor_total_deal`, `ingreso_neto_total`, `costo_total_contrato`, `contribucion_total`, `pct_utilidad_promedio`, `cumple_margen_minimo`, `cliente`, `tipo_cliente`, `antiguedad_cliente`, `linea_negocio`, `ciudad`, `sede`, `fecha_inicio`, `fecha_fin`, `duracion_contrato`, `periodo_pago_dias`, `divisa`) | 0 | 0 | 0 | Ninguno | Ninguno |
| `VisionPyG` | `@dataclass(slots=True)` | 7 (`resumen: ResumenEjecutivoPyG`, `filas: list[VisionPyGRow]`, `meses_contrato`, `meses_activos`, `filas_detalle: list[VisionPyGRowDetalle]`, `puestos_trabajo`, `fechas_meses: list[str]`) | 0 | 0 | 0 | Ninguno | Ninguno |

---

## 4. Validación DTO puro

### Criterios aplicados

Un modelo es DTO puro si cumple los 10 criterios:

1. Solo define estructura de datos
2. No ejecuta cálculos
3. No tiene lógica de negocio
4. No tiene propiedades calculadas (excepto sumatorias triviales)
5. No tiene métodos compute/build/from/result complejos
6. No importa calculators, formulas, engines ni servicios
7. No depende de modelos de otros dominios de forma ambigua
8. No contiene defaults calculados con lógica de negocio
9. No orquesta transformaciones
10. No accede a Excel, storage, DB ni serializers

### Veredictos

| Clase | ¿DTO puro? | Evidencia | Observación |
|---|---|---|---|
| `DesgloseCTSCadenaA` | **SÍ** | 13 campos float, 1 @property `total()` = `self.nomina + self.no_payroll` | La sumatoria es presentación, no cálculo de negocio |
| `DesgloseCTSCadenaB` | **SÍ** | 9 campos float, 1 @property `total()` = `self.componente_fijo + self.componente_variable` | Igual que el anterior — suma de dos campos propios |
| `CanalCTSDetalle` | **SÍ** | 18 campos, 0 propiedades, 0 métodos, 0 imports externos | Contenedor puro |
| `ResultadoCostToServe` | **SÍ** | 15 campos, 0 propiedades, 0 métodos, 0 imports externos | Composición de DTOs anidados |
| `VisionPyGRow` | **SÍ** | 10 campos, 0 propiedades, 0 métodos, 0 imports externos | Contenedor puro |
| `VisionPyGRowDetalle` | **SÍ** | 11 campos, 0 propiedades, 0 métodos, 0 imports externos | Contenedor puro |
| `ResumenEjecutivoPyG` | **SÍ** | 19 campos, 0 propiedades, 0 métodos, 0 imports externos | Contenedor puro (metadatos del deal) |
| `VisionPyG` | **SÍ** | 7 campos, 0 propiedades, 0 métodos, 0 imports externos | Composición de DTOs anidados |

**Resultado: 8/8 clases son DTOs puros.**

---

## 5. Clasificación final

| Modelo | Clasificación final | Justificación | Riesgo de migración |
|---|---|---|---|
| `DesgloseCTSCadenaA` | `DTO_PRESENTACION` | Output de display de CTS para Cadena A; instanciado únicamente en `cost_to_serve_calculator.py` | BAJO |
| `DesgloseCTSCadenaB` | `DTO_PRESENTACION` | Output de display de CTS para Cadena B | BAJO |
| `CanalCTSDetalle` | `DTO_PRESENTACION` | Detalle por canal en la visión CTS | BAJO |
| `ResultadoCostToServe` | `DTO_PRESENTACION` | Raíz de la visión completa CTS; referenciada en `PricingResult.cost_to_serve` (forward ref) | BAJO |
| `VisionPyGRow` | `DTO_PRESENTACION` | Fila del estado de resultados; instanciada en `vision_pyg_builder.py` | BAJO |
| `VisionPyGRowDetalle` | `DTO_PRESENTACION` | Sub-fila del P&G | BAJO |
| `ResumenEjecutivoPyG` | `DTO_PRESENTACION` | Resumen ejecutivo del deal (metadatos + totales pre-calculados) | BAJO |
| `VisionPyG` | `DTO_PRESENTACION` | Raíz de la visión P&G; referenciada en `PricingResult.vision_pyg` (forward ref) | BAJO |

---

## 6. Impacto en imports

### Consumidores directos (15 archivos)

| Modelo | Consumidores directos | Tipo de import | Riesgo | Acción futura |
|---|---|---|---|---|
| `DesgloseCTSCadenaA/B` | `cost_to_serve_calculator.py`, `pricing_result_serializer.py`, `vision_imprimible_builder.py` | Via `visions.py` re-export | BAJO | Actualizar 3 imports al mover |
| `CanalCTSDetalle` | `cost_to_serve_calculator.py`, serializer | Via `visions.py` | BAJO | Actualizar 2 imports |
| `ResultadoCostToServe` | `cost_to_serve_calculator.py`, `results.py` (forward ref), `vision_imprimible_builder.py`, serializer | Via `visions.py` + forward ref en `results.py` | MEDIO | Actualizar forward ref en `PricingResult` |
| `VisionPyGRow/Detalle` | `vision_pyg_builder.py`, serializer | Via `visions.py` | BAJO | Actualizar 2 imports |
| `ResumenEjecutivoPyG` | `vision_pyg_builder.py`, serializer | Via `visions.py` | BAJO | Actualizar 2 imports |
| `VisionPyG` | `vision_pyg_builder.py`, `results.py` (forward ref), serializer | Via `visions.py` + forward ref en `results.py` | MEDIO | Actualizar forward ref en `PricingResult` |

### Puntos de acoplamiento notables

1. **`results.py:PricingResult`** — tiene dos forward references a modelos de este grupo:
   ```python
   cost_to_serve: Optional["ResultadoCostToServe"]
   vision_pyg: Optional["VisionPyG"]
   ```
   Al mover los modelos, estas referencias deben actualizarse o se deben mantener re-exports en `shared/models`.

2. **`modules/shared/contracts/api_v1/response/visions.py`** — contiene Pydantic V1 mirror models (`CostToServeDesgloseAV1`, etc.). Están **desacoplados** de los domain DTOs — no requieren cambios al migrar los dataclasses.

3. **Ningún consumidor importa directamente** `visions_cts` o `visions_pyg` — todos van a través del re-export hub `visions.py`.

---

## 7. Re-exports detectados

| Modelo | Re-export detectado | Archivo | Líneas | Riesgo | Recomendación |
|---|---|---|---|---|---|
| `DesgloseCTSCadenaA/B`, `CanalCTSDetalle`, `ResultadoCostToServe` | SÍ | `visions.py` (explícito, `# noqa: F401`) | 12-43 | BAJO | Mantener re-export durante transición |
| `VisionPyGRow/Detalle`, `ResumenEjecutivoPyG`, `VisionPyG` | SÍ | `visions.py` | 12-43 | BAJO | Mantener re-export durante transición |
| Todos | SÍ (wildcard) | `shared/models/__init__.py` | 9 | BAJO | Actualizar wildcard post-migración |

**Todos los consumidores externos usan `visions.py` como punto de entrada, no los módulos fuente directamente.** Esto es favorable para la migración: mover los archivos fuente y actualizar los imports en `visions.py` es suficiente para desacoplar sin tocar los 15 consumidores individualmente.

---

## 8. Decisión de migrabilidad

| Archivo | ¿Migrable? | Condición | Bloqueadores | Recomendación |
|---|---|---|---|---|
| `visions_cts.py` | **SÍ** | 4 clases puras, sin dependencias externas, 1 consumidor principal de instanciación | Ninguno | Mover a `modules/vision_cost_to_serve/dto/models.py` |
| `visions_pyg.py` | **SÍ** | 4 clases puras, sin dependencias externas, 1 constructor principal | Ninguno | Mover a `modules/pyg/dto/models.py` |

**Estrategia de migración segura (sin tocar consumidores individualmente):**

1. Crear `modules/vision_cost_to_serve/dto/models.py` con el contenido de `visions_cts.py`.
2. Crear `modules/pyg/dto/models.py` con el contenido de `visions_pyg.py`.
3. Actualizar `modules/shared/models/visions.py` para re-exportar desde las nuevas ubicaciones.
4. Actualizar forward references en `modules/shared/models/results.py` (2 líneas).
5. Actualizar los imports directos en `cost_to_serve_calculator.py` y `vision_pyg_builder.py` (owners naturales).
6. Añadir guardrails que confirmen que los modelos ya no están en `shared/models`.

---

## 9. Riesgos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Forward references en `PricingResult` (`results.py`) rotas al mover | MEDIO | Actualizar 2 líneas en `results.py` en la misma fase |
| Wildcard `from visions import *` en `__init__.py` deja de funcionar si se elimina `visions.py` | BAJO | Mantener `visions.py` como re-export hub hasta que todos los consumidores sean migrados |
| Tests de integración fallan si importan por path absoluto no actualizado | BAJO | `grep -r "shared.models.visions_cts\|shared.models.visions_pyg" tests/` antes de ejecutar |
| API contracts Pydantic V1 (`api_v1/response/visions.py`) se desacoplan del source | NINGUNO | Ya están desacoplados — mirror models independientes |
| Paridad Excel afectada | NINGUNO | DTOs son contenedores de presentación; la lógica está en calculators |

---

## 10. Recomendación para la siguiente fase

### Fase 2B — Migración efectiva

**Paso 1 — Ejecutar tests baseline antes de cualquier cambio:**
```bash
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short
# Esperado: 1249 pass / 57 fail
```

**Paso 2 — Crear módulos dto en los dueños naturales:**
```
modules/vision_cost_to_serve/dto/__init__.py
modules/vision_cost_to_serve/dto/models.py  ← copiar visions_cts.py
modules/pyg/dto/__init__.py
modules/pyg/dto/models.py                   ← copiar visions_pyg.py
```

**Paso 3 — Actualizar visions.py (re-export hub) para apuntar a nuevas ubicaciones:**
```python
# modules/shared/models/visions.py — actualizar 2 bloques de imports
from nexa_engine.modules.vision_cost_to_serve.dto.models import (
    DesgloseCTSCadenaA, DesgloseCTSCadenaB, CanalCTSDetalle, ResultadoCostToServe,
)
from nexa_engine.modules.pyg.dto.models import (
    VisionPyGRow, VisionPyGRowDetalle, ResumenEjecutivoPyG, VisionPyG,
)
```

**Paso 4 — Actualizar forward references en `results.py`** (2 líneas — cambiar path del string o import).

**Paso 5 — Actualizar imports directos en los owners naturales:**
- `vision_cost_to_serve/services/cost_to_serve_calculator.py` → importar desde `dto.models`
- `pyg/builders/vision_pyg_builder.py` → importar desde `dto.models`

**Paso 6 — Tests después:**
```bash
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short
make validate-excel  # paridad Excel
make verify          # snapshot congelado
```

**Paso 7 — Añadir guardrails estructurales** en `test_traceability_boundary_guardrails.py` o nuevo archivo de guardrails de modelos.

**Precaución:** NO eliminar `visions_cts.py` ni `visions_pyg.py` de `shared/models` hasta que todos los consumidores (15 archivos) sean migrados gradualmente. Mantener re-exports en `visions.py` durante la transición.

---

## Veredicto final

```
Veredicto: PHASE_2A_READY_TO_MIGRATE

Motivo:
visions_cts.py y visions_pyg.py contienen únicamente DTOs puros. Las 8 clases son
@dataclass(slots=True) con campos tipados, sin lógica de negocio, sin propiedades
calculadas complejas, sin imports de dominio externo. Los únicos dos @property
(DesgloseCTSCadenaA.total, DesgloseCTSCadenaB.total) son sumatorias triviales de
campos propios — no califican como lógica de negocio.

La migración puede ejecutarse actualizando únicamente visions.py (re-export hub)
y 2 forward references en results.py, sin tocar los 15 consumidores downstream.
El riesgo de regresión es BAJO. La paridad Excel no se ve afectada.
```
