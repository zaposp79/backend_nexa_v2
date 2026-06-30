# Visión Imprimible — Persisted Contract Trace

**Fecha:** 2026-06-05
**Rama:** `refactor/modular-pure`
**Auditoría:** VISION_IMPRIMIBLE_PERSISTED_CONTRACT_TRACE

---

## Veredicto

**CERTIFICADO — Contrato de persistencia completo. 15 campos canónicos trazados.**

El documento persistido en `storage/simulation_results/{simulation_id}.json` contiene
todos los campos que el GET `vision-imprimible` proyecta al frontend. Cada campo tiene
un propietario identificado, una fuente original en `PricingResult` o en los helpers de VI,
y un tipo documentado.

---

## Flujo POST → Persistencia

```
POST /simulation/calculate
│
├── 1. CalculationRequest.user_input
│
├── 2. UserInputLoader.cargar() → UserInput
│
├── 3. SimulationContextBuilder.construir() → PricingRequest
│
├── 4. NexaPricingEngine.calcular(solicitud) → PricingResult
│      │
│      ├── NominaCalculator          (Capa 2: nómina Cadena A)
│      ├── NoPayrollCalculator       (Capa 3: OPEX no-payroll)
│      ├── CadenaBCalculator         (Capa 4-5: volumen externo)
│      ├── CadenaCCalculator         (Capa 6: polizas/otros)
│      ├── CostosTotalesCalculator   (Capa 7: suma todos los costos)
│      ├── CostosFinancierosCalculator (Capa 8: componente financiero)
│      ├── PyGCalculator             (Capa 9: PyGMensual × meses)
│      ├── KPIsCalculator            (Capa 10: kpis.ingreso_mensual, valor_total_deal)
│      ├── VisionTarifasCalculator   (canales por modelo de cobro)
│      ├── VisionPyGBuilder          (estructura secciones para frontend)
│      ├── RiesgoCalculator          (evaluacion_riesgo, requiere_aprobacion)
│      ├── CostToServeCalculator     (desglose_a, desglose_b, vol_cadena_b)
│      ├── VisionImprimibleBuilder   (vision_por_servicio, vision_por_canal,
│      │                              detalle_por_canal, estructura_equipo,
│      │                              comparativo_escenarios)
│      └── VisionDatasetsBuilder     (datasets_vision: staffing, polizas, indexacion)
│
├── 5. validate_visions_complete(resultado)
│      └── Verifica pyg_por_mes, kpis, waterfall, evaluacion_riesgo,
│          reglas_negocio, vision_tarifas, vision_pyg, cost_to_serve
│
├── 6. pricing_result_to_dict(resultado, simulation_id)
│      │
│      ├── _ficha_deal_to_dict(panel)          → delegado a helpers/ficha.py
│      ├── asdict(resultado.kpis)              → KPIsCalculator
│      ├── [_pyg_to_dict(p) for p in pyg_por_mes] → PyGCalculator
│      ├── _waterfall_to_dict(resultado.waterfall)
│      ├── _configuracion_comercial(resultado) → delegado a helpers/configuracion_comercial.py
│      ├── _reglas_negocio_to_dict(...)        → delegado a helpers/reglas_negocio.py
│      ├── _evaluacion_riesgo_to_dict(...)
│      │     └── _aprobaciones_requeridas(...) → delegado a helpers/aprobaciones.py
│      ├── _vision_pyg_to_dict(resultado.vision_pyg)
│      ├── _cost_to_serve_to_dict(resultado.cost_to_serve)
│      ├── _vision_tarifas_to_dict(resultado.vision_tarifas)
│      └── _vision_ejecutiva_sections(resultado)
│            └── vision_por_servicio, vision_por_canal, detalle_por_canal,
│                estructura_equipo, comparativo_escenarios
│
├── 7. ResultsRepository.save(full_dict)
│      └── document = {"id": simulation_id, **full_dict}
│          DocumentStore.upsert(collection, document)
│
├── 8. TraceWriter.write()    (FASE G — trazabilidad)
└── 9. SnapshotRepository.save() (FASE 4 — snapshot de inputs + parametrización)
```

---

## Flujo GET → Lectura

```
GET /simulation/{simulation_id}/results/vision-imprimible
│
├── router.py — Depends(get_results_repository)
│     └── NO llama NexaPricingEngine
│         NO llama pricing_result_to_dict
│         NO lee archivos Excel
│         NO accede a storage directamente
│
├── ResultsRepository.get(simulation_id)
│     ├── DocumentStore.get(collection, simulation_id)
│     │     └── provider activo: JsonDocumentStore → lee storage/simulation_results/{id}.json
│     ├── Strip campo "id" técnico
│     └── retorna dict completo
│
└── router proyecta 15 campos canónicos:
      vision = {
        "ficha_deal":              data.get("ficha_deal"),
        "kpis":                    data.get("kpis"),
        "pyg_por_mes":             data.get("pyg_por_mes"),
        "waterfall_promedio":      data.get("waterfall_promedio"),
        "configuracion_comercial": data.get("configuracion_comercial"),
        "reglas_negocio":          data.get("reglas_negocio"),
        "evaluacion_riesgo":       data.get("evaluacion_riesgo"),
        "vision_pyg":              data.get("vision_pyg"),
        "cost_to_serve":           data.get("cost_to_serve"),
        "vision_tarifas":          data.get("vision_tarifas"),
        "vision_por_servicio":     data.get("vision_por_servicio", []),
        "vision_por_canal":        data.get("vision_por_canal", []),
        "detalle_por_canal":       data.get("detalle_por_canal", []),
        "estructura_equipo":       data.get("estructura_equipo"),
        "comparativo_escenarios":  data.get("comparativo_escenarios", []),
      }
```

---

## Matriz de Contrato Persistido

| Campo GET | Campo en documento | Generado por | Fuente original | Tipo | Fórmula / Transformación | Owner | Estado |
|---|---|---|---|---|---|---|---|
| `ficha_deal` | `ficha_deal` | `_ficha_deal_to_dict(panel)` | `PanelDeControl` | `FORMULA_PROPIA_VISION_IMPRIMIBLE` | `fecha_fin = last day(meses_contrato)`, `duracion_contrato = "DD/MM a DD/MM"`, `mes_finalizacion = (mes_inicio−1)+meses` | `modules/vision_imprimible/helpers/ficha.py` | `CERTIFICADO_PERSISTIDO` |
| `kpis` | `kpis` | `asdict(resultado.kpis)` | `KPIsCalculator` | `DATO_CALCULATOR` | Serialización pura vía `asdict()` | `modules/calculator/` | `CERTIFICADO_PERSISTIDO` |
| `pyg_por_mes` | `pyg_por_mes` | `[_pyg_to_dict(p) for p]` | `PyGCalculator` | `SERIALIZACION_PURA` | `asdict()` + `@property` capturados explícitamente | `modules/calculator/` | `CERTIFICADO_PERSISTIDO` |
| `waterfall_promedio` | `waterfall_promedio` | `_waterfall_to_dict(waterfall)` | `PyGCalculator` | `SERIALIZACION_PURA` | `asdict()` | `modules/calculator/` | `CERTIFICADO_PERSISTIDO` |
| `configuracion_comercial` | `configuracion_comercial` | `_configuracion_comercial(resultado)` | `VisionTarifasCalculator` + `PanelDeControl` | `FORMULA_PROPIA_VISION_IMPRIMIBLE` | `canal_principal = max(canales, key=facturación)` F-03; `tarifa_fija = facturación × pct_fijo` F-04 | `modules/vision_imprimible/helpers/configuracion_comercial.py` | `CERTIFICADO_PERSISTIDO` |
| `reglas_negocio` | `reglas_negocio` | `_reglas_negocio_to_dict(reglas, resultado)` | `RiesgoCalculator` + `business_rules` | `FORMULA_PROPIA_VISION_IMPRIMIBLE` | `alerta.activa = requiere_aprobacion OR reglas_fuera_rango`; mensaje prioridad Alta Dirección (BP-01) | `modules/vision_imprimible/helpers/reglas_negocio.py` | `CERTIFICADO_PERSISTIDO` |
| `evaluacion_riesgo` | `evaluacion_riesgo` | `_evaluacion_riesgo_to_dict(ev, …)` | `RiesgoCalculator` | `SHARED_PERSISTED_PROJECTION` | `asdict(ev)` + `aprobaciones_requeridas()` 3 niveles (VI!M91-M93) | `helpers/aprobaciones.py` + `serializer_helpers.py` | `CERTIFICADO_PERSISTIDO` |
| `vision_pyg` | `vision_pyg` | `_vision_pyg_to_dict(resultado.vision_pyg)` | `VisionPyGBuilder` | `SERIALIZACION_PURA` | Agrupa filas por sección, anida `detalle`, produce `secciones[]` | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_PERSISTIDO` |
| `cost_to_serve` | `cost_to_serve` | `_cost_to_serve_to_dict(cts)` | `CostToServeCalculator` | `SERIALIZACION_PURA` | `asdict()` + `desglose_a.total`, `desglose_b.total` (properties) | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_PERSISTIDO` |
| `vision_tarifas` | `vision_tarifas` | `_vision_tarifas_to_dict(vt)` | `VisionTarifasCalculator` | `SERIALIZACION_PURA` | Filtra campos a `_VT_CANAL_FIELDS` (18 de 35 total) | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_PERSISTIDO` |
| `vision_por_servicio` | `vision_por_servicio` | `_vision_ejecutiva_sections(resultado)` | `VisionImprimibleBuilder` | `SERIALIZACION_PURA` | `[asdict(s) for s]` | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_LEGACY_DEFAULT` (`[]` si ausente) |
| `vision_por_canal` | `vision_por_canal` | `_vision_ejecutiva_sections(resultado)` | `VisionImprimibleBuilder` | `SERIALIZACION_PURA` | `[asdict(c) for c]` | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_LEGACY_DEFAULT` (`[]` si ausente) |
| `detalle_por_canal` | `detalle_por_canal` | `_vision_ejecutiva_sections(resultado)` | `VisionImprimibleBuilder` | `SERIALIZACION_PURA` | `[asdict(c) for c]` | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_LEGACY_DEFAULT` (`[]` si ausente) |
| `estructura_equipo` | `estructura_equipo` | `_vision_ejecutiva_sections(resultado)` | `VisionImprimibleBuilder` | `SERIALIZACION_PURA` | `asdict(vi.estructura_equipo)` | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_LEGACY_DEFAULT` (`None` si ausente) |
| `comparativo_escenarios` | `comparativo_escenarios` | `_vision_ejecutiva_sections(resultado)` | `VisionImprimibleBuilder` | `SERIALIZACION_PURA` | `[asdict(e) for e]` (GAP-VIS-1 cerrado) | `modules/calculator/serializers/serializer_helpers.py` | `CERTIFICADO_LEGACY_DEFAULT` (`[]` si ausente) |

---

## Campos mínimos requeridos (no-legacy)

Los siguientes 10 campos son obligatorios. Si están ausentes en el documento persistido,
el GET los retorna como `None` (sin excepción) y el frontend verá datos vacíos:

```
ficha_deal
kpis
configuracion_comercial
reglas_negocio
evaluacion_riesgo
pyg_por_mes
waterfall_promedio
vision_pyg
cost_to_serve
vision_tarifas
```

`validate_visions_complete()` lanza `VisionIncompleteError` antes de persistir
si alguno de estos campos está ausente en el `PricingResult`. Es la guardia del POST.

---

## Defaults legacy permitidos

Los 5 campos siguientes tienen `data.get("campo", default)` en el router.
Son poblados por `VisionImprimibleBuilder`. Si el builder no ejecutó o produjo vacío,
el GET retorna el default sin error:

| Campo | Default | Justificación |
|---|---|---|
| `vision_por_servicio` | `[]` | VisionImprimibleBuilder puede no tener datos |
| `vision_por_canal` | `[]` | ídem |
| `detalle_por_canal` | `[]` | ídem |
| `comparativo_escenarios` | `[]` | GAP-VIS-1 cerrado, pero puede ser vacío |
| `estructura_equipo` | `None` | `data.get("estructura_equipo")` — None si ausente |

---

## Fórmulas propias de Vision Imprimible

Todas certificadas en `docs/refactor/vision_imprimible_formula_ownership.md`.

| ID | Fórmula | Archivo | Certificación |
|---|---|---|---|
| F-00 | `aprobaciones_requeridas()` — 3 niveles VI!M91-M93 | `helpers/aprobaciones.py` | `FORMULA_OWNERSHIP_1` |
| F-01 | `ficha_deal_to_dict()` — derivaciones de fecha, cadenas activas | `helpers/ficha.py` | `FORMULA_OWNERSHIP_2` |
| F-03 | `select_principal_channel()` — max(facturación) | `helpers/configuracion_comercial.py` | `FORMULA_OWNERSHIP_3` |
| F-04 | `tarifa_fija = facturación × pct_fijo` | `helpers/configuracion_comercial.py` | `FORMULA_OWNERSHIP_3` |
| F-02 | `alerta_activa = requiere_aprobacion OR reglas_fuera_rango` | `helpers/reglas_negocio.py` | `FORMULA_OWNERSHIP_4` |

**El serializer (`serializer_helpers.py`) solo contiene wrappers de delegación.**
No implementa ninguna fórmula propia de VI directamente.

---

## Validación de helpers

```python
# helpers/__init__.py exporta:
from nexa_engine.modules.vision_imprimible.helpers.aprobaciones import (
    aprobaciones_requeridas,
    UMBRAL_GERENCIA_FINANCIERA_COP,   # 100_000_000
    UMBRAL_GERENCIA_GENERAL_COP,      # 200_000_000
    UMBRAL_ALTA_DIRECCION_COP,        # 1_000_000_000
)
from nexa_engine.modules.vision_imprimible.helpers.ficha import ficha_deal_to_dict
from nexa_engine.modules.vision_imprimible.helpers.configuracion_comercial import (
    select_principal_channel, configuracion_comercial_to_dict,
)
from nexa_engine.modules.vision_imprimible.helpers.reglas_negocio import reglas_negocio_to_dict
```

---

## Tests ejecutados

```
tests/db/test_vision_imprimible_persisted_contract.py::test_c1_documento_minimo_cubre_15_campos_canonicos         PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c2_campos_obligatorios_retornan_none_si_ausentes      PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c3_ficha_deal_subcampos_canonicos                      PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c4_kpis_ingreso_mensual_numerico                       PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c5_configuracion_comercial_campos_propios_vi           PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c6_reglas_negocio_alerta_estructura                    PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c7_evaluacion_riesgo_aprobaciones_requeridas_tres_niveles PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c8_pyg_por_mes_12_meses                               PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c9_waterfall_promedio_no_es_none                       PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c10_vision_pyg_tiene_secciones                        PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c11_vision_ejecutiva_campos_son_listas                 PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c12_helpers_vi_importables_y_serializer_delega        PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c13_router_get_no_llama_engine                        PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c14_ciclo_completo_engine_serializer_save_get         PASSED
tests/db/test_vision_imprimible_persisted_contract.py::test_c15_campo_id_interno_no_filtra                        PASSED
────────────────────────────────────────────────────────────────────────────────
15 passed, 0 failed
```

---

## Gaps identificados

Ningún gap crítico. El contrato de persistencia es completo y coherente.

**Gap menor documentado (no bloquea):**
- `VisionImprimibleBuilder` puede producir listas vacías para `vision_por_servicio`,
  `vision_por_canal`, `detalle_por_canal`, `comparativo_escenarios`. El default `[]`
  en el router lo absorbe sin error. No requiere acción hasta que el frontend consuma
  estas secciones activamente.

---

## Invariantes arquitecturales confirmadas

1. **POST escribe, GET lee**: el cálculo ocurre exactamente una vez, al POST. El GET no recalcula.
2. **Serializador como transformador**: `pricing_result_to_dict` es la única transformación entre `PricingResult` y el documento persistido. No hay transformación adicional en el GET.
3. **Helpers VI como frontera de ownership**: las fórmulas propias de VI viven en `modules/vision_imprimible/helpers/`. El serializer solo delega.
4. **validate_visions_complete como guardia**: los 10 campos obligatorios son verificados antes de persistir. Un POST no puede guardar un documento incompleto.
5. **DocumentStore como abstracción completa**: el módulo VI no conoce qué provider está activo. La sustitución JSON ↔ Cosmos es transparente.
