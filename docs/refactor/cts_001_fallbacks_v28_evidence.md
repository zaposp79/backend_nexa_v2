# CTS-001 Fallbacks — Diagnóstico V2-8

**Fecha:** 2026-06-11  
**Scope:** Auditoría de fallbacks HR-AutRot y OP-Config en relación al delta CTS-001 de 525.07 COP/tx

---

## Conclusión principal

**Los fallbacks HR-AutRot y OP-Config NO son la causa del delta CTS-001.**

`request/request.json` provee overrides explícitos que el engine usa ANTES de consultar al provider:
- `datos_operativos.pct_rotacion = 0.0815` → match exacto con Excel V2-8 `Panel de Control General!B19`
- `datos_operativos.pct_ausentismo = 0.065` → match exacto con Excel V2-8 `Panel de Control General!B18`
- `datos_operativos.cons_costo_de_financiacion = False` → Excel `Panel!B20 = 'No'` (financiación desactivada)

El provider es invocado (y devuelve los fallbacks), pero `context_builder.py` (líneas 134-138) usa el override del usuario primero.

---

## Fallback 1: HR-AutRot (rotacion/ausentismo)

| Fuente | Existe | Rotación | Ausentismo | Observación |
|--------|--------|----------|------------|-------------|
| Excel V2-8 `Rot, Ausent y Rentabilidad` | sí | 0.077175 (SAC avg 4m) | 0.081975 (SAC avg 4m) | Datos históricos por línea |
| Excel V2-8 `Panel de Control General!B18-19` | sí | 0.0815 | 0.065 | **Valores reales usados en cálculo** |
| HR productiva activa (`6506b1fa...`) | no | — | — | No tiene sección `rotacion_ausentismo` |
| OP-Costo global (fallback) | sí | 0.09 | 0.07 | Solo se usa si provider no tiene override |
| `request.json` override | sí | **0.0815** | **0.065** | Override de usuario; coincide con Panel Excel |

**Estado: HR_AUTROT_NOT_BLOCKING_CTS001**

El fallback OP-Costo (0.09/0.07) es devuelto por el provider pero ignorado por el engine porque el request tiene valores explícitos. El provider log muestra WARNING `HR-AutRot missing, using OP-Costo global fallback=0.0900/0.0700` pero estos valores no llegan al cálculo CTS.

La hoja `Rot, Ausent y Rentabilidad` contiene datos históricos de 4 meses pero NO es la fuente que alimenta la hoja `Nomina Loaded`. La fuente real es `Panel de Control General!B18-B19`.

---

## Fallback 2: OP-Config (tasa_financiacion)

| Fuente | Existe | Campo | Valor | Observación |
|--------|--------|-------|-------|-------------|
| Excel V2-8 `Pólizas - Costo Financiacion` | N/A | Se considera costo de financiación | 'No' | **Financiación desactivada** |
| Active OP storage (`14da70ab...`) | no | OP-Config sheet | — | Sheets: OP-LV, OP-OPEXFijo, OP-HardSoft, OP-DispositivoRequerido, OP-Componente, OP-ComponenteAcumulado, OP-Poliza, OP-PolizaFija, OP-ICA, OP-Costo, OP-MargenObjetivo — no OP-Config |
| Hardcoded default | sí | tasa_financiacion_mensual | 0.0088 | Usado porque OP-Config ausente |

**Estado: OP_CONFIG_NOT_BLOCKING_CTS001**

`cons_costo_de_financiacion = False` en request.json y `'No'` en Excel → el componente financiero es cero en ambos. `tasa_financiacion` no impacta CTS-001.

---

## Impacto en CTS-001

| Estado | Delta | % |
|--------|-------|---|
| Antes (post ed07c42 + 22df2dd) | 525.07 COP/tx | 8.4354% |
| Después de investigación fallbacks | 525.07 COP/tx | 8.4354% — UNCHANGED |

**Los fallbacks no son la causa.** La hipótesis original era incorrecta.

---

## Causa real del delta CTS-001 (8.44%)

Aún por determinar. Candidatos a investigar en siguiente sesión:

1. **Diferencias de salario por cargo en HR V2-8 vs V2-7** — el provider activo tiene valores de HR_productiva_2026-06-10, no del Excel V2-8. La estructura de salarios (HR `nomina`, `salarios`, `prestaciones`) puede diferir.

2. **Diferencias en estructura de perfiles** — `condiciones_cadena_a.perfiles` en request.json puede no coincidir exactamente con la configuración asumida en Excel V2-8.

3. **Costo fijo mensual** — desglose de `costo_fijo_mensual` dentro de `NominaCalculator` puede tener gaps vs Excel `Costo Fijo` o `Nomina Loaded`.

**Diagnóstico siguiente:** Comparar valor de `costo_fijo_mensual_cadena_a` entre backend y Excel `Nomina Loaded` o `Costo Fijo` para identificar el componente con mayor divergencia.

---

## Gates

- `tests/golden/test_cts_001_v28.py` — 2/2 PASS (50% tolerance, unaffected)
- Full formula runner `Vision Cost To Serve:C34` — FORMULA_PARITY_FAIL, delta=525.07 (unchanged)
- `make all` — PASS (no regression)
