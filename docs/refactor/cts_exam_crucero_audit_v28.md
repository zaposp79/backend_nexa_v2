# CTS-EXAM / CTS-CRUCERO — Auditoría V2-8

Fecha: 2026-06-11 · Rama: `refactor/modular-pure`  
Base: commit `1e775c5` (`CTS_SENA_INCLUSION_PROVIDER_PATCH_APPLIED`).  
Excel: `Nexa - Pricing - Simulador - V2-8.xlsx`.

---

## Estado

| Gap | Excel COP/tx | Backend antes | Backend después | Fix | Estado |
|---|---|---|---|---|---|
| CTS-EXAM | 12.241808 | 0.016 | **11.512** | `_v28_deal_provider.py` | `CTS_EXAM_APPLIED` (parcial) |
| CTS-CRUCERO | 10.629257 | 0.000 | **9.892** | `CRUCERO_REQUEST_ALIGNMENT` (request.json) | `CTS_CRUCERO_PARTIAL` |

---

## 1. Trazabilidad Excel — Exámenes

### Ruta en Excel

```
Vision CTS!C41 (Exámenes Médicos = 12.241808 COP/tx)
  = SUM(IF(Panel!M17=TRUE, NL!D373:BK373, 0)) / Panel!C11 / Panel!W31
  ↓
NL!D373:BK373  (Inbound Exámenes — 24 meses)
  sum = 64,930,552 COP → ÷24 = 2,705,440/mes → ÷221,000 = 12.2418 COP/tx
  ↓
NL!C366:C372   (costo por canal = SUMIFS en E345:E361 que mira C338:C341 × NL!C329-C331)
  NL!C329 = C330 = C331 = 60,800 COP (costo externo por examen)
                                        ← HR-Med-Seg valor 60,800
  × pct_examen_anual = 0.28             ← CCA!E135
```

### Tabla de trazabilidad

| Concepto | Celda Excel | Fórmula | Valor Excel | Destino provider | Observación |
|---|---|---|---|---|---|
| Exámenes COP/tx | `Vision CTS!C41` | SUM(NL D373:BK373)/C11/W31 | 12.241808 | — | anchor |
| Exámenes mensual | `Nomina Loaded!D373` (sum) | SUM(D366:D372) | 2,705,440 avg/mes | — | suma 24 meses |
| Costo examen médico | `Nomina Loaded!C329/C330/C331` | array formula | **60,800 COP** | `med_seg[Bogota].valor` | activo HR = 60.8 (error escala) |
| pct_examen_anual | `Condiciones Cadena A!E135` | input directo | **0.28** | `rotacion_ausentismo[SAC].pct_examen_anual` | fallback HR = 1.0 |
| Toggle exam inicial | `Condiciones Cadena A!E144` | checkbox | TRUE | — | activo en deal |
| Toggle exam rotación | `Condiciones Cadena A!E145` | checkbox | TRUE | — | activo en deal |
| Toggle exam anual | `Condiciones Cadena A!E146` | checkbox | TRUE | — | activo en deal |

### Resultado backend post-fix

| Métrica | Antes | Después | Excel | Residual |
|---|---|---|---|---|
| examenes COP/tx | 0.016 | **11.512** | 12.242 | -0.730 (5.9%) |
| CTS-001 COP/tx | 6,143.81 | **6,155.30** | 6,224.58 | -69.27 (1.113%) |

**Causa del residual -0.73:** `fte_examenes` backend (~270 FTE) < Excel efectivo (~287 FTE, incluye soporte).
Parte del `STAFFING_FTE_MISMATCH`. Requiere modules/ — fuera de scope.

---

## 2. Trazabilidad Excel — Crucero

### Ruta en Excel

```
Vision CTS!C43 (Crucero = 10.629257 COP/tx)
  = SUM(IF(Panel!M17=TRUE, NL!D479:BK479, 0)) / Panel!C11 / Panel!W31
  ↓
NL!D479:BK479  (Inbound Crucero — 24 meses, sum = 56,377,580)
  = 2,349,066/mes → ÷221,000 = 10.6293 COP/tx
  ↓
NL!E451:E453   (costo por escenario, desde FILTER en CCA!E152:T152)
  CCA!E152 = 1,193,936  (Escenario SAC Actual, mensual)
  CCA!F152 =   420,400  (WhatsApp Actual, mensual)
  CCA!G152 =   734,730  (Crecimiento inhouse, mensual)
  Total    = 2,349,066  COP/mes
```

### Tabla de trazabilidad

| Concepto | Celda Excel | Fórmula | Valor Excel | Destino backend | Observación |
|---|---|---|---|---|---|
| Crucero COP/tx | `Vision CTS!C43` | SUM(NL D479:BK479)/C11/W31 | 10.629257 | — | anchor |
| Crucero mensual SAC | `Condiciones Cadena A!E152` | input directo | 1,193,936 COP/mes | `datos_operativos.crucero` | BLOQUEADO (request.json) |
| Crucero mensual WhatsApp | `Condiciones Cadena A!F152` | input directo | 420,400 COP/mes | — | parte del total |
| Crucero mensual Crec. | `Condiciones Cadena A!G152` | input directo | 734,730 COP/mes | — | parte del total |

### Clasificación

**`CTS_CRUCERO_REQUIRES_INPUT_SCOPE`** — BLOQUEADO. *(SUPERSEDED 2026-06-11 — ver actualización abajo.)*

El backend usa `tarifa_crucero * perfil.fte * indexacion` (tasa por FTE desde Panel).
El Excel usa una suma de costos mensuales totales por escenario (desde `Condiciones Cadena A!E152:G152`).
La arquitectura backend no permite inyectar `tarifa_crucero` via provider HR/GN/OP.
La fuente (`datos_operativos.crucero` = `request.json[panel].crucero`) está fuera de scope.

Para cerrar: activar `tarifa_crucero` en request.json → `datos_operativos.crucero = 2_349_066 / FTE_total`.

> **Actualización 2026-06-11 (sesión `CTS_INPUT_DECISION_CHECKPOINT`):** reclasificado a
> **`CTS_CRUCERO_FIXABLE_WITH_REQUEST`** (NO requiere campo nuevo). Ground truth verificado:
> - `request.json` línea 13 `datos_operativos.crucero = 8408` → **SÍ presente** (mapea a
>   `tarifa_crucero` vía `user_input_loader.py:323`). La afirmación "tarifa ausente" era **falsa**.
> - `incluye_crucero` **ya existe en el contrato público** (`shared/contracts/api_v1/request/cadena_a.py:36`)
>   y está cableado per-perfil (`user_input_builders_cadena_a.py:159` → `PerfilCadenaAInput.incluye_crucero`).
> - Backend retorna 0 solo porque los perfiles no declaran `incluye_crucero: true` (default False).
> - Consistencia: `8408 × ~279 FTE ≈ 2.35M/mes` ≈ Excel 2,349,066/mes → el modelo per-FTE replica el total.
>
> Cierre = activar `incluye_crucero: true` en perfiles Cadena A de `request.json` (request-scope,
> sin contrato nuevo, sin `modules/`). Detalle: `cts_001_decision_checkpoint_v28.md` §3.

---

## 3. Backend — Tabla de estado

| Concepto | Backend file/método | Valor antes | Valor después | Causa del 0/error |
|---|---|---|---|---|
| costo_examen_medico | `provider.get_examen_medico("Bogota")` vía `HR-Med-Seg` | 60.8 | **60,800** | escala HR storage |
| pct_examen_anual | `provider.get_pct_examen_anual("SAC")` vía `HR-AutRot` | 1.0 (fallback) | **0.28** | HR-AutRot missing |
| examenes COP/tx | `_examenes(perfil, mes)` en `nomina.py` | 0.016 | **11.512** | ambos valores corregidos |
| crucero COP/tx | `_crucero(perfil, mes)` en `nomina.py` | 0.0 | 0.0 (no cambió) | tarifa_crucero=0 en request.json |

---

## 4. Commit y artefactos

- Provider patch: `tests/refactor/_v28_deal_provider.py` (med_seg + rotacion_ausentismo SAC)
- Tests: `tests/golden/test_cts_exam_crucero_v28.py` (2 golden tests: exam + crucero anchor)
- Gates: CTS golden 4/4 PASS, validate-excel-v28 6/6 PASS, make all PASS

---

## 5. Estado post-CRUCERO_REQUEST_ALIGNMENT (2026-06-11)

**Fix aplicado:** `incluye_crucero=true` en los 3 perfiles Cadena A de `request.json`.
`tarifa_crucero=8408` ya estaba presente en `datos_operativos.crucero`.

| Métrica | Antes | Después | Excel | Residual |
|---|---|---|---|---|
| crucero COP/tx | 0.000 | **9.892** | 10.629 | -0.737 (6.9%) |
| CTS-001 COP/tx | 6,155.30 | **6,165.20** | 6,224.58 | -59.38 (0.954%) |

**Residual crucero -0.737** = mismo cargos_adicionales gap del Support FTE (backend usa solo `fte_agentes`,
Excel usa `fte_agentes + cargos_adicionales` en el numerador de crucero también: `CCA!E134×(E9+E26)`).

**Próximos pasos:**
- `OPEX_REQUEST_ALIGNMENT`: reconciliar `opex_fijo.items` vs Excel "No payroll" (backend +71.95 sobre Excel).
- `CONTRACT_CHANGE_CARGOS_ADICIONALES`: única vía para cerrar el residual de Supervisor soporte y crucero.
- `CTS-002`: Cadena B gap pendiente.
