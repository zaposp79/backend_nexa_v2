# Guía de Agentes — NEXA Claude Code

12 agentes especializados disponibles en `.claude/agents/`.

---

## Agentes por especialidad

### 📊 Exploración & Análisis

**scanner-agent** (haiku)
- Lectura pura, sin modificaciones
- Buscar archivos, rutas, referencias
- Entender estructura pre-cambios
- **Uso:** Inventarios, grep, pre-análisis

**coordinator-agent** (sonnet)
- Clasificación de tareas
- Routing a worker correcto
- **Uso:** Interno, raramente directo

---

### 💻 Implementación

**backend-agent** (sonnet)
- APIs, endpoints, servicios
- DTOs, repositories, persistencia
- Cambios funcionales simples
- **Uso:** Features backend, fixes API, refactor módulos

**cleanup-agent** (haiku)
- Renombrado, reordenamiento
- Limpieza sin cambios de lógica
- Imports no usados, comentarios
- **Uso:** Mantenimiento, deuda técnica

**frontend-agent** (sonnet)
- UI, formularios, estado
- Integración API frontend
- **Uso:** Cambios visuales, forms

---

### 📋 Calidad & Validación

**qa-agent** (sonnet)
- Tests unitarios, golden, regresiones
- Diagnóstico de fallos
- **Uso:** Tests, debugging, cobertura

**reviewer-agent** (sonnet)
- Revisión final de diffs
- Scope, regresión, contrato
- **Uso:** Pre-merge checklist

---

### 🏗️ Decisiones Arquitectónicas

**architecture-agent** (opus)
- Diseño modular, refactor transversal
- Límites de dominio, DI
- Decisiones de alto nivel
- **Uso:** Features complejas, arquitectura

**security-agent** (opus)
- Seguridad, auth, secrets
- Production readiness
- CORS, uploads, logs sensibles
- **Uso:** Seguridad, compliance, auditoría

**infra-agent** (sonnet/opus)
- Docker, Terraform, Azure
- CI/CD, Cosmos DB, Key Vault
- **Uso:** Infra, deployment, cloud

---

### 📈 Business Rules & Datos

**business-rules-agent** (opus)
- Excel, pricing, fórmulas
- Paridad numérica crítica
- Drift de parámetros
- **Uso:** Cambios V2-8, validación Excel, business logic

---

### 📝 Documentación

**docs-agent** (haiku/sonnet)
- Documentación técnica
- ADRs, reportes
- README, guías
- **Uso:** Docs, referencias, wikis

---

## Cuándo usar cada agente

| Tarea | Agente | Modelo | Tiempo |
|---|---|---|---|
| Buscar función X | scanner | haiku | 5 min |
| Crear endpoint | backend | sonnet | 20 min |
| Refactor variable | cleanup | haiku | 5 min |
| Arreglar test fallido | qa | sonnet | 15 min |
| Cambiar fórmula Excel | business-rules | opus | 40 min |
| Diseñar módulo nuevo | architecture | opus | 60 min |
| Revisar seguridad | security | opus | 45 min |
| Actualizar README | docs | haiku | 10 min |
| Pre-merge check | reviewer | sonnet | 20 min |

---

## Cómo invocar agentes

```bash
# Opción 1: Automático (Agent tool con subagent_type)
claude --agent backend-agent "Crea endpoint GET /foo"

# Opción 2: Directo (usar modelo + permisos)
claude --model sonnet --permission-mode plan "Refactoriza foo()"

# Opción 3: Consulta corta (sin agente)
claude -p --max-turns 3 "Dónde está función X?"
```

---

## Stack recomendado por proyecto/fase

### NEXA Backend (actual)
- scanner: inventarios pre-cambios
- backend: features, fixes, refactor
- business-rules: paridad Excel, parámetros
- qa: tests, regresiones
- reviewer: pre-merge
- architecture: decisiones grandes
- security: auditoría, producción

### Minimal (si no usas agentes)
- No necesario; usa `claude --model <X>` + permisos

---

## Política de contexto en agentes

Cada agente especializazo tiene política de ahorro:
- scanner: lee solo grep results
- backend: lee módulo + tests
- business-rules: lee findings.csv + hoja
- qa: lee tests + harness
- docs: lee docs affected

Ver `.claude/agents/` para detalles.

---

## Notas importantes

1. **No enviar agentes en paralelo** sin necesidad de coordinación
2. **Usar `--permission-mode plan`** para cambios mayores (plan → ejecución)
3. **Fallback a `claude --model X`** si no necesitas especialidad
4. **Los agentes NO cambian el stack** — solo especializan el modelo/contexto
5. **Leer `CONTEXT_SAVING_POLICY.md`** antes de invocar para minimizar contexto
