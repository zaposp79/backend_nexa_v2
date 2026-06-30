# Code Review & Correction Workflow

Proceso práctico para revisar código existente, corregirlo, y aplicar cambios nuevos.

---

## 1. Revisar código existente (sin cambios aún)

### Paso 1: Identificar qué revisar

```bash
# Ver cambios sin commit en la branch actual
git status

# Ver diff detallado
git diff

# Ver commits que divergen de main
git log main..HEAD --oneline
```

### Paso 2: Lanzar reviewer-agent

**Para diff pequeño (< 500 líneas):**

```
Usa reviewer-agent para revisar los cambios en [ruta/archivo.py].
Genera lista de:
- Cambios esperados vs. inesperados
- Riesgos de arquitectura o seguridad
- Impacto en tests
- Recomendación: ¿está listo para commit?
```

**Para refactor grande (> 500 líneas):**

```
Usa architecture-agent para revisar la estrategia de cambio en [módulo].
Enfócate en:
- ¿Quebranta límites de módulos?
- ¿Introduce imports circulares?
- ¿Afecta contratos públicos (DTOs, APIs)?
- ¿Hay drift vs. baseline?
```

### Paso 3: Ejecutar tests locales

```bash
# Desde el directorio padre de backend_nexa/

# Tests críticos (parity + baseline) — NUNCA deben romperse
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -v --tb=short

# Tests del módulo tocado
PYTHONPATH=$(pwd) pytest backend_nexa/tests/integration/ -v --tb=short

# Tests específicos si hay duda
PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test_file.py -v
```

---

## 2. Corregir código existente

### A. Bug en código existente

**Flujo:**

1. **Reproduce el bug**
   ```bash
   # Ejecuta el test que falla
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test.py::test_name -v
   ```

2. **Clasifica el bug**
   - ¿Es en lógica de negocio? → `business-rules-agent` + opus
   - ¿Es en API/validación? → `backend-agent` + sonnet
   - ¿Es en persistencia? → `architecture-agent` + opus
   - ¿Es en tests? → `qa-agent` + sonnet

3. **Ejecuta corrección**
   ```
   El worker lee el código, identifica la causa, aplica fix mínimo,
   ejecuta tests que debería pasar, reporta cambios.
   ```

4. **Valida**
   ```bash
   # El mismo test que fallaba ahora debe pasar
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test.py::test_name -v
   
   # Tests críticos intactos
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q
   ```

5. **Actualiza contexto**
   - Edita `docs/ai/TASK_STATE.md`: qué se arregló, riesgo, validación
   - Edita `docs/ai/VALIDATION.md` si fallos conocidos cambiaron

6. **Commit**
   ```bash
   git add -A
   git commit -m "fix: [módulo] descripción breve de la corrección
   
   Causa: descripción del bug
   Solución: qué se cambió
   Tests: especifica qué tests pasan ahora
   
   Co-Authored-By: Claude [model] <noreply@anthropic.com>"
   ```

### B. Dead code / deuda técnica

**Flujo:**

1. **Identifica dead code con evidence**
   ```bash
   # Grep para verificar que nada lo usa
   grep -r "función_vieja" backend_nexa --include="*.py" | grep -v "def función_vieja"
   
   # Si grep retorna solo la definición → dead code confirmado
   ```

2. **Lanza cleanup-agent**
   ```
   Elimina [función/archivo/import] con evidencia: 
   - grep -r confirma cero referencias
   - Tests pasan sin este código
   - Riesgo: CERO
   ```

3. **Valida**
   ```bash
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q
   ```

4. **Commit**
   ```bash
   git add -A
   git commit -m "cleanup: [módulo] elimina código muerto
   
   Código: [qué se eliminó]
   Evidencia: grep -r [búsqueda] → 0 referencias
   Tests: 101/101 PASSED
   
   Co-Authored-By: Claude Haiku <noreply@anthropic.com>"
   ```

### C. Refactor existente (cambiar sin alterar comportamiento)

**Flujo:**

1. **Captura baseline ANTES del cambio**
   ```bash
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v --tb=short > /tmp/baseline_before.txt
   
   # Guarda snapshot de outputs
   cp -r backend_nexa/storage/simulation_results /tmp/results_before/
   ```

2. **Lanza architecture-agent o cleanup-agent según el refactor**
   ```
   Refactor [archivo] para mejorar [legibilidad/nombres/estructura].
   NO cambiar comportamiento.
   Ejecutar tests después y reportar diferencias.
   ```

3. **Valida no hay drift**
   ```bash
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v --tb=short > /tmp/baseline_after.txt
   
   # Compara
   diff /tmp/baseline_before.txt /tmp/baseline_after.txt
   # Si la diferencia es solo tiempo de ejecución → OK
   # Si hay fallos → rollback
   ```

4. **Commit**
   ```bash
   git add -A
   git commit -m "refactor: [módulo] [razón: nombres, estructura, legibilidad]
   
   Cambios: [qué se refactorizó sin cambiar lógica]
   Validación: baseline PASSED (sin drift)
   Riesgo: CERO (cambio de superficie, sin lógica)
   
   Co-Authored-By: Claude [model] <noreply@anthropic.com>"
   ```

---

## 3. Aplicar código NUEVO

### A. Nuevo endpoint/servicio

**Flujo:**

1. **Lee contexto**
   ```
   - CLAUDE.md (arquitectura, buenas prácticas)
   - PROJECT_CONTEXT.md (convenciones)
   - ROUTING_MATRIX.md (worker a usar)
   ```

2. **Diseña antes de implementar**
   ```
   Lanza architecture-agent o plan para:
   - Qué capa toca (router → use case → repo → store)
   - Qué DTOs nuevos necesita
   - Qué excepciones puede lanzar
   - Qué tests protegen esto
   
   Una vez aprobado el plan → implementar
   ```

3. **Implementa con worker especificado**
   ```
   backend-agent para endpoint + DTOs + servicios
   qa-agent para tests simultáneamente
   ```

4. **Valida**
   ```bash
   # Tests nuevos pasan
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test_new_feature.py -v
   
   # Tests existentes intactos (parity + baseline)
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q
   
   # API manual
   # 1. Levantar servidor
   python -m backend_nexa.app
   # 2. Llamar endpoint nuevo
   curl http://localhost:8000/api/v1/[nuevo_endpoint] ...
   # 3. Verificar respuesta formato ApiResponse
   ```

5. **Actualiza contexto y commits**
   ```bash
   # Edita docs/ai/TASK_STATE.md: qué se agregó
   # Edita docs/ai/PROJECT_CONTEXT.md si hay nuevos módulos
   
   git add -A
   git commit -m "feat: [módulo] describe nuevo endpoint o servicio
   
   Descripción: [qué hace, para quién]
   Endpoint: POST /api/v1/[ruta]
   DTO: [nombre] en modules/[dominio]/api/dto.py
   Tests: [cantidad] tests new + [cantidad] tests existing PASSED
   
   Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"
   ```

### B. Nueva fórmula / cálculo

**Flujo — CRÍTICO, escalar a opus:**

1. **Verifica fuente canónica**
   ```
   Antes de cualquier fórmula nueva, confirmar:
   - ¿Está en el Excel NexaPricing_Simulador.xlsx?
   - ¿Cuáles son los inputs exactos?
   - ¿Cuál es el output esperado (golden value)?
   ```

2. **Lanza business-rules-agent**
   ```
   Implement calculadora nueva [Nombre] para [qué calcula].
   
   Inputs: [lista exacta de campos]
   Fórmula: [transcribe del Excel con referencias a celdas]
   Output: [DTO esperado]
   Golden test: [valor esperado del Excel]
   
   Validar con tests parity ANTES de commit.
   ```

3. **Valida contra Excel**
   ```bash
   cd backend_nexa && make validate-excel
   
   # Si hay delta > 0.5, investigar
   # Si delta = 0, ✅ PARITY OK
   ```

4. **Commit**
   ```bash
   git add -A
   git commit -m "feat: [calculadora] nuevos cálculos de [qué]
   
   Fórmula: [referencia Excel V2-7, ej. K167=...]
   Inputs: [lista de campos del PricingRequest]
   Output: [DTO creado]
   Parity: Excel vs Backend = 0 delta ✅
   Tests: [cantidad] new + parity PASSED
   
   Co-Authored-By: Claude Opus <noreply@anthropic.com>"
   ```

### C. Nueva visión / reporte

**Flujo:**

1. **Diseña estructura**
   ```
   architecture-agent para:
   - DTOs del resultado (ej. VisionNuevaDTO)
   - Builder que transforma PricingResult en VisionNuevaDTO
   - Dónde persiste (storage/simulation_results/{sim_id}?)
   - Cómo se consulta (GET /api/v1/simulation/{id}/results/[vision]?)
   ```

2. **Implementa**
   ```
   backend-agent para:
   - Builder (módule/vision_nueva/builders/)
   - Repositorio si es persistencia custom
   - Router y DTO respuesta (modules/vision_nueva/api/)
   ```

3. **Valida**
   ```bash
   # Test nuevo
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/test_vision_nueva.py -v
   
   # Baseline intacta
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -q
   
   # API manual
   curl http://localhost:8000/api/v1/simulation/{id}/results/vision-nueva
   ```

4. **Commit**
   ```bash
   git add -A
   git commit -m "feat: vision_nueva — nueva visión de [qué muestra]
   
   Módulo: modules/vision_nueva/
   Builder: transforma PricingResult → VisionNuevaDTO
   Endpoint: GET /api/v1/simulation/{id}/results/vision-nueva
   Tests: [cantidad] new + baseline PASSED
   
   Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"
   ```

---

## 4. Checklist antes de cada commit

- [ ] Tests críticos pasan: `PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q`
- [ ] Tests del módulo tocado pasan
- [ ] Si hay API nueva: probada manual con curl
- [ ] Si hay fórmula nueva: parity Excel = 0 delta (o drift documentado)
- [ ] Mensaje de commit claro: feat/fix/refactor + descripción
- [ ] `docs/ai/TASK_STATE.md` actualizado con lo que se hizo
- [ ] Si hay cambios arquitectónicos: `DECISIONS.md` actualizado
- [ ] Código sigue buenas prácticas de CLAUDE.md (sección 11, checklist)
- [ ] Sin secrets, paths hardcodeados ni imports `_privados` entre módulos

---

## 5. Workflows rápidos (copy-paste)

### Revisar + Corregir un bug pequeño

```bash
# 1. Ver qué cambió
git status

# 2. Entender el cambio
git diff

# 3. Ejecutar test fallido
PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test.py::test_name -v

# 4. Lanzar worker (reemplazar [...] con detalles reales)
# → reviewer-agent para revisar qué salió mal
# → backend-agent o qa-agent para corregir

# 5. Validar post-corrección
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q

# 6. Commit
git add -A
git commit -m "fix: [módulo] descripción corta
Causa: ...
Solución: ...
Tests: ... PASSED

Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"
```

### Agregar nuevo endpoint

```bash
# 1. Diseñar
# → Lanzar architecture-agent o plan

# 2. Implementar
# → backend-agent para código + qa-agent para tests

# 3. Crear archivo test
touch backend_nexa/tests/integration/test_nuevo_endpoint.py

# 4. Escribir test
# → qa-agent escribe test con fixtures

# 5. Validar
PYTHONPATH=$(pwd) pytest backend_nexa/tests/integration/test_nuevo_endpoint.py -v
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -q

# 6. Probar API manual
python -m backend_nexa.app &
curl http://localhost:8000/api/v1/nuevo/endpoint

# 7. Commit
git add -A
git commit -m "feat: [módulo] nuevo endpoint [ruta]
Endpoint: POST /api/v1/...
DTO: ...
Tests: ... PASSED

Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"
```

### Eliminar dead code

```bash
# 1. Verificar que nada lo usa
grep -r "nombre_funcion" backend_nexa --include="*.py"

# 2. Si solo aparece la definición → dead code
# Lanzar cleanup-agent

# 3. Validar
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q

# 4. Commit
git add -A
git commit -m "cleanup: elimina código muerto [nombre]
Evidencia: grep -r confirma 0 referencias
Tests: baseline PASSED

Co-Authored-By: Claude Haiku <noreply@anthropic.com>"
```

---

## 6. Escaladas a especialistas

| Situación | Worker | Modelo |
|---|---|---|
| Bug en fórmula de Excel → backend | business-rules-agent | opus |
| Falla de paridad Excel | business-rules-agent | opus |
| Necesario refactor de arquitectura | architecture-agent | opus |
| Security issue o credenciales | security-agent | opus |
| Tests fallan en Cosmos DB | architecture-agent + infra-agent | sonnet/opus |
| Drift vs baseline | qa-agent | sonnet/opus |

---

## 7. Contexto a actualizar SIEMPRE

**Después de cada tarea completada:**

```
docs/ai/TASK_STATE.md
  ├─ Estado actual: qué se hizo
  ├─ Último test ejecutado: qué pasó
  └─ Próximo paso: qué viene

docs/ai/VALIDATION.md
  ├─ Comandos ejecutados: copiar exactos
  ├─ Resultados: tests PASSED/FAILED
  └─ Fallos nuevos/resueltos: si hay

docs/ai/DECISIONS.md (solo si hay decisión técnica)
  ├─ Qué se decidió
  ├─ Por qué (motivo)
  └─ Riesgo/impacto
```

**Nunca actualizar:**
- `docs/ai/PROJECT_CONTEXT.md` (a menos que cambios de stack o convenciones)
- `docs/ai/ROUTING_MATRIX.md` (a menos que cambios de política de workers)
- CLAUDE.md (a menos que cambios de reglas críticas)
