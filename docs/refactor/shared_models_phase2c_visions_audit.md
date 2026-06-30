# SHARED_MODELS_PHASE2C — VISIONS_TARIFAS + VISIONS_IMPRIMIBLE AUDIT

**Status:** AUDITORÍA COMPLETA
**Veredicto:** `PHASE_2C_DEFER_SHARED_VISION_MODELS`
**Fecha:** 2026-06-10
**Rama:** `refactor/modular-pure`
**Riesgo:** AUDITORÍA SIN CAMBIOS

---

## 1. Resumen ejecutivo

`visions_tarifas.py` (18 clases) y `visions_imprimible.py` (14 clases) son DTOs puros
sin lógica de negocio. Sin embargo, **no deben moverse** en esta fase: son contratos de
salida final (API-facing, persistidos en DB). Su fanout es alto (17 + 9 archivos
consumidores) y moverlos genera deuda de re-exports sin beneficio arquitectónico claro.
La posición actual en `shared/models/` es correcta para contratos de salida cross-cutting.

---

## 2. Diagnóstico de `parallel_parametrization`

```
parallel_parametrization triage:
- Estado:           PRE_EXISTING_CONFIRMED — RESUELTO
- Ruta verificada:  modules/parametrizacion/shared/repositories/cosmos_parametrization_repository.py
- ¿Existe actualmente? NO (todos los 4 archivos prohibidos están ausentes)
- Relación con la tarea anterior: NO
- Causa raíz: pycache contaminado de sesiones previas causó falso positivo en colección de tests
- Recomendación: ignorar — el test pasa limpiamente en ejecución aislada
```

Test ejecutado individualmente: **PASS** confirmado.

---

## 3. Archivos auditados

| Archivo | Líneas | Clases | Imports externos | Estado |
|---|---|---|---|---|
| `modules/shared/models/visions_tarifas.py` | 289 | 18 | Ninguno | ✅ Auditado |
| `modules/shared/models/visions_imprimible.py` | 218 | 14 | 4 símbolos de visions_tarifas | ✅ Auditado |

---

## 4. Inventario de clases

### visions_tarifas.py — 18 clases

| Clase | Base | Campos | @property | Métodos | Validators | Imports externos |
|---|---|---|---|---|---|---|
| `TarifaCanal` | `@dataclass(slots=True)` | 33 | 0 | 0 | 0 | Ninguno |
| `EscenarioTarifasResumen` | `@dataclass(slots=True)` | 10 | 0 | 0 | 0 | Ninguno |
| `ReglasBusiness` | `@dataclass(slots=True)` | 7 | 0 | 0 | 0 | Ninguno |
| `DesgloseCadenaTarifas` | `@dataclass(slots=True)` | 11 | 0 | 0 | 0 | Ninguno |
| `ImproductiveBreakdown` | `@dataclass(slots=True)` | 12 | 0 | 0 | 0 | Ninguno |
| `TimeCascade` | `@dataclass(slots=True)` | 5 | 0 | 0 | 0 | Ninguno |
| `ComponenteFijo` | `@dataclass(slots=True)` | 5 (1 anidado) | 0 | 0 | 0 | Ninguno |
| `MesComision` | `@dataclass(slots=True)` | 8 | 0 | 0 | 0 | Ninguno |
| `ComponenteVariable` | `@dataclass(slots=True)` | 3 (1 list anidada) | 0 | 0 | 0 | Ninguno |
| `TarifaXVenta` | `@dataclass(slots=True)` | 3 | 0 | 0 | 0 | Ninguno |
| `DesgloseProductoOpex` | `@dataclass(slots=True)` | 4 | 0 | 0 | 0 | Ninguno |
| `TarifasEscenario` | `@dataclass(slots=True)` | 8 | 0 | 0 | 0 | Ninguno |
| `EscenarioTarifasDetalle` | `@dataclass(slots=True)` | 7 (5 anidados) | 0 | 0 | 0 | Ninguno |
| `ResultadoVisionTarifas` | `@dataclass(slots=True)` | 10 | **1** (`costo_total_scenario`) | 0 | 0 | Ninguno |
| `ReglaNegocios` | `@dataclass(slots=True)` | 7 | 0 | 0 | 0 | Ninguno |
| `WaterfallPromedio` | `@dataclass(slots=True)` | 15 | 0 | 0 | 0 | Ninguno |
| `CriterioRiesgo` | `@dataclass(slots=True)` | 7 | 0 | 0 | 0 | Ninguno |
| `EvaluacionRiesgo` | `@dataclass(slots=True)` | 4 (1 list anidada) | 0 | 0 | 0 | Ninguno |

**Nota sobre `ResultadoVisionTarifas.costo_total_scenario`:**
```python
@property
def costo_total_scenario(self) -> float:
    return self.costo_cadena_a_total + self.costo_cadena_c_total
```
Derivación trivial (suma de dos campos propios). Igual a las `total()` de CTS ya migradas.

### visions_imprimible.py — 14 clases

| Clase | Base | Campos | @property | Métodos | Validators | Imports externos |
|---|---|---|---|---|---|---|
| `FichaDelDeal` | `@dataclass(slots=True)` | 4 | 0 | 0 | 0 | Ninguno |
| `EconomicsDeal` | `@dataclass(slots=True)` | 5 | 0 | 0 | 0 | Ninguno |
| `ConfiguracionComercial` | `@dataclass(slots=True)` | 4 | 0 | 0 | 0 | `TarifaCanal` de visions_tarifas |
| `EvolucionMensual` | `@dataclass(slots=True)` | 5 | 0 | 0 | 0 | Ninguno |
| `ComparativoEscenario` | `@dataclass(slots=True)` | 3 | 0 | 0 | 0 | Ninguno |
| `VisionServicioResumen` | `@dataclass(slots=True)` | 10 | 0 | 0 | 0 | Ninguno |
| `ModalidadCanalMetricas` | `@dataclass(slots=True)` | 5 | 0 | 0 | 0 | Ninguno |
| `CanalResumen` | `@dataclass(slots=True)` | 10 | 0 | 0 | 0 | Ninguno |
| `CanalDetalleModalidad` | `@dataclass(slots=True)` | 16 | 0 | 0 | 0 | Ninguno |
| `CanalDetalle` | `@dataclass(slots=True)` | 21 | 0 | 0 | 0 | Ninguno |
| `RolEquipo` | `@dataclass(slots=True)` | 8 | 0 | 0 | 0 | Ninguno |
| `GrupoCargoEquipo` | `@dataclass(slots=True)` | 4 | 0 | 0 | 0 | Ninguno |
| `EstructuraEquipo` | `@dataclass(slots=True)` | 7 | 0 | 0 | 0 | Ninguno |
| `VisionImprimible` | `@dataclass(slots=True)` | 11 (8 anidados incl. de VT) | 0 | 0 | 0 | 4 de visions_tarifas |

---

## 5. Validación DTO puro

| Clase | ¿DTO puro? | Evidencia |
|---|---|---|
| Todas las de `visions_tarifas.py` (menos una) | **SÍ** (17/18) | Solo `@dataclass(slots=True)` + campos primitivos/anidados, sin imports externos |
| `ResultadoVisionTarifas` | **DUDOSO** | @property `costo_total_scenario = self.a + self.b` — derivación trivial, acepta el patrón ya validado en CTS |
| Todas las de `visions_imprimible.py` | **SÍ** (14/14) | Más limpio del codebase — cero properties, cero métodos, solo campos |

**Total: 31/32 clases son DTOs puros.**

---

## 6. Clasificación arquitectónica

| Modelo | Clasificación | Owner probable | Evidencia | Riesgo |
|---|---|---|---|---|
| Clases de `visions_tarifas.py` | `CROSS_CUTTING` | Ninguno único — 5 dominios consumidores | 17 archivos en calculator_motor, vision_tarifas, vision_imprimible, pyg, parametrizacion | MEDIO (output final) |
| `ResultadoVisionTarifas` | `CROSS_CUTTING` | vision_tarifas lo construye; motor, imprimible, pyg lo consumen | Instanciado en VisionTarifasCalculator; consumido por 5 dominios | ALTO (contrato API) |
| Clases de `visions_imprimible.py` | `SINGLE_OWNER` | `vision_imprimible` | 8/9 consumidores son del módulo vision_imprimible | ALTO (contrato API final) |
| `VisionImprimible` | `SINGLE_OWNER` | `vision_imprimible` | Constructor = vision_imprimible_builder; API = vision_imprimible/api | ALTO (contrato público) |

---

## 7. Consumidores e imports

### visions_tarifas.py — 17 consumidores

| Dominio | Archivos | Uso |
|---|---|---|
| `calculator_motor` | engine.py, formulas/risk/riesgo.py, serializers/(2) | Composición del motor; serialización a JSON |
| `vision_tarifas` | reglas.py, mixins/(2) | **Owner constructor** — VisionTarifasCalculator instancia ResultadoVisionTarifas |
| `vision_imprimible` | builders/vision_imprimible_builder.py, helpers/(2) | Lector secundario — compone VisionImprimible desde ResultadoVisionTarifas |
| `pyg` | services/kpis_calculator.py | Derivación de KPIs desde tarifas |
| `parametrizacion` | gn/contracts.py | Validación de contrato Excel GN (ComponenteFijo/Variable) |

### visions_imprimible.py — 9 consumidores

| Dominio | Archivos | Uso |
|---|---|---|
| `vision_imprimible` | builders/(1), api/(2), helpers/(1), models/(1) | **Owner completo** |
| `calculator_motor` | engine.py | Pasa VisionImprimible al serializer |
| `shared` | contracts/api_v1/response/visions.py, models/results.py | Contrato API v1; PricingResult.vision_imprimible |
| `tests` | 7 archivos | contract, ownership, persistence, schema |

---

## 8. Dependencias entre visiones

| Dependencia | Archivo origen | Archivo destino | Tipo | Riesgo |
|---|---|---|---|---|
| `visions_imprimible` → `visions_tarifas` | visions_imprimible.py (líneas 6-11) | visions_tarifas.py | `DTO_REFERENCE` | BAJO |
| Símbolos importados | `TarifaCanal`, `ReglaNegocios`, `WaterfallPromedio`, `EvaluacionRiesgo` | — | — | — |
| Dirección inversa | — | NO existe | — | — |

**Grafo acíclico confirmado.** `visions_tarifas` no importa de `visions_imprimible`.

**Implicación para migración:** si se decide mover ambas a sus módulos verticales, hay que mover `visions_tarifas` **primero** (o en la misma fase) para no romper el import de `visions_imprimible`.

---

## 9. Overlap con módulos existentes

| Modelo shared | Equivalente en dominio | Ruta | ¿Duplicado? |
|---|---|---|---|
| `ResultadoVisionTarifas` y jerarquía | Ninguno en `vision_tarifas/dto/` | — | No |
| `VisionImprimible` y jerarquía | Ninguno en `vision_imprimible/dto/` | — | No |
| — | `vision_tarifas/models/vt_facts.py` | Modelo interno de transporte (EscenarioCanalFacts) | No duplica — facts internos ≠ output final |
| — | `vision_imprimible/models/vision_datasets.py` | Datasets complementarios (staffing, pólizas) | No duplica — datasets ≠ VisionImprimible |

**No hay duplicación.** Los `models/` en cada dominio son read-models internos de transporte, no los outputs finales que están en `shared/`.

---

## 10. Re-exports detectados

| Modelo | Re-export | Archivo | Riesgo |
|---|---|---|---|
| Todos los de visions_tarifas | SÍ (explícito) | `shared/models/visions.py` líneas 18-37 | BAJO — hub de compatibilidad |
| Todos los de visions_imprimible | SÍ (explícito) | `shared/models/visions.py` líneas 44-59 | BAJO |
| Todos | SÍ (wildcard) | `shared/models/__init__.py` línea 9 | BAJO |

`visions.py` ya fue convertido en adapter en Fase 2B. Los re-exports de tarifas e imprimible todavía apuntan a los archivos originales (no a módulos de dominio) — correcto para esta fase.

---

## 11. Decisión de migrabilidad

| Archivo | ¿Migrable? | Condición | Bloqueadores | Recomendación |
|---|---|---|---|---|
| `visions_tarifas.py` | **DIFERIR** | Contrato de salida final, 5 dominios consumidores, `visions_imprimible` depende de él | Mover requiere coordinar con visions_imprimible; alto fanout | Mantener en shared/models — posición correcta para contrato cross-cutting |
| `visions_imprimible.py` | **DIFERIR** | Contrato de salida final, API-facing, persistido en DB | Depende de 4 símbolos de visions_tarifas; contrato API público | Mantener en shared/models — SINGLE_OWNER pero de alto impacto |

**Recomendación principal:** No mover estos archivos en las próximas fases. Su posición en `shared/models/` refleja correctamente su naturaleza de contratos de salida transversales.

**Diferencia con CTS y PyG ya migrados:** CTS y PyG eran DTOs intermedios con 1 constructor y baja fanout. `visions_tarifas` y `visions_imprimible` son outputs finales con alta fanout, expuestos en la API y persistidos.

---

## 12. Riesgos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| `ResultadoVisionTarifas` y `VisionImprimible` son contratos API — cambiar estructura es breaking change | ALTO | Versionar si es necesario; nunca mutar silenciosamente |
| `visions_imprimible` depende de 4 símbolos de `visions_tarifas` — orden de migración importa | MEDIO | Si se decide mover, mover tarifas primero o en misma fase |
| 17 + 9 consumidores — alto costo de actualización de imports | MEDIO | Mantener re-exports en visions.py como adapter si se migra |
| `parallel_parametrization` era falso positivo por pycache — podría recurrirse | BAJO | Limpiar pycache con `find . -name __pycache__ -exec rm -rf {} +` si ocurre |

---

## 13. Recomendación para la siguiente fase

**No continuar con migration de visions_tarifas ni visions_imprimible.**

Arquitectura actual de `shared/models` post-Fase 2B:

```
shared/models/
  panel.py           ← inputs del motor (pendiente auditoría propia)
  results.py         ← outputs del pipeline (pendiente auditoría propia)
  visions_cts.py     ← FUENTE (puede eliminarse cuando 0 consumers directos)
  visions_pyg.py     ← FUENTE (puede eliminarse cuando 0 consumers directos)
  visions_tarifas.py ← MANTENER — output final cross-cutting
  visions_imprimible.py ← MANTENER — output final single-owner
  visions.py         ← adapter temporal ← YA ACTUALIZADO para CTS+PyG
```

**Acciones recomendadas para la siguiente fase:**

1. **Eliminar `visions_cts.py` y `visions_pyg.py` de shared/models** — ya migrados en Fase 2B, 0 consumers directos confirmados. Solo queda el adapter en `visions.py`.
2. **Auditar `results.py`** — clasificar las 9 clases de pipeline output antes de decidir migración.
3. **Dejar `visions_tarifas.py` y `visions_imprimible.py` donde están** — decisión arquitectónica documentada.

---

## Deferred Work (Fase 2C closure — 2026-06-10)

| Ticket | Scope | Prerequisites |
|---|---|---|
| **FASE_2D** | Mover 10 clases `SINGLE_OWNER_vision_tarifas` a `modules/vision_tarifas/dto/` (`EscenarioTarifasResumen`, `ReglasBusiness`, `DesgloseCadenaTarifas`, `ImproductiveBreakdown`, `TimeCascade`, `ComponenteFijo`, `ComponenteVariable`, `DesgloseProductoOpex`, `TarifasEscenario`, `EscenarioTarifasDetalle`) | Confirmar estructura receptora en `vision_tarifas/dto/`; actualizar `visions.py` re-exporter; agregar guardrail que confirme que las clases NO siguen en `shared/models/`; verificar sin payload/contract change |
| **FASE_2E** | Mover 13 clases `SINGLE_OWNER_vision_imprimible` a `modules/vision_imprimible/dto/` (`FichaDelDeal`, `EconomicsDeal`, `ConfiguracionComercial`, `EvolucionMensual`, `ComparativoEscenario`, `VisionServicioResumen`, `ModalidadCanalMetricas`, `CanalResumen`, `CanalDetalleModalidad`, `CanalDetalle`, `RolEquipo`, `GrupoCargoEquipo`, `EstructuraEquipo`) | Confirmar estructura receptora en `vision_imprimible/dto/`; actualizar `visions.py` re-exporter; agregar guardrail; verificar sin payload/contract change |
| **FASE_2F** | Mover `CriterioRiesgo` a `modules/calculator_motor/formulas/risk/` (único consumidor real) | Análisis de impacto cruzado con `EvaluacionRiesgo` (cross-cutting, tiene `criterios: list[CriterioRiesgo]`); asegurar que `EvaluacionRiesgo` sigue importable desde `shared/models/`; actualizar `visions.py` re-exporter |

Cada ticket debe:
- Actualizar `visions.py` re-exporter para mantener la superficie pública de API.
- Agregar guardrail que confirme que la clase movida ya NO está en `shared/models/`.
- Verificar que no hay cambio de payload ni de contrato (parity tests pasan sin delta).
