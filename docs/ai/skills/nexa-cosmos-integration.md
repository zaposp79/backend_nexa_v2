# Skill: nexa-cosmos-integration

## When to use

Tareas relacionadas con Cosmos DB: configurar el provider, ejecutar smoke tests de integración, validar concurrencia/ETag, revisar particiones, o verificar que la integración preparada funciona contra un Cosmos real.

**Riesgo esperado: alto** — operaciones contra Cosmos de staging/producción son irreversibles; una configuración incorrecta puede afectar datos compartidos.

## When not to use

- Tareas con `DB_PROVIDER=json` (default local) — no requieren esta skill.
- Tareas de negocio o fórmulas sin relación a persistencia.
- Infraestructura Azure (Terraform, RBAC) — usa `infra-agent`.

## Context to read first

1. `CLAUDE.md` — sección "Capa de persistencia (`db/`)" y variables de entorno `COSMOS_*`.
2. `db/container.py` — root de inyección, construcción del `DocumentStore`.
3. Provider de Cosmos en `db/` (importación diferida de `azure-cosmos`).
4. Tests marcados `@pytest.mark.cosmos_integration` en `tests/`.

**No leer por defecto:** calculadores, fórmulas, parametrizaciones frozen, tests golden.

## Operating rules

1. **Distinguir integración preparada vs certificada:**
   - **Preparada**: el código tiene el provider implementado pero no ha sido ejecutado contra Cosmos real.
   - **Certificada**: el provider fue ejecutado con `COSMOS_ENDPOINT` y `COSMOS_KEY` reales y los smoke tests pasaron.
2. No afirmar certificación real sin haber ejecutado con credenciales reales.
3. **Particiones**: respetar la separación GN/HR/OP/business_rules al leer/escribir documentos. No mezclar particiones.
4. **ETag y concurrencia**: validar ETag en operaciones de update cuando el provider lo soporte. Documentar si no está implementado.
5. No modificar contratos de persistencia (`DocumentStore`, `ResultsRepository`, `TraceabilityRepository`) sin pruebas de integración.
6. Smoke tests marcados `cosmos_integration` son la única evidencia válida de certificación — no se puede afirmar que funciona solo leyendo el código.
7. `ALLOW_COSMOS_NON_PRODUCTION=true` solo para testing controlado, nunca en ambientes compartidos.
8. `azure-cosmos` debe importarse de forma diferida (no en el módulo principal) para evitar dependencia en flujo `DB_PROVIDER=json`.

## Forbidden actions

- Cambiar `DB_PROVIDER` default de `json` a `cosmos` sin configuración explícita.
- Importar `azure-cosmos` en `app.py` o en módulos del flujo principal.
- Afirmar que la integración Cosmos está certificada sin evidencia de ejecución real.
- Modificar la estructura de particiones sin análisis de impacto en datos existentes.
- Ejecutar operaciones destructivas contra Cosmos de producción durante un smoke test.

## Validation

```bash
# Ejecutar smoke tests (requiere credenciales reales)
DB_PROVIDER=cosmos \
COSMOS_ENDPOINT=<endpoint> \
COSMOS_KEY=<key> \
COSMOS_DATABASE=<db> \
COSMOS_CONTAINER=<container> \
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m cosmos_integration -v

# Verificar que el flujo json no importa azure-cosmos (ejecutar desde directorio padre)
PYTHONPATH=$(pwd) python -c "import backend_nexa.app; print('OK')"  # sin DB_PROVIDER=cosmos

# Health check con Cosmos activado
APP_ENV=development DB_PROVIDER=cosmos \
  COSMOS_ENDPOINT=<endpoint> COSMOS_KEY=<key> \
  python -m backend_nexa.app
curl http://localhost:8000/health
```

## Final response format

```md
## Resultado
## Evidencia
## Riesgo
## Validación
## Siguiente paso
```

Indicar siempre: `DB_PROVIDER` usado en la validación, si las credenciales eran reales o mock, y si el resultado es "preparado" o "certificado".

---

**Ejemplo de invocación:**

```
Usando la skill nexa-cosmos-integration:
Verificar que el DocumentStore con DB_PROVIDER=cosmos funciona contra
el endpoint de staging.
Ejecutar smoke tests cosmos_integration.
No modificar contratos de persistencia.
Reportar si la integración queda como "preparada" o "certificada".
```
