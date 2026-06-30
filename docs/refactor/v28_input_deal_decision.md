# Decisión de negocio requerida — Deal de referencia V2-8

## Resumen ejecutivo

El plan V2-8 está bloqueado en la validación de paridad numérica porque
el deal cargado en `request/request.json` no coincide con el deal del
Excel V2-8 de referencia. Ningún cambio técnico posterior (Stage 2 T1,
Stage 2 T2, Stage 3) puede validarse sin resolver este mismatch.

**Esta es una decisión de producto / negocio, no técnica.**

## Estado del mismatch

| Campo | Valor en `request.json` actual | Valor en Excel V2-8 |
|-------|-------------------------------|---------------------|
| servicio | Cobranzas | SAC |
| cliente | Bancamia | METROCUADRADO COM SAS |
| tipo_cliente | No Grupo Aval | Grupo Aval |

El parity runner reporta `INPUT_DEAL_MISMATCH` con estos 3 campos como
causa raíz. Ver `reports/v28_parity_runner.md`.

> Nota: las anclas P&G del cache V2-8 retornan 0.00 (Visión P&G!C26/C31/C40/C44/C65/C75)
> porque el Excel cacheado corresponde a otro deal; la comparación numérica
> es informativa, no un veredicto de paridad.

## Opciones de decisión

### Opción A — Mantener deal actual (Cobranzas / Bancamia / No Grupo Aval)

**Implica:**
- El Excel V2-8 deja de ser fuente de verdad numérica para validación.
- Stage 2 Target 1 y Target 2 no se pueden validar contra Excel.
- Se requiere recalcular Excel V2-8 con el deal actual o renunciar a la
  paridad numérica.
- Los 42 goldens actuales (basados en deal actual) siguen siendo válidos.

**Apto si:**
- El deal actual es el que se usa en producción.
- El Excel V2-8 es solo referencia de fórmulas, no de números.

### Opción B — Adoptar deal V2-8 (SAC / METROCUADRADO / Grupo Aval)

**Implica:**
- `request/request.json` debe reemplazarse con el deal V2-8 completo
  (no solo los 3 campos identificados).
- Los 63 goldens deben regenerarse contra el nuevo deal.
- Stage 2 Target 1 y Target 2 se pueden validar directamente contra
  Excel V2-8.
- Se pierde el baseline numérico del deal actual.

**Apto si:**
- El Excel V2-8 representa el deal canónico futuro.
- La paridad numérica con Excel es objetivo primario.

### Opción C — Mantener ambos en paralelo

**Implica:**
- Crear `request/request_v28.json` con el deal V2-8.
- Mantener `request/request.json` con el deal actual.
- Duplicar el parity runner para validar ambos.
- Goldens duplicados: `tests/golden/current/` y `tests/golden/v28/`.

**Apto si:**
- Ambos deals son relevantes a largo plazo.
- El costo de mantener dos baselines es aceptable.

## Recomendación técnica

(El agente NO recomienda. Solo expone implicancias. La decisión es del
stakeholder de negocio.)

## Pregunta para el stakeholder

¿Cuál es el deal canónico de referencia para validación de paridad V2-8?

- [ ] Opción A — Deal actual (Cobranzas / Bancamia)
- [ ] Opción B — Deal V2-8 Excel (SAC / METROCUADRADO)
- [ ] Opción C — Ambos en paralelo
- [ ] Otra — describir

## Próximos pasos según decisión

| Decisión | Acción técnica resultante |
|----------|----------------------------|
| A | Recalcular Excel V2-8 con deal actual o renunciar a paridad numérica |
| B | Reemplazar `request.json` + regenerar 63 goldens + retomar Stage 2 T1/T2 |
| C | Crear infraestructura de doble validación + duplicar goldens |

Ninguna opción se ejecuta hasta que el stakeholder responda.
