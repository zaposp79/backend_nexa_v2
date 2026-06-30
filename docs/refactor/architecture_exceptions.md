# Excepciones Arquitectónicas Aceptadas

**Fecha de decisión:** 2026-06-04 (FASE GAP-1 / GAP-2)
**Estado:** Congelado — no mover sin fase dedicada aprobada

---

## Contexto

Tras la auditoría completa de arquitectura `db/` y módulos (2026-06-04), los siguientes archivos
fueron revisados y se tomaron decisiones explícitas de conservarlos como están.

Ningún agente, script ni fase de refactorización debe modificar estos archivos sin:
1. Referenciar esta tabla.
2. Crear una fase dedicada (ORACLE-FIN, FROZEN-1, etc.).
3. Ejecutar Oracle (parity tests) tras el cambio.
4. Confirmar `Δ = 0` en Oracle.

---

## Tabla de excepciones

| Archivo | Decisión | Motivo técnico | Revisión futura |
|---|---|---|---|
| `modules/parametrizacion/services/resolver.py` | `KEEP_WITH_REASON` | El fallback `get_parametrization_store()` en `__init__` es la implementación de `get_resolver()` singleton. Eliminar el fallback requiere refactorizar el singleton de forma equivalente. La ganancia de DI sería mínima: el resultado es el mismo DocumentStore singleton. | Solo si se elimina o refactoriza `get_resolver()` |
| `modules/parametrizacion/mixins/provider_business_rules.py` | `KEEP_TEMPORARILY_WITH_REASON` | El fallback de `_load_active_business_rules()` existe para tests que instancian `ParametrizationProvider` sin container completo. El happy path de producción siempre inyecta `_br_repo` via container. Se añadió `logger.warning` para auditar si el fallback se activa en producción. | Cuando todos los tests usen container; remover fallback y hacerlo obligatorio |
| `modules/parametrizacion/repositories/frozen_parametrization_repository.py` | `KEEP_LEGACY_READ_ONLY_CONFIRMED` | **FROZEN-1 confirmó:** Los snapshots frozen son datos certificados inmutables — semánticamente diferentes del CRUD de GN/HR/OP. `DocumentStore` está diseñado para CRUD con versiones activas/inactivas; frozen no necesita esa semántica. Usar `open()` es correcto para datos inmutables. Los hashes de los 6 archivos frozen están registrados (ver abajo). Migrar a DocumentStore implicaría cambiar la serialización e invalidar los hashes de paridad. | NO migrar a DocumentStore salvo que cambie el modelo de certificación completo. |
| `modules/costos_financieros/reglas.py` | `RESOLVED` | **refactor/modular-pure:** El archivo fue eliminado y `CostosFinancierosCalculator` migrado a `modules/costos_financieros/calculators/`. Oracle confirmó `Δ = 0` post-movimiento (2026-06-04). Excepción cerrada. | N/A — resuelto |

---

## Accesos legacy aceptados en producción

| Archivo | Acceso legacy | Justificación |
|---|---|---|
| `resolver.py:50-54` | `get_parametrization_store()` en fallback `__init__` | Composition root del singleton `get_resolver()`. Equivale a lo que haría el container. |
| `provider_business_rules.py:36-37` | `get_parametrization_store()` en fallback | Safety net para tests sin container. Logger warning activo para detectar uso en producción. |
| `frozen_parametrization_repository.py:59,105` | `open()` directo | Snapshots frozen son datos inmutables certificados, no CRUD. |

---

## Lo que NO está permitido sin nueva decisión

1. ~~Mover `costos_financieros/reglas.py`~~ — **RESOLVED** (eliminado en refactor/modular-pure, 2026-06-04).
2. Migrar `frozen_parametrization_repository.py` a `DocumentStore`.
3. Eliminar el fallback de `resolver.py` sin actualizar `get_resolver()`.
4. Eliminar el fallback de `provider_business_rules.py` sin confirmar que todos los consumidores inyectan `_br_repo`.
5. Reintroducir `build_panel_parametros()` en cualquier módulo (fue eliminada en GAP-1 por dead code con 0 consumidores).

---

## Hashes de archivos frozen certificados

Registrados en FROZEN-1 (2026-06-04). Cualquier cambio en estos hashes indica modificación no autorizada.

| Archivo | payload_sha256 | Tamaño |
|---|---|:---:|
| `storage/parametrization/frozen/v2-6.json` | `98c541cefb397323...` | 2,645 B |
| `storage/parametrization/v2-7/gn.json` | `01c9482f7bc96703...` | 9,711 B |
| `storage/parametrization/v2-7/hr.json` | `7db9b3a5969af969...` | 104,656 B |
| `storage/parametrization/v2-7/op.json` | `5820a03723c398b8...` | 26,557 B |
| `storage/parametrization/v2-7/business_rules.json` | `b6868eaa05c6dc61...` | 3,464 B |
| `storage/parametrization/v2-7/manifest.json` | `c8338d96752c8e70...` | 958 B |

Los hashes completos (64 chars) están en `tests/unit/test_frozen_parametrization_integrity.py`.

---

## Guardrails activos

Los siguientes tests verifican que estas excepciones se mantienen correctamente:

```
tests/unit/test_architecture_exceptions.py
tests/unit/test_frozen_parametrization_integrity.py
```

Si algún guardrail falla, significa que se está intentando una refactorización no aprobada.
