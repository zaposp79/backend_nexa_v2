# Structure Audit Lite — Motor ↔ Vistas (Stage 1, read-only)

**Fecha:** 2026-06-10 · **Rama:** refactor/modular-pure · **Alcance:** inventario; sin acciones.

Decisión de arquitectura aprobada: **parity only, defer structural**. Se inventarían
violaciones de frontera motor↔vista pero NO se reestructura en esta fase.

## 1. Arquitectura real (hallazgo central)

El prompt rev7 asume separación estricta: *motor calcula+persiste → vistas releen y
recalculan sus fórmulas/gráficos en cada request*. La realidad es **híbrida**:

- `NexaPricingEngine.calcular()` (`modules/calculator_motor/engine.py`) ejecuta TODO el
  pipeline en una sola pasada, **incluyendo los builders de vista**
  (`VisionTarifasCalculator`, `VisionImprimibleBuilder`, `CostToServeCalculator`,
  `VisionPyGBuilder`). La lógica de vista vive en `modules/vision_*/` pero **corre dentro
  de la pasada del motor**.
- El `PricingResult` completo (con todas las sub-estructuras de vista ya calculadas) se
  persiste una vez vía `modules/calculator/persistence/results_repository.py`.
- Los endpoints HTTP de vista son **read-through puros**: devuelven la sub-estructura
  persistida; NO recalculan en request time.
- **No existen carpetas `charts/`** ni funciones `build_*_chart`.

Alcanzar la separación ideal del prompt = refactor estructural masivo → prohibido por el
propio prompt (`No refactor estructural masivo`) y kill-switch `MOTOR_VIEW_BOUNDARY_BREAK`.

## 2. Módulos motor

| Módulo | Rol |
|--------|-----|
| `calculator_motor/` | Engine (`NexaPricingEngine.calcular`), pipeline 10 capas, formulas (payroll, no_payroll, pricing, profitability, costos_financieros, risk), serializers, validation, models |
| `calculator/` | Orquestación API (`api/calculate_*`) + **persistencia** (`persistence/results_repository.py`, `traceability_repository.py`, `snapshots_repository.py`) |
| `pyg/services/` | `CostosTotalesCalculator`, `PyGCalculator`, `KPIsCalculator` (corren dentro del motor) |
| `cadena_b/reglas.py`, `cadena_c/reglas.py` | `CadenaBCalculator`, `CadenaCCalculator` (corren dentro del motor) |
| `panel/`, `cadena_a/` | Parametrización de input consumida por el motor |

## 3. Módulos vista

| Módulo | Endpoint | Patrón |
|--------|----------|--------|
| `vision_tarifas/` | `GET /results/vision-tarifas` | read-through; calc (`reglas.py`) corre dentro del motor |
| `vision_imprimible/` | `GET /results/vision-imprimible` | read-through; `builders/` corren dentro del motor |
| `vision_cost_to_serve/` | `GET /results/cost-to-serve` | read-through; `services/cost_to_serve_calculator.py` corre dentro del motor |
| `pyg/` | `GET /results/vision-pyg` | read-through; `builders/vision_pyg_builder.py` corre dentro del motor |

## 4. Violaciones de frontera (inventario — DIFERIDAS)

| Categoría | Descripción | Decisión |
|-----------|-------------|----------|
| `VIEW_LOGIC_IN_MOTOR` | Builders de vista invocados dentro de `engine.calcular()` (arquitectura híbrida por diseño actual) | DEFER a refactor estructural |
| `CHART_IN_MOTOR` | Datos de gráfico embebidos en domain models (`VisionPyGRow`, `EvolucionMensual`, `WaterfallPromedio`) construidos en la pasada del motor; no hay `charts/` | DEFER |
| `VIEW_RECALCS_MOTOR` | **No detectado** — las vistas NO reinvocan el motor (leen de persistencia) ✅ | n/a |
| `VAGUE_FILENAME` | **No detectado** — sin `utils.py`/`common.py`/`charts.py` monolíticos en `modules/` ✅ | n/a |

## 5. Conclusión

Arquitectura limpia salvo por la frontera híbrida motor↔vista (vista-lógica corre dentro
del motor). Se respeta la decisión "parity only": ningún cambio estructural en Stage 1.
Cualquier reubicación de charts/builders a `modules/<vision>/calculators/formulas/charts/`
pertenece a un refactor estructural posterior, fuera de esta fase de paridad.
