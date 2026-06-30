# Quick Start — Flujo de trabajo diario

Referencia rápida para empezar una sesión de trabajo. Copiar y pegar.

---

## 0. Al iniciar sesión

```bash
# Navega a la raíz del repo
cd /Users/darwin.minota.quinto/Projects/NEXA

# Activa el venv
source backend_nexa/venv/bin/activate

# Lee el estado actual
cat backend_nexa/docs/ai/TASK_STATE.md  # ¿Qué está en progreso?

# Verifica qué cambió desde último commit
cd backend_nexa && git status
git diff --name-only
```

---

## 1. Revisar código (sin cambios aún)

### Ver cambios pequeños (< 100 líneas)

```bash
git diff  # Muestra exactamente qué cambió

# ❓ ¿Parece correcto? 
# → Avanzar a "Ejecutar tests"
# → O lanzar: reviewer-agent para revisar el diff
```

### Ejecutar tests (lo primero siempre)

```bash
# Prueba rápida de parity + baseline (2 min aprox)
PYTHONPATH=$(pwd) pytest tests/ -m "parity or baseline" -q

# Si PASSED → código está bien (o el error es existente)
# Si FAILED → hay un problema real
```

### Si fallan tests

```bash
# Ver cuál test falló exactamente
PYTHONPATH=$(pwd) pytest tests/path/al/test_que_falló.py -v

# Analizar el error
# → Si es en lógica de negocio: business-rules-agent
# → Si es en API/validación: backend-agent
# → Si es en tests: qa-agent
```

---

## 2. Corregir código existente

### Bugfix simple (1-2 archivos)

```bash
# 1. Reproduce el bug
PYTHONPATH=$(pwd) pytest tests/test_que_falla.py::test_name -v

# 2. Lanza worker
# → Copiar paso por paso de CODE_REVIEW_WORKFLOW.md sección "2.A"

# 3. Valida post-fix
PYTHONPATH=$(pwd) pytest tests/test_que_falla.py::test_name -v
# ✅ PASSED

# 4. Verifica no rompiste nada más
PYTHONPATH=$(pwd) pytest tests/ -m "parity or baseline" -q
# ✅ PASSED

# 5. Commit
git add -A
git commit -m "fix: [módulo] descripción corta
Causa: ...
Tests: ... PASSED

Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"
```

### Dead code cleanup

```bash
# 1. Verifica que nada lo usa
grep -r "nombre_funcion_vieja" backend_nexa --include="*.py"
# → Si solo aparece donde se define: dead code ✅

# 2. Lanza cleanup-agent
# → Copia de CODE_REVIEW_WORKFLOW.md sección "2.B"

# 3. Valida
PYTHONPATH=$(pwd) pytest tests/ -m "parity or baseline" -q
# ✅ PASSED

# 4. Commit
git add -A
git commit -m "cleanup: elimina [función/archivo]
Evidencia: grep confirma 0 referencias
Tests: ... PASSED

Co-Authored-By: Claude Haiku <noreply@anthropic.com>"
```

### Refactor (cambiar sin alterar lógica)

```bash
# 1. Captura baseline ANTES
PYTHONPATH=$(pwd) pytest tests/ -m baseline -q > /tmp/before.txt

# 2. Lanza cleanup-agent o architecture-agent
# → Copia de CODE_REVIEW_WORKFLOW.md sección "2.C"

# 3. Compara baseline DESPUÉS
PYTHONPATH=$(pwd) pytest tests/ -m baseline -q > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt
# → Diferencia debe ser solo time, no test names

# 4. Si todo igual → Commit
git add -A
git commit -m "refactor: [módulo] [razón: nombres/estructura/legibilidad]
Cambios: ...
Baseline: PASSED (sin drift)

Co-Authored-By: Claude [Model] <noreply@anthropic.com>"
```

---

## 3. Aplicar código NUEVO

### Nuevo endpoint

```bash
# 1. Lee el diseño esperado
cat docs/ai/CODE_REVIEW_WORKFLOW.md  # Sección "3.A"

# 2. Lanza workers
# → architecture-agent para diseño
# → backend-agent para implementación + DTOs
# → qa-agent para tests

# 3. Escribe test PRIMERO (TDD)
mkdir -p backend_nexa/tests/integration/
cat > backend_nexa/tests/integration/test_nuevo.py << 'EOF'
import pytest
from fastapi.testclient import TestClient

def test_nuevo_endpoint(client: TestClient):
    response = client.post("/api/v1/nuevo/endpoint", json={...})
    assert response.status_code == 200
    assert response.json()["success"] is True
EOF

# 4. Implementa código hasta que test pase
# → Lanzar backend-agent

# 5. Valida
PYTHONPATH=$(pwd) pytest tests/integration/test_nuevo.py -v
# ✅ PASSED

PYTHONPATH=$(pwd) pytest tests/ -m "parity or baseline" -q
# ✅ PASSED

# 6. Prueba manual
python -m backend_nexa.app &
curl http://localhost:8000/api/v1/nuevo/endpoint -X POST -d '...'

# 7. Commit
git add -A
git commit -m "feat: nuevo endpoint [ruta]
Descripción: ...
Tests: ... PASSED

Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"
```

### Nueva fórmula / cálculo (⚠️ CRÍTICO)

```bash
# 1. ANTES de tocar código: verifica el Excel
# NexaPricing_Simulador.xlsx → ¿Dónde está la fórmula? ¿Cuáles son inputs/outputs?

# 2. Lanza business-rules-agent (SIEMPRE OPUS para fórmulas)

# 3. Escribe test golden PRIMERO
cat > backend_nexa/tests/golden/test_formula_nueva.py << 'EOF'
def test_formula_nueva_golden(engine, solicitud_caso_1):
    result = engine.calcular(solicitud_caso_1)
    assert result.kpis.formulanueva == 12345.67  # Excel value
EOF

# 4. Implementa calculadora hasta que test pase

# 5. Ejecuta parity completa
cd backend_nexa && make validate-excel
# → Delta debe ser ~0

# 6. Valida todas las suite
PYTHONPATH=$(pwd) pytest tests/ -m "parity or baseline" -v

# 7. Commit
git add -A
git commit -m "feat: calculadora nueva [nombre]
Fórmula: Excel K167 = ...
Inputs: ...
Parity: 0 delta ✅
Tests: ... PASSED

Co-Authored-By: Claude Opus <noreply@anthropic.com>"
```

---

## 4. Ciclo de una sesión típica

```
INICIO
  ├─ git status  → ¿Qué hay sin commit?
  ├─ docs/ai/TASK_STATE.md  → ¿Qué estaba en progreso?
  ├─ PYTHONPATH=$(pwd) pytest tests/ -m "parity or baseline" -q  → baseline OK?
  │
  ├─ [ Si hay cambios sin commit ]
  │  ├─ git diff  → revisar qué son
  │  ├─ Decidir: ¿fix? ¿cleanup? ¿feature? ¿refactor?
  │  ├─ Lanzar worker correspondiente (ver ROUTING_MATRIX.md)
  │  └─ Ejecutar tests → Commit si PASSED
  │
  ├─ [ Si tarea nueva ]
  │  ├─ Leer CODE_REVIEW_WORKFLOW.md sección 3.X
  │  ├─ Diseñar → Lanzar architecture-agent
  │  ├─ Implementar → Lanzar worker especializado
  │  ├─ Tests → Lanzar qa-agent
  │  └─ Validar → Commit si PASSED
  │
  ├─ Actualizar docs/ai/TASK_STATE.md (qué se hizo, próximo paso)
  └─ FIN
```

---

## 5. Comandos más útiles (copiar)

```bash
# === TESTS ===
# Rápido: parity + baseline (2 min)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q

# Completo: parity + baseline + golden
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -v

# Un archivo specific
PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test_file.py -v

# Un test específico
PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test_file.py::test_name -v

# === API LOCAL ===
# Levantar servidor
python -m backend_nexa.app

# En otra terminal: probar endpoint
curl http://localhost:8000/api/v1/simulation/calculate \
  -X POST \
  -H "Content-Type: application/json" \
  -d @backend_nexa/test_cases/request.json

# === GIT ===
# Ver cambios sin commit
git diff

# Ver archivos sin commit
git status

# Ver commits no pusheados
git log origin/HEAD..HEAD --oneline

# Commit con template
git add -A
git commit -m "feat/fix/refactor: [módulo] descripción

Detalles si es importante.

Co-Authored-By: Claude [Model] <noreply@anthropic.com>"

# === UTILS ===
# Limpiar cache de tests
rm -rf backend_nexa/__pycache__ tests/__pycache__ backend_nexa/.pytest_cache/

# Limpiar storage (JSON local)
rm -rf backend_nexa/storage/

# Ver logs del último commit
git show --stat

# Ver diferencias vs main
git diff main...HEAD
```

---

## 6. Antes de cada commit

```bash
# ✅ Checklist rápida
[ ] tests -m "parity or baseline" PASSED?
    → PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q
    
[ ] Tests del módulo PASSED?
    → PYTHONPATH=$(pwd) pytest backend_nexa/tests/integration/ -q
    
[ ] Si hay API: probada manual?
    → curl http://localhost:8000/api/v1/[nuevo_endpoint]
    
[ ] Si hay fórmula: parity = 0?
    → cd backend_nexa && make validate-excel
    
[ ] Mensaje commit claro?
    → git commit -m "feat/fix/refactor: ..."
    
[ ] docs/ai/TASK_STATE.md actualizado?
    → cat docs/ai/TASK_STATE.md
    
[ ] Sin secrets, imports _privados, paths hardcodeados?
    → git diff HEAD~1 | grep -E "KEY=|_from|Path.cwd"
```

---

## 7. Si algo se rompe

```bash
# Tests fallan pero no sabes por qué
PYTHONPATH=$(pwd) pytest backend_nexa/tests/test_que_falla.py -vvv --tb=long

# Storage corrupto (JSON local)
rm -rf backend_nexa/storage/
# API se reinicia automáticamente y regenera

# Imports rotos (módulos no encontrados)
PYTHONPATH=$(pwd) python -c "from nexa_engine.modules.x import Y"
# Si falla → hay un import roto

# Volver a baseline
git diff HEAD~1  # Ver qué cambió
git reset --hard HEAD~1  # Revertir último commit
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q
# Debe pasar

# Ver qué cambios rompieron tests
git log --oneline | head -5  # Ver últimos 5 commits
git diff [commit_anterior]..[commit_nuevo]  # Comparar
```

---

## 8. Workers a lanzar (quick reference)

| Necesito... | Worker | Comando |
|---|---|---|
| Revisar diff | reviewer-agent | "Revisa cambios en [archivo]" |
| Arreglar bug | backend-agent / qa-agent / business-rules-agent | Según el módulo |
| Eliminar código muerto | cleanup-agent | "Elimina [función/archivo] con evidencia" |
| Diseñar feature | architecture-agent | "Diseña [qué]" |
| Implementar endpoint | backend-agent + qa-agent | "Crea endpoint POST [ruta]" |
| Implementar fórmula | business-rules-agent | "Implementa calculadora [nombre]" |
| Documentar | docs-agent | "Documenta [qué]" |
| Revisar seguridad | security-agent | "Audita seguridad de [área]" |

---

## 9. Archivos importantes (memoriza paths)

```
backend_nexa/
  app.py                         ← API factory
  modules/calculator/engine.py   ← Motor de cálculo (Composition Root)
  modules/shared/responses.py    ← ApiResponse (todas las respuestas)
  modules/shared/exceptions.py   ← Excepciones de dominio
  db/container.py               ← Inyección de persistencia
  api/v1/router.py              ← Agrega todos los routers
  
docs/ai/
  CLAUDE.md                      ← Buenas prácticas + arquitectura
  PROJECT_CONTEXT.md             ← Stack, módulos, convenciones
  TASK_STATE.md                  ← Estado actual (LEER PRIMERO)
  VALIDATION.md                  ← Comandos y gates
  ROUTING_MATRIX.md              ← Tarea → Worker → Modelo
  CODE_REVIEW_WORKFLOW.md        ← Este documento (detallado)
  QUICK_START.md                 ← Este documento (rápido)
```
