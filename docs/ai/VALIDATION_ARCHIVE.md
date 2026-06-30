# Archivo de Validaciones Históricas

**Ubicación real:** `docs/ai/VALIDATION.md` (1072 líneas)

**Propósito:** Registro histórico de validaciones ejecutadas. No necesita leerse en cada sesión.

---

## Cuándo leer VALIDATION.md

### ✅ SÍ leer VALIDATION.md si:
1. Debugueas un error similar al documentado
2. Necesitas entender qué fue validado en una fase pasada
3. Buscas un comando de validación específico
4. Requieres evidencia histórica para un cambio

### ❌ NO leer VALIDATION.md si:
1. Estás haciendo una tarea puntual (grep, refactor, documental)
2. Trabajas en una nueva feature
3. Solo necesitas compilar/correr tests
4. Ejecutas validación mínima suficiente para tu cambio

---

## Cómo acceder al histórico

### Lectura selectiva (recomendado)
```bash
# Buscar validación de una fase específica
grep -A 50 "FORMULA_REFACTOR_PHASE10" docs/ai/VALIDATION.md | head -30

# Ver resultado de una fecha
grep "2026-06-06" docs/ai/VALIDATION.md

# Extraer command de validación
grep "pytest.*parity" docs/ai/VALIDATION.md | head -1
```

### Si necesitas el archivo completo
```bash
# Leerlo completo (última opción)
less docs/ai/VALIDATION.md
```

---

## Estructura del VALIDATION.md

Cada fase tiene:
1. **Scope** — qué se validó
2. **Test Results** — comandos ejecutados + resultados
3. **Validation Results** — tabla de métricas
4. **Total** — resumen de pass/fail

Ejemplo de búsqueda:
```bash
grep "### Scope:" docs/ai/VALIDATION.md | wc -l
# Muestra cuántas fases validadas
```

---

## Validación mínima para nuevas tareas (SIN leer VALIDATION.md)

| Tarea | Validación mínima |
|---|---|
| Cambio código | `pytest <modulo_afectado> -q` |
| Refactor | `pytest <ruta> -q` |
| Paridad puntual | `pytest tests/parity/test_<sheet>_v28.py -q` |
| Documentación | `git diff -- docs/` |
| Seguridad | `pytest backend_nexa/tests/security/ -q` |

---

## Integración con CI/CD

Si CI/CD necesita histórico de validaciones:
1. Versionar `VALIDATION.md` (actual: parte de repo)
2. Buscar por fecha: `git log -p docs/ai/VALIDATION.md | grep "2026-06-"`
3. O mantener en rama separada de archivo

---

## Política de actualización

**VALIDATION.md se actualiza cuando:**
- Completa una fase mayor (refactor, feature, paridad)
- Necesita evidencia histórica

**VALIDATION.md se IGNORA si:**
- Trabajas en tarea puntual
- Ejecutas validación mínima suficiente
- La fase ya pasó (información histórica)

---

## Comandos rápidos para validación histórica

```bash
# Últimas 3 fases validadas
grep "### Scope:" docs/ai/VALIDATION.md | tail -3

# Fases fallidas
grep "❌" docs/ai/VALIDATION.md

# Fases exitosas
grep "✅" docs/ai/VALIDATION.md | grep "PASSED"

# Búsqueda por palabra clave
grep -i "paridad\|baseline\|golden" docs/ai/VALIDATION.md

# Ver métricas totales de una fase
grep -A 20 "FORMULA_REFACTOR_PHASE10" docs/ai/VALIDATION.md | grep "PASSED\|Status"
```

---

## Conclusión

**Regla de oro:**
- Sí necesitas validar **tu cambio actual**: ejecuta pytest mínimo
- Si necesitas **contexto histórico**: grep + lectura selectiva de VALIDATION.md
- Si trabajas en **desarrollo normal**: ignora VALIDATION.md completamente

Ahorro de contexto: **No cargar VALIDATION.md automáticamente = 40 KB ahorrados por sesión**
