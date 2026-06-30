# Índice de documentación de refactor

## Propósito

`docs/refactor` conserva reportes, auditorías y decisiones tomadas durante los
trabajos de paridad V2-8, estructura modular, persistencia y preparación de
producción.

## Estado actual

| Área | Estado |
|---|---|
| Paridad V2-8 | Cerrada con validación de golden y verify. |
| API, motor y persistencia | Lista para `DB_PROVIDER=json`. |
| Smoke productivo backend | Cerrado para health, readiness, CORS y configuración. |
| Estructura modular y DB | Cerrada tras limpieza de imports y shims. |
| Mapa de fórmulas | Cerrado con documentación de lineage. |
| Cosmos real | Diferido hasta contar con endpoint y credenciales. |

## Documentos canónicos

| Documento | Propósito |
|---|---|
| `v28_final_closure_status.md` | Cierre formal V2-8. |
| `CLOSEOUT_REPORT.md` | Cierre de canonicalización de input contract. |
| `FINAL_BRANCH_STABILITY_REPORT.md` | Estabilidad de rama tras fixes de API y persistencia. |
| `FINAL_BRANCH_STABILITY_AFTER_API_ROUTER.md` | Estabilidad tras modularización de router API v1. |
| `module_db_structure_audit.md` | Auditoría completa de estructura módulo/DB. |
| `module_structure_polish_audit.md` | Estado de pulido modular. |
| `calculator_motor_structure_audit.md` | Auditoría de `calculator_motor`. |
| `architecture_exceptions.md` | Excepciones arquitectónicas explícitas. |
| `persistence_architecture_decision_f4_f8.md` | Decisiones de persistencia F4/F8. |
| `engine_runtime_contract_audit.md` | Auditoría del contrato runtime del motor. |

## Producción y persistencia

| Documento | Propósito |
|---|---|
| `api_production_readiness_audit.md` | Auditoría de seguridad y readiness de API. |
| `backend_production_smoke_audit.md` | Smoke de producción backend. |
| `persistence_traceability_audit.md` | Ciclo de vida de resultados y trazabilidad. |
| `db_agnostic_persistence_closeout.md` | Cierre de persistencia agnóstica a backend. |

## Fórmulas, paridad y negocio

| Documento | Propósito |
|---|---|
| `formula_map_v28.md` | Mapa Excel celda a función backend. |
| `BUSINESS_GLOSSARY.md` | Glosario de dominio. |
| `excel_backend_parity_certification_closeout.md` | Cierre de certificación de paridad Excel. |
| `v28_archive_index.md` | Índice de investigaciones V2-8. |
| `v28_backlog.md` | Hallazgos diferidos. |

## Parametrización y shared

| Documento | Propósito |
|---|---|
| `parametrization_source_policy.md` | Política de fuente canónica de parametrización. |
| `parametrizacion_business_rules_domain_removal.md` | Decisión de extracción de reglas de negocio. |
| `shared_module_taxonomy_audit.md` | Auditoría histórica de taxonomía shared. |
| `shared_boundary_reorganization_audit.md` | Auditoría de límites shared. |

## Documentos históricos

Los documentos de fases, investigaciones CTS, wiring de fórmulas y pasos DB se
conservan como evidencia. No deben borrarse desde cambios de documentación
general; cualquier archivo histórico debe moverse o archivarse solo en una fase
dedicada.

## Validación registrada

Último estado documentado de la rama `refactor/modular-pure` al 2026-06-14:

```text
lineage:   11/11 PASS
contracts: 55/55 PASS
API:       123/123 PASS
golden:    99/99 PASS
make verify: baseline match, sin drift
```

## Guía de navegación

- Empezar por `v28_final_closure_status.md` para resumen ejecutivo V2-8.
- Leer `module_structure_polish_audit.md` antes de tocar estructura de módulos.
- Leer `calculator_motor_structure_audit.md` antes de cambiar el motor.
- Leer `formula_map_v28.md` antes de tocar fórmulas.
- Revisar `v28_backlog.md` para pendientes diferidos.
