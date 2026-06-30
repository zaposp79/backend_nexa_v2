# Decisions

Registra decisiones técnicas relevantes. No incluir logs ni outputs completos.

Formato:
```
Fecha:
Decisión:
Motivo:
Alternativas descartadas:
Riesgo:
Validación:
```

---

**2026-06-06**
Decisión: Alias `nexa_engine` → `backend_nexa` via `sys.modules` en `__init__.py`.
Motivo: Permite importar como `nexa_engine.*` en todo el código interno sin depender del nombre del directorio. Facilita rename futuro sin tocar imports.
Alternativas descartadas: Renombrar el directorio (requería cambios masivos), usar symlink (frágil en CI).
Riesgo: Uvicorn debe usar siempre `backend_nexa.app:create_app` (módulo canónico real). El alias falla en subprocesses de reload si se usa `nexa_engine.app`.
Validación: Tests pasan. Hot reload funciona con módulo canónico.

---

**2026-06-06**
Decisión: `DB_PROVIDER=json` como default. Cosmos es opt-in via variable de entorno.
Motivo: Elimina dependencia de `azure-cosmos` del flujo principal. La app arranca sin credenciales ni red.
Alternativas descartadas: Cosmos como default (requiere credenciales siempre), SQLite (cambio de contrato de persistencia).
Riesgo: Tests `cosmos_integration` requieren instalación manual del paquete.
Validación: `DB_PROVIDER=json` — app arranca y persiste en `storage/`. Cosmos — requiere `COSMOS_*` explícito.

---

**2026-06-06**
Decisión: Composition Root de DI en `engine.py` (`_construir_calculadores`) y `db/container.py` (`build_container`).
Motivo: Ningún calculador ni repositorio instancia sus dependencias. Facilita tests con mocks.
Alternativas descartadas: Service Locator (acoplamiento global), DI framework (overhead innecesario).
Riesgo: Agregar nuevos calculadores requiere modificar `_construir_calculadores` explícitamente.
Validación: Tests unitarios inyectan `MockParametrizationProvider` sin cambios en el motor.

---

**2026-06-06**
Decisión: `docs_enabled=False` en `APP_ENV=production`. Swagger/OpenAPI desactivados.
Motivo: Evitar exposición accidental de la API en producción.
Alternativas descartadas: Auth en /docs (más complejo, no necesario).
Riesgo: Developers necesitan `APP_ENV=development` para acceder a /docs localmente.
Validación: `APP_ENV=production` → `/docs` devuelve 404.
