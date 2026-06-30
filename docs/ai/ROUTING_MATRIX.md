# Routing Matrix — Decisión rápida de tarea

## Regla general
Empieza barato. Escala solo si el riesgo lo exige.

**⚠️ Ahorro de contexto:** Lee `docs/ai/CONTEXT_SAVING_POLICY.md` para reducir tokens 50-88% según tarea.

| Tarea | Worker | Modelo | Leer mínimo | NO leer | Validación mínima |
|---|---|---|---|
| Leer estructura del repo | scanner-agent | haiku | CLAUDE.md + ROUTING_MATRIX.md | Excel, reportes, VALIDATION.md histórico | grep + resumen |
| Buscar archivos relevantes | scanner-agent | haiku | Archivos encontrados por grep | backend completo, todas las carpetas | grep findings |
| Encontrar tests relacionados | scanner-agent | haiku | Ruta + nombre test | VALIDATION.md, TASK_STATE.md | find + listar |
| Entender flujo antes de tocar código | scanner-agent | haiku | Evita lectura masiva |
| Renombrar variables locales | cleanup-agent | haiku | Mecánico y bajo riesgo |
| Mejorar nombres de funciones privadas | cleanup-agent | haiku | Bajo riesgo si no cambia contratos |
| Eliminar comentarios obvios | cleanup-agent | haiku | Limpieza simple |
| Traducir comentarios útiles a español | cleanup-agent | haiku | Tarea textual simple |
| Eliminar imports no usados | cleanup-agent | haiku | Mecánico |
| Ordenar código sin cambiar lógica | cleanup-agent | haiku | Bajo riesgo |
| Eliminar dead code con evidencia | cleanup-agent | sonnet | Puede afectar referencias |
| Crear endpoint backend | backend-agent | sonnet | Implementación normal |
| Crear DTO, schema o contract | backend-agent | sonnet | Puede afectar contrato |
| Cambiar servicio backend | backend-agent | sonnet | Requiere entender flujo |
| Cambiar validaciones backend | backend-agent | sonnet | Riesgo medio |
| Cambiar repositorio/persistencia simple | backend-agent | sonnet | Riesgo medio |
| Persistencia crítica o migración | architecture-agent | opus | Riesgo alto |
| Crear tests unitarios simples | qa-agent | sonnet | Requiere criterio técnico |
| Arreglar tests fallidos simples | qa-agent | sonnet | Diagnóstico técnico |
| Crear golden tests | qa-agent | sonnet | Protege comportamiento |
| Validar regresiones numéricas | qa-agent | sonnet/opus | opus si hay paridad crítica |
| Revisar arquitectura de módulos | architecture-agent | opus | Decisión estructural |
| Diseñar refactor transversal | architecture-agent | opus | Alto riesgo |
| Cambiar límites de dominio | architecture-agent | opus | Puede romper diseño |
| Revisar seguridad | security-agent | opus | Alto impacto |
| Revisar production readiness | security-agent | opus | Análisis estricto |
| Auth, roles, permisos o secretos | security-agent | opus | Riesgo alto |
| CORS, uploads o logs sensibles | security-agent | opus | Seguridad operacional |
| Docker simple | infra-agent | sonnet | Infra normal |
| docker-compose simple | infra-agent | sonnet | Infra normal |
| Terraform, Azure, RBAC, App Service o CI/CD | infra-agent | sonnet/opus | opus si afecta prod o seguridad |
| Cosmos DB configuration o Key Vault | infra-agent | sonnet/opus | opus si afecta persistencia |
| Optimización de costos Azure | infra-agent | sonnet | Análisis medio |
| Excel, fórmulas, pricing o NEXA | business-rules-agent | opus | Alta precisión |
| Paridad Excel/backend | business-rules-agent | opus | Fuente canónica |
| Paridad Excel V2-8 / differences / findings.csv | business-rules-agent | opus | Leer `docs/refactor/excel_v28/findings.csv` antes de modificar |
| Traducción puntual de fórmula Excel a backend | backend-agent | sonnet | Mantener comentario de trazabilidad Excel en código |
| Inventario, grep, búsqueda de referencias en paridad | scanner-agent | haiku | No modificar código salvo instrucción explícita |
| Drift de parámetros o golden values | business-rules-agent | opus | No permitir hacks |
| UI, formularios o frontend | frontend-agent | sonnet | Implementación normal |
| Documentación simple | docs-agent | haiku | Bajo costo |
| Reporte técnico con evidencia | docs-agent | sonnet | Síntesis técnica |
| Resumen ejecutivo | docs-agent | haiku | Texto breve |
| Revisión final de diff | reviewer-agent | sonnet | Validación de alcance |
| Revisión final de seguridad/arquitectura | reviewer-agent | opus | Riesgo alto |

---

## Tareas NEXA — contexto mínimo optimizado

| Tarea | Worker | Modelo | Leer mínimo | NO leer | Validación |
|---|---|---|---|---|---|
| Inventario / grep / referencias | scanner-agent | haiku | Archivos encontrados por grep | backend completo, Excel, histórico | grep results |
| Refactor mecánico (1 módulo) | backend-agent o cleanup-agent | sonnet | Módulo + tests directos | VALIDATION.md, TASK_STATE.md, Excel | pytest módulo |
| Paridad Excel V2-8 puntual | business-rules-agent | opus | findings.csv + hoja/mapa + calculador | todo Excel, backend completo | test parity específico |
| Traducción fórmula Excel→código | backend-agent | sonnet | Celda/fórmula + función + test | hojas no relacionadas, otros módulos | test puntual |
| Seguridad main/app | security-agent | opus/sonnet | app.py + security deps | módulos negocio, Excel, parametrización | smoke tests seguridad |
| Documentación puntual | docs-agent | haiku/sonnet | Docs afectados | código, Excel, tests | git diff markdown |

---

## Skills de contexto mínimo

Para tareas recurrentes, usa las skills de `docs/ai/skills/` — encapsulan contexto mínimo, reglas y validación por tipo de tarea:

| Skill | Cuándo | Archivo |
|---|---|---|
| nexa-backend-context | Endpoints, servicios, DTOs, repositorios | [skills/nexa-backend-context.md](skills/nexa-backend-context.md) |
| nexa-refactor-controlled | Refactors sin cambios funcionales | [skills/nexa-refactor-controlled.md](skills/nexa-refactor-controlled.md) |
| nexa-golden-validation | Golden tests, snapshots, paridad, RCA | [skills/nexa-golden-validation.md](skills/nexa-golden-validation.md) |
| nexa-excel-migration | Análisis de cambios Excel V2-7 → V2-8 | [skills/nexa-excel-migration.md](skills/nexa-excel-migration.md) |
| nexa-security-review | Seguridad FastAPI, production readiness | [skills/nexa-security-review.md](skills/nexa-security-review.md) |
| nexa-cosmos-integration | Cosmos DB: config, smoke tests, certificación | [skills/nexa-cosmos-integration.md](skills/nexa-cosmos-integration.md) |
| nexa-prompt-routing | Elegir worker/modelo/contexto antes de actuar | [skills/nexa-prompt-routing.md](skills/nexa-prompt-routing.md) |

Ver [docs/ai/skills/README.md](skills/README.md) para ejemplos de invocación y árbol de decisión.

---

## Workers disponibles

| Worker | Modelo | Especialidad |
|---|---|---|
| coordinator-agent | sonnet | Clasificación y routing de tareas |
| scanner-agent | haiku | Exploración read-only del repo |
| cleanup-agent | haiku | Limpieza sin cambios de comportamiento |
| backend-agent | sonnet | APIs, servicios, DTOs, repositorios |
| qa-agent | sonnet | Tests, golden, regresiones |
| architecture-agent | opus | Diseño, refactor, DI, límites de dominio |
| security-agent | opus | Seguridad, producción, auth, secretos |
| infra-agent | sonnet | Docker, Terraform, Azure, Cosmos DB, CI/CD |
| business-rules-agent | opus | Excel, pricing, paridad numérica |
| frontend-agent | sonnet | UI, formularios, estado |
| docs-agent | haiku | Documentación, ADRs, reportes |
| reviewer-agent | sonnet | Revisión final de diff |
