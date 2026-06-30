# SHARED_MODELS_REORGANIZATION_AUDIT

**Status:** AUDITORÍA COMPLETA — Pendiente migración por fases  
**Fecha:** 2026-06-10  
**Rama:** `refactor/modular-pure`

---

## 1. Objetivo

Eliminar el uso incorrecto de `modules/shared/models` como contenedor genérico de modelos de negocio y redistribuir los modelos hacia sus dominios correspondientes, garantizando:

- Arquitectura modular pura
- Ownership claro por módulo vertical
- Separación de responsabilidades (input/output/presentación)
- Cero duplicidad conceptual
- Cero dependencias ambiguas

---

## 2. Inventario

### 2.1 Archivos existentes en `modules/shared/models/`

| Archivo | Clases definidas | Función actual |
|---|---|---|
| `panel.py` | 18 | Modelos de entrada del motor (PricingRequest, PanelDeControl, Cadenas A/B/C, Nómina) |
| `results.py` | 9 | Outputs del pipeline de 10 capas (ResultadoNomina → PricingResult) |
| `visions_cts.py` | 4 | DTOs de presentación Cost-To-Serve |
| `visions_tarifas.py` | 18 | DTOs de presentación Visión Tarifas |
| `visions_pyg.py` | 4 | DTOs de presentación Visión P&G |
| `visions_imprimible.py` | 14 | DTOs de presentación Visión Imprimible |
| `visions.py` | 0 (57 re-exportados) | Router de re-exportación de todos los DTOs de visión |

**Total: 67 clases de negocio en `shared/models`.**

---

## 3. Clasificación por clase

### panel.py — 18 clases

| Clase | Clasificación | Dominio propietario |
|---|---|---|
| `PricingRequest` | DOMAIN_MODEL | `calculator_motor/dto/` — Facade de entrada al motor |
| `PanelDeControl` | DOMAIN_MODEL | `panel/` — Input del Panel de Control General |
| `PerfilCadenaA` | DOMAIN_MODEL | `cadena_a/models/` — Perfil operacional Cadena A |
| `ParametrosNomina` | DOMAIN_MODEL | `cadena_a/models/` — Parámetros de nómina |
| `ParametrosNoPayroll` | DOMAIN_MODEL | `cadena_a/models/` — Costos no-nómina por estación |
| `CanalCadenaB` | DOMAIN_MODEL | `cadena_b/models/` — Canal digital Cadena B |
| `ParametrosCadenaB` | DOMAIN_MODEL | `cadena_b/models/` — Parámetros completos Cadena B |
| `CanalCadenaC` | DOMAIN_MODEL | `cadena_c/models/` — Canal IA Cadena C |
| `ParametrosCadenaC` | DOMAIN_MODEL | `cadena_c/models/` — Parámetros completos Cadena C |
| `EscenarioComercial` | DOMAIN_MODEL | `panel/` o `calculator_motor/dto/` — Escenario de facturación |
| `PolizaConfiguracion` | DOMAIN_MODEL | `calculator_motor/dto/` — Póliza de seguro por cadena |
| `PolizaContractual` | DOMAIN_MODEL | `calculator_motor/dto/` — Póliza contractual del deal |
| `ParametrosCalculo` | DOMAIN_MODEL | `calculator_motor/dto/` — Parámetros técnicos de algoritmo |
| `CadenasActivas` | SHARED_REAL | `shared/models/` — Estado booleano transversal de cadenas |
| `Indexacion` | SHARED_REAL | `shared/models/` — Value object de indexación (multi-dominio) |
| `ItemOpexConsumoB` | DOMAIN_MODEL | `cadena_b/models/` — Ítem de consumo variable (metering) |
| `MiembroEquipo` | DOMAIN_MODEL | `calculator_motor/dto/` — Miembro de equipo operativo |
| `DispositivoSM` | DOMAIN_MODEL | `cadena_b/models/` — Dispositivo tecnológico S&M |

### results.py — 9 clases

| Clase | Clasificación | Dominio propietario |
|---|---|---|
| `ResultadoNomina` | FORMULA_OUTPUT | `cadena_a/dto/` — Output capa 2 (NominaCalculator) |
| `ResultadoNoPayroll` | FORMULA_OUTPUT | `cadena_a/dto/` — Output capa 3 (NoPayrollCalculator) |
| `ResultadoCadenaB` | FORMULA_OUTPUT | `cadena_b/dto/` — Output capas 4-5 (CadenaBCalculator) |
| `ResultadoCadenaC` | FORMULA_OUTPUT | `cadena_c/dto/` — Output capa 6 (CadenaCCalculator) |
| `CostosTotalesMes` | FORMULA_OUTPUT | `pyg/dto/` — Output capa 7 (CostosTotalesCalculator) |
| `CostosFinancierosMes` | FORMULA_OUTPUT | `pyg/dto/` — Output capa 8 (CostosFinancierosCalculator) |
| `PyGMensual` | FORMULA_OUTPUT | `pyg/dto/` — Output capa 9 (PyGCalculator) |
| `KPIsDeal` | FORMULA_OUTPUT | `pyg/dto/` — Output capa 10 (KPIsCalculator) |
| `PricingResult` | FORMULA_OUTPUT | `calculator_motor/dto/` — Output completo del pipeline |

### visions_cts.py — 4 clases

| Clase | Clasificación | Dominio propietario |
|---|---|---|
| `DesgloseCTSCadenaA` | DTO_PRESENTACION | `vision_cost_to_serve/dto/` |
| `DesgloseCTSCadenaB` | DTO_PRESENTACION | `vision_cost_to_serve/dto/` |
| `CanalCTSDetalle` | DTO_PRESENTACION | `vision_cost_to_serve/dto/` |
| `ResultadoCostToServe` | DTO_PRESENTACION | `vision_cost_to_serve/dto/` |

### visions_tarifas.py — 18 clases

| Clase | Clasificación | Dominio propietario |
|---|---|---|
| `TarifaCanal` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `EscenarioTarifasResumen` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `ReglasBusiness` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `DesgloseCadenaTarifas` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `ImproductiveBreakdown` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `TimeCascade` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `ComponenteFijo` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `MesComision` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `ComponenteVariable` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `TarifaXVenta` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `DesgloseProductoOpex` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `TarifasEscenario` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `EscenarioTarifasDetalle` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `ResultadoVisionTarifas` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `ReglaNegocios` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `WaterfallPromedio` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `CriterioRiesgo` | DTO_PRESENTACION | `vision_tarifas/dto/` |
| `EvaluacionRiesgo` | DTO_PRESENTACION | `vision_tarifas/dto/` |

### visions_pyg.py — 4 clases

| Clase | Clasificación | Dominio propietario |
|---|---|---|
| `VisionPyGRow` | DTO_PRESENTACION | `pyg/dto/` |
| `VisionPyGRowDetalle` | DTO_PRESENTACION | `pyg/dto/` |
| `ResumenEjecutivoPyG` | DTO_PRESENTACION | `pyg/dto/` |
| `VisionPyG` | DTO_PRESENTACION | `pyg/dto/` |

### visions_imprimible.py — 14 clases

| Clase | Clasificación | Dominio propietario |
|---|---|---|
| `FichaDelDeal` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `EconomicsDeal` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `ConfiguracionComercial` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `EvolucionMensual` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `ComparativoEscenario` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `VisionServicioResumen` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `ModalidadCanalMetricas` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `CanalResumen` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `CanalDetalleModalidad` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `CanalDetalle` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `RolEquipo` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `GrupoCargoEquipo` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `EstructuraEquipo` | DTO_PRESENTACION | `vision_imprimible/dto/` |
| `VisionImprimible` | DTO_PRESENTACION | `vision_imprimible/dto/` |

---

## 4. Impacto en imports

### Consumidores por archivo

| Archivo | Consumidores (módulos) | Símbolos importados | Riesgo |
|---|---|---|---|
| `panel.py` | 26 archivos (calculator_motor, cadena_*, vision_*, pyg, audit) | ~210 símbolos | **ALTO** |
| `results.py` | 27 archivos (+vision_cost_to_serve/models/cts_facts.py) | ~150 símbolos | **ALTO** |
| `visions_cts.py` | 26 archivos | ~40 símbolos | **MEDIO** |
| `visions_tarifas.py` | 26 archivos (incluye cross-import desde visions_imprimible) | ~120 símbolos | **MEDIO-ALTO** |
| `visions_pyg.py` | 26 archivos | ~30 símbolos | **MEDIO** |
| `visions_imprimible.py` | 26 archivos | ~100 símbolos | **MEDIO-ALTO** |
| `visions.py` | 26 archivos (re-export router) | 57 re-exportados | **BAJO** |

### Acoplamiento crítico identificado

| Consumidor | Símbolos | Complejidad de migración |
|---|---|---|
| `calculator_motor/context_builder.py` + 4 mixins | 18 símbolos de panel.py c/u | MUY ALTA — hub de inyección |
| `calculator_motor/serializers/pricing_result_serializer.py` | 11 símbolos de visions_* | ALTA — despacha por tipo |
| `vision_imprimible/builders/vision_imprimible_builder.py` | 24 símbolos de visions_imprimible + tarifas | ALTA — constructor compuesto |
| `vision_tarifas/reglas.py` + 2 mixins | 18 símbolos de visions_tarifas | ALTA — reglas del dominio |

### Dependencia circular potencial

`visions_imprimible.py` importa desde `visions_tarifas.py` (`TarifaCanal`, `ReglaNegocios`, `WaterfallPromedio`, `EvaluacionRiesgo`). Al redistribuir, estas dos deben moverse en la **misma fase** o el primero en moverse debe re-exportar temporalmente desde el segundo.

---

## 5. Diseño final de `shared/models`

Después de la migración, `shared/models` debe quedar reducido a:

```
shared/
  models/
    __init__.py   ← re-exporta solo los SHARED_REAL
    base.py       ← Indexacion, CadenasActivas (value objects transversales)
```

**Candidatos SHARED_REAL confirmados:**

| Clase | Justificación |
|---|---|
| `CadenasActivas` | Estado booleano agregador, sin semántica de cálculo, usado en 3+ dominios |
| `Indexacion` | Value object genérico de indexación salarial/tecnológica, cross-cutting |

**Todo lo demás se mueve a su dominio propietario.**

---

## 6. Plan de migración por fases

### Prerrequisito: ejecutar tests antes de cada fase

```bash
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short
```

Baseline esperado: 1249 pass / 57 fail (estable en `refactor/modular-pure`).

---

### Fase 1 — Visión Tarifas + Visión Imprimible (bajo riesgo de ciclos)

**Objetivo:** Mover DTOs de presentación de visions_tarifas y visions_imprimible.

**Archivos afectados:**
- Crear `modules/vision_tarifas/dto/models.py` con las 18 clases de visions_tarifas
- Crear `modules/vision_imprimible/dto/models.py` con las 14 clases de visions_imprimible
- Actualizar imports en consumers (vision_tarifas/reglas.py, vision_imprimible/builders/*)
- Actualizar serializer dispatch

**Checklist:**
- [ ] Tests antes (baseline)
- [ ] Crear `dto/models.py` en cada módulo visión
- [ ] Actualizar imports en consumers
- [ ] Tests después (sin regresión)
- [ ] Validar paridad (`make validate-excel`)
- [ ] Añadir guardrails: `visions_tarifas` y `visions_imprimible` no importados desde shared

---

### Fase 2 — Visión P&G + Visión Cost-To-Serve

**Objetivo:** Mover DTOs de presentación de visions_pyg y visions_cts.

**Archivos afectados:**
- Crear `modules/pyg/dto/` con clases de visions_pyg
- Crear `modules/vision_cost_to_serve/dto/` con clases de visions_cts
- Actualizar pyg/builders/*, vision_cost_to_serve/services/*

**Checklist:**
- [ ] Tests antes
- [ ] Crear `dto/` en cada módulo
- [ ] Actualizar imports
- [ ] Tests después
- [ ] Validar paridad
- [ ] Actualizar `visions.py` re-exportador (o eliminar)

---

### Fase 3 — Resultados del pipeline (results.py)

**Objetivo:** Mover FORMULA_OUTPUT hacia módulos de dominio.

**Grupos:**
- `ResultadoNomina`, `ResultadoNoPayroll` → `cadena_a/dto/`
- `ResultadoCadenaB` → `cadena_b/dto/`
- `ResultadoCadenaC` → `cadena_c/dto/`
- `CostosTotalesMes`, `CostosFinancierosMes`, `PyGMensual`, `KPIsDeal` → `pyg/dto/`
- `PricingResult` → `calculator_motor/dto/`

**Advertencia:** `vision_cost_to_serve/models/cts_facts.py` importa `ResultadoNomina`, `ResultadoNoPayroll`, `ResultadoCadenaB` — actualizar después de Fases 1-2.

**Checklist:**
- [ ] Tests antes
- [ ] Crear `dto/` en cada cadena
- [ ] Mover clases de resultado
- [ ] Actualizar serializers y builders
- [ ] Tests después
- [ ] Validar paridad
- [ ] Validar baseline (`make verify`)

---

### Fase 4 — Modelos de entrada de cadenas (panel.py parcial)

**Objetivo:** Mover modelos de entrada de cadenas A, B, C a sus módulos.

**Grupos:**
- `PerfilCadenaA`, `ParametrosNomina`, `ParametrosNoPayroll` → `cadena_a/models/`
- `CanalCadenaB`, `ParametrosCadenaB`, `ItemOpexConsumoB`, `DispositivoSM` → `cadena_b/models/`
- `CanalCadenaC`, `ParametrosCadenaC` → `cadena_c/models/`

**Advertencia ALTA:** `calculator_motor/context_builder.py` + 4 mixins importan estos modelos con ~18 símbolos c/u. Actualizar con cuidado para no romper el Composition Root.

**Checklist:**
- [ ] Tests antes
- [ ] Crear `models/` en cada cadena (o mover a archivo existente)
- [ ] Actualizar context_builder + mixins
- [ ] Tests después
- [ ] Validar paridad
- [ ] Validar baseline

---

### Fase 5 — Modelos del motor (panel.py resto + PricingRequest)

**Objetivo:** Consolidar modelos del motor en `calculator_motor/dto/`.

**Clases:**
- `PricingRequest` → `calculator_motor/dto/`
- `PanelDeControl`, `EscenarioComercial` → `panel/models/` o `calculator_motor/dto/`
- `PolizaConfiguracion`, `PolizaContractual`, `ParametrosCalculo`, `MiembroEquipo` → `calculator_motor/dto/`

**Checklist:**
- [ ] Tests antes
- [ ] Mover clases
- [ ] Actualizar engine.py, context_builder.py, audit/writer.py
- [ ] Tests después
- [ ] Validar paridad
- [ ] Validar baseline

---

### Fase 6 — Reducción final de shared/models

**Objetivo:** Dejar `shared/models` únicamente con `SHARED_REAL`.

**Acciones:**
- Eliminar `panel.py`, `results.py`, `visions_*.py` de shared/models
- Crear `shared/models/base.py` con `CadenasActivas`, `Indexacion`
- Actualizar `__init__.py` del paquete
- Añadir guardrail: `shared/models` solo puede contener `base.py`

---

## 7. Riesgos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Romper context_builder + 4 mixins (18 símbolos c/u) | ALTO | Fase 4 última; revisar manualmente cada mixin antes de cambiar |
| Dependencia circular visions_imprimible → visions_tarifas | MEDIO | Mover en la misma fase; re-exportar temporalmente |
| Serializer dispatch (11 símbolos de visions_*) | MEDIO | Actualizar después de que todas las visions tengan su `dto/` |
| Romper contratos públicos de API (PricingRequest, PricingResult) | ALTO | Mantener re-exportaciones en shared hasta versión de API estabilizada |
| Impacto en tests de paridad (golden values) | ALTO | Ejecutar `make validate-excel` después de cada fase |
| `PolizaConfiguracion` — posible dead code | BAJO | Verificar antes de mover; si no tiene consumidores activos, eliminar directamente |

---

## 8. Recomendaciones por fase

| Fase | Prioridad | Complejidad | Valor |
|---|---|---|---|
| Fase 1 (visions_tarifas + imprimible) | MEDIA | MEDIA | Ownership inmediato de los DTOs más voluminosos |
| Fase 2 (pyg + cts) | MEDIA | BAJA | Limpieza rápida, bajo acoplamiento |
| Fase 3 (results.py) | ALTA | MEDIA | Elimina la mayor dependencia de serializers |
| Fase 4 (cadenas en panel.py) | ALTA | ALTA | Requiere tocar context_builder — mayor riesgo |
| Fase 5 (motor en panel.py) | MEDIA | MEDIA | Finaliza la redistribución de inputs |
| Fase 6 (reducción final) | BAJA | BAJA | Limpieza cosmética; valor arquitectónico alto |

**Orden recomendado:** 2 → 1 → 3 → 4 → 5 → 6 (empezar por las visions más simples).

---

## 9. Criterios de aceptación

La auditoría se considera completada cuando:

- [ ] No queda ningún modelo de negocio en `shared/models`
- [ ] `shared/models/` solo contiene `base.py` (`CadenasActivas`, `Indexacion`)
- [ ] Cada modelo tiene ownership claro en su módulo vertical
- [ ] No hay duplicación conceptual entre módulos
- [ ] No hay imports ambiguos ni `from shared.models import *`
- [ ] No se han introducido dependencias circulares
- [ ] Baseline intacto: 1249 pass / 57 fail estable
- [ ] `make validate-excel` pasa (paridad Excel)
- [ ] `make verify` pasa (snapshot congelado)
- [ ] Contratos públicos de API no rotos (PricingRequest, PricingResult re-exportados si es necesario)

---

## 10. Estructura objetivo de `modules/` post-migración

```
shared/
  models/
    base.py           ← Indexacion, CadenasActivas (SHARED_REAL únicamente)

cadena_a/
  models/             ← PerfilCadenaA, ParametrosNomina, ParametrosNoPayroll
  dto/                ← ResultadoNomina, ResultadoNoPayroll

cadena_b/
  models/             ← CanalCadenaB, ParametrosCadenaB, ItemOpexConsumoB, DispositivoSM
  dto/                ← ResultadoCadenaB

cadena_c/
  models/             ← CanalCadenaC, ParametrosCadenaC
  dto/                ← ResultadoCadenaC

calculator_motor/
  dto/                ← PricingRequest, PricingResult, PolizaConfiguracion, PolizaContractual,
                         ParametrosCalculo, MiembroEquipo

panel/
  models/             ← PanelDeControl, EscenarioComercial

pyg/
  dto/                ← CostosTotalesMes, CostosFinancierosMes, PyGMensual, KPIsDeal
                         VisionPyG, VisionPyGRow, VisionPyGRowDetalle, ResumenEjecutivoPyG

vision_cost_to_serve/
  dto/                ← DesgloseCTSCadenaA, DesgloseCTSCadenaB, CanalCTSDetalle,
                         ResultadoCostToServe

vision_tarifas/
  dto/                ← TarifaCanal, EscenarioTarifasResumen, ReglasBusiness,
                         DesgloseCadenaTarifas, ImproductiveBreakdown, TimeCascade,
                         ComponenteFijo, MesComision, ComponenteVariable, TarifaXVenta,
                         DesgloseProductoOpex, TarifasEscenario, EscenarioTarifasDetalle,
                         ResultadoVisionTarifas, ReglaNegocios, WaterfallPromedio,
                         CriterioRiesgo, EvaluacionRiesgo

vision_imprimible/
  dto/                ← FichaDelDeal, EconomicsDeal, ConfiguracionComercial, EvolucionMensual,
                         ComparativoEscenario, VisionServicioResumen, ModalidadCanalMetricas,
                         CanalResumen, CanalDetalleModalidad, CanalDetalle, RolEquipo,
                         GrupoCargoEquipo, EstructuraEquipo, VisionImprimible
```
