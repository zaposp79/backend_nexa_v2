> **⚠️ POST-W17 CONTEXT**: Claims of certified parity in this report
> were based on circular tests. W17 oracle validation showed the actual
> parity gap is structural. The infrastructure built in this wave is
> still valid, but the parity certification claim is rescinded until
> the Semantic Reconstruction Program completes.

# WAVE 5 — Normalización semántica + Logging estructurado + Cleanup

**Fecha**: 2026-05-27
**Branch**: `refactor/engine-v2`
**Pre-requisito**: WAVE 4 (suite paridad 39/39, 742/27/321).
**Scope**: Bloque A (canonicalización), Bloque B (logging estructurado),
Bloque C (bugs cleanup + documentación).

---

## 1. Resumen ejecutivo

| Bloque | Estado | Resultado |
|--------|--------|-----------|
| A — Canonicalización semántica | Completado | `shared/canonicalization.py` + overlay `op.json[canonicalization_aliases]`. Provider canonicaliza internamente; contrato DTO intacto. Bug #1 resuelto. |
| B — Logging estructurado | Completado | 5 tags (`PAYROLL_BUILD`, `STAFFING_BUILD`, `SCENARIO_BUILD`, `PRICING_BUILD`, `VISION_BUILD`) en archivos clave, nivel INFO, lazy formatting. |
| C — Bugs cleanup | Completado | Bug #1 resuelto. Bug #2 documentado como INTENTIONAL. Bug #4 documentado como business override permanente. Bug #5 documentado en doc dedicado. |

**Tests parity**: 39 / 39 passing (100%, sin xfail).
**Suite global**: 742 passed, 27 failed, 23 skipped, 65 xfailed, 321 errors —
**idéntico a WAVE 4**, sin regresiones.

---

## 2. Bloque A — Canonicalización semántica

### 2.1 Módulo `shared/canonicalization.py`

Funciones puras, idempotentes, sin I/O salvo un único log WARNING cuando
no hay alias.

| Función | Dimensión | Canónica |
|---------|-----------|----------|
| `canonical_service(s)` | servicios / lineas | Sac, SACO, Cobranzas, Ventas multicanal, Captura de Datos, Plataformas |
| `canonical_channel(s)` | canales | Voz, WhatsApp, Correo, WebChat, IVR, Mensajes, Otros, Fuerza de ventas |
| `canonical_role(s)` | roles HR | Supervisor, GTR, Director de cuentas, Formadores, Monitor de Calidad, ... |
| `canonical_modalidad(s)` | modalidad | Inbound / Outbound / Blended |
| `canonical_complejidad(s)` | complejidad | BAJA / MEDIA / ALTA |

Operaciones aplicadas (en orden):
1. `strip` + `lower`
2. `unicodedata.normalize("NFD", s)` → quita acentos
3. Lookup en overlay desde `op.json` (preferido)
4. Lookup en aliases built-in
5. Si no hay match → devuelve input original + log WARNING

### 2.2 Aliases definidos (extracto)

**Servicios** (canónica → variantes aceptadas):
* `Sac` ← SAC, S.A.C, S A C, Servicio al Cliente, Customer Care, Atencion al cliente
* `SACO` ← SACO, S.A.C.O, SAC+O
* `Cobranzas` ← cobranzas, Collections, Recuperaciones
* `Ventas multicanal` ← Ventas, Multicanal, Ventas multi-canal
* `Captura de Datos` ← Backoffice, Back office, Data capture
* `Plataformas` ← Platforms, Plataforma

**Canales**:
* `WhatsApp` ← whatsapp, WA, Whats App, Whats-App, WSP
* `Voz` ← voice, telefonia, phone
* `Correo` ← email, mail, e-mail
* `WebChat` ← Chat, Web chat, Chat web

**Roles**:
* `Supervisor` ← SUPERVISOR, Sup., Sup
* `GTR` ← G.T.R, gtr
* `Director de cuentas` ← Director cuentas, Account director
* `Monitor de Calidad` ← QA, Monitor calidad
* `Aprendiz SENA` ← Aprendiz

**Modalidad**: `Inbound` ← INB, IN, Entrante · `Outbound` ← OUT, OUTB, Saliente
· `Blended` ← BLD, Mixto, Mixed

**Complejidad**: `BAJA` ← Baja, B, Low · `MEDIA` ← M, Med, Medium · `ALTA` ← A, High

### 2.3 Overlay en `op.json[canonicalization_aliases]`

Se persistieron los aliases conocidos del Excel V2-7 en
`storage/parametrization/v2-7/op.json` bajo la clave nueva
`canonicalization_aliases` (sub-bloques: `services`, `channels`, `roles`,
`modalidad`, `complejidad`). El módulo los carga lazy al primer uso; los
aliases built-in funcionan como fallback inline si el overlay no está
disponible.

### 2.4 Aplicación NO invasiva en el provider

`repositories/parametrization_provider.py` aplica canonicalización en cada
método que toma `linea` / `linea_negocio` como argumento:

* `get_rampup(linea_negocio, mes)`
* `get_margen_minimo(linea_negocio)`
* `get_pct_rotacion(linea)`, `get_pct_ausentismo(linea)`, `get_pct_examen_anual(linea)`
* `get_ratios_staff(linea)`

Patrón de fallback seguro:
```python
canon = canonical_service(linea)
try:
    value = self._payroll.get_X(canon)
except ParametrizationError:
    if canon != linea:
        value = self._payroll.get_X(linea)  # fallback al original
    else:
        raise
```

El DTO sigue aceptando "SAC" / "S.A.C" / "Sac" — **no se rompe el contrato**.

Validación funcional (Bug #1):
```
>>> p.get_pct_rotacion("cobranzas") -> 0.119875
>>> p.get_pct_rotacion("SAC")       -> 0.077175
>>> p.get_pct_rotacion("S.A.C")     -> 0.077175
>>> p.get_pct_rotacion("Sac")       -> 0.077175
```

---

## 3. Bloque B — Logging estructurado

### 3.1 Formato común

```
[<TAG>] op=<operation> inputs={k:v,...} outputs={k:v,...} source=<fuente>
```

Nivel **INFO** para hitos agregados (1 por simulación), DEBUG para detalles.
Lazy formatting (`%s`) para no costar nada cuando el logger no está activo.

### 3.2 Logs agregados (archivo → tag → operación)

| Archivo | Tag | Operación | Nivel | Frecuencia |
|---------|-----|-----------|-------|-------------|
| `calculators/nomina.py` | `[PAYROLL_BUILD]` | `calcular_para_mes` | INFO | 1× por mes |
| `calculators/pyg.py` | `[PRICING_BUILD]` | `calcular_contrato` | INFO | 1× por contrato |
| `calculators/vision_tarifas.py` | `[VISION_BUILD]` | `calcular_vision_tarifas` | INFO | 1× por simulación |
| `calculators/cost_to_serve.py` | `[VISION_BUILD]` | `calcular_cost_to_serve` | INFO | 1× por simulación |
| `input/context_builder.py` | `[SCENARIO_BUILD]` | `build_escenarios` | INFO | 1× por simulación |
| `input/context_builder.py` | `[STAFFING_BUILD]` | `construir_perfiles_a` | INFO | 1× por simulación |

### 3.3 Ejemplo de log generado

```
[PRICING_BUILD] op=calcular_contrato inputs={meses:24,margen_a:0.1800,margen_b:0.3000,linea:Cobranzas} outputs={ingreso_bruto_total:5876123.45,costo_total:4521987.32,contribucion_total:1354136.13} source=Panel+CostosTotales+CostosFinancieros

[PAYROLL_BUILD] op=calcular_para_mes mes=12 inputs={perfiles:8} outputs={salario_fijo:152345.67,comisiones:8240.12,cap_inicial:1234.55,cap_rotacion:3456.78,examenes:412.50,seguridad:200.00} source=HR-Nomina+HR-Med-Seg

[VISION_BUILD] op=calcular_vision_tarifas inputs={meses:24,canales:4,factor_billing:0.770250} outputs={costo_total:188415.89,ingreso_total:244611.40,costo_a:175302.12,costo_b:13113.77,costo_c:0.00} source=PyG+Panel(margen_a)

[STAFFING_BUILD] op=construir_perfiles_a inputs={linea:Cobranzas,meses:24,pct_rotacion:0.1199} outputs={total_perfiles:9,agentes:1,soporte:8,total_fte:15} source=cadena_a.perfiles+HR-Ratios
```

### 3.4 Volumen y rendimiento

Para una simulación canónica (24 meses, 1 escenario):
* `[PAYROLL_BUILD]`: 24 logs (1 por mes) — único de alta frecuencia
* `[PRICING_BUILD]`, `[VISION_BUILD]×2`, `[SCENARIO_BUILD]`, `[STAFFING_BUILD]`: 1 cada uno
* **Total**: ~29 logs INFO por simulación.

Suficiente para debugging end-to-end sin saturar (cf. los logs DEBUG existentes
del provider que producían >500 entradas).

---

## 4. Bloque C — Bugs cleanup

| # | Bug | Estado WAVE 5 | Acción |
|---|-----|----------------|--------|
| 1 | `linea_negocio` exige match exacto (case + acentos) | **RESUELTO** | Canonicalización en provider — `SAC`, `S.A.C`, `Sac` ahora son equivalentes. |
| 2 | `payroll_a` sin ramp-up vs. `ingreso_a` con ramp-up | **DOCUMENTADO** como INTENTIONAL | `docs/v27/ESPECIFICACION_MATEMATICA.md` — ANEXO WAVE 5. |
| 3 | Excel V2-7 pre-cargado con Captura de Datos → P&G en blanco | Sin cambio | Ya abordado por golden master Bancamia en WAVE 4. |
| 4 | Director de cuentas / GTR comisión 0 en Excel vs. 5%/10% spec | **DOCUMENTADO** como business override permanente | `docs/v27/HARD_CODES_Y_ANOMALIAS.md` — Sección 5. |
| 5 | Layout 4 secciones distintas en hoja "Inputs de Nomina" | **DOCUMENTADO** formalmente | Nuevo `docs/v27/NOMINA_LAYOUT_V2_7.md`. |

---

## 5. Conteo de tests

| Métrica | Pre-WAVE-5 (= WAVE 4 final) | Post-WAVE-5 | Δ |
|---------|------------------------------|--------------|---|
| Parity passed | 39 | 39 | 0 |
| Parity total | 39 | 39 | — |
| Suite passed | 742 | 742 | 0 |
| Suite failed | 27 | 27 | 0 |
| Suite errors | 321 | 321 | 0 |
| Suite skipped | 23 | 23 | 0 |
| Suite xfailed | 65 | 65 | 0 |

**100% paridad mantenida**. Cero regresiones. La canonicalización no
introduce cambios de comportamiento numérico — solo expande el espacio de
inputs aceptados.

---

## 6. Archivos modificados / creados

### Creados
* `shared/canonicalization.py` (nuevo módulo, ~220 líneas)
* `docs/v27/NOMINA_LAYOUT_V2_7.md` (nueva doc)
* `docs/v27/WAVE5_REPORT.md` (este reporte)
* `docs/v27/CERTIFICACION_PARIDAD_V2_7.md` (cierre 5 waves)

### Modificados
* `repositories/parametrization_provider.py` (canonicalización + logs)
* `calculators/nomina.py` (log `[PAYROLL_BUILD]`)
* `calculators/pyg.py` (log `[PRICING_BUILD]`)
* `calculators/vision_tarifas.py` (log `[VISION_BUILD]`)
* `calculators/cost_to_serve.py` (log `[VISION_BUILD]`)
* `input/context_builder.py` (logs `[SCENARIO_BUILD]` + `[STAFFING_BUILD]`)
* `storage/parametrization/v2-7/op.json` (bloque `canonicalization_aliases`)
* `docs/v27/HARD_CODES_Y_ANOMALIAS.md` (Sección 5)
* `docs/v27/ESPECIFICACION_MATEMATICA.md` (ANEXO WAVE 5)

---

## 7. Arquitectura post-V2-7

```
                ┌──────────────────────────────────────────────────────────┐
                │   USUARIO / API REQUEST  (DTO inputs sin normalizar)      │
                └────────────────┬─────────────────────────────────────────┘
                                 │  (SAC / S.A.C / Sac / Customer Care)
                                 ▼
                ┌──────────────────────────────────────────────────────────┐
                │  shared/canonicalization.py     (WAVE 5)                  │
                │  canonical_service / channel / role / modalidad / complej.│
                │  + overlay op.json[canonicalization_aliases]              │
                └────────────────┬─────────────────────────────────────────┘
                                 │  "Sac"
                                 ▼
                ┌──────────────────────────────────────────────────────────┐
                │  parametrization_provider.py    (capa Application)        │
                │  WAVE 4: business overrides marcados                      │
                │  WAVE 5: canonicaliza linea/role antes del lookup         │
                └────────────────┬─────────────────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────────────────────┐
            ▼                    ▼                                    ▼
    ┌──────────────┐   ┌──────────────────┐                ┌──────────────────┐
    │ HR repos     │   │ OP / GN repos     │               │ Business rules   │
    │ payroll      │   │ infrastructure /  │                │ versions.json    │
    │ profitability│   │ financial         │                │ + business override│
    └──────┬───────┘   └─────────┬─────────┘                └──────────────────┘
           │                     │
           ▼                     ▼
    ┌─────────────────────────────────────────────┐
    │ storage/parametrization/v2-7/ (WAVE 1)       │
    │   hr.json   gn.json   op.json                │
    │   business_rules.json   manifest.json         │
    └─────────────────────────────────────────────┘

   ┌──────── Engine pipeline (calculators) ────────────────────────────┐
   │                                                                   │
   │  input/context_builder.py                                          │
   │     [SCENARIO_BUILD] + [STAFFING_BUILD]   (WAVE 5)                 │
   │             │                                                     │
   │             ▼                                                     │
   │  calculators/nomina.py            [PAYROLL_BUILD]   (WAVE 5)       │
   │             │                                                     │
   │             ▼                                                     │
   │  calculators/no_payroll.py / cadena_b.py / cadena_c.py             │
   │             │                                                     │
   │             ▼                                                     │
   │  calculators/costos_totales.py + costos_financieros.py             │
   │             │                                                     │
   │             ▼                                                     │
   │  calculators/pyg.py               [PRICING_BUILD]   (WAVE 5)       │
   │             │   ── fórmula WAVE 3:                                 │
   │             │      ingreso = costo / ((1-m)(1-op)(1-com)(1-mk)(1+d))│
   │             ▼                                                     │
   │  calculators/vision_tarifas.py + cost_to_serve.py + visión_pyg.py  │
   │     [VISION_BUILD] (WAVE 5)                                        │
   │             │                                                     │
   │             ▼                                                     │
   │  Resultado → KPIs → API response                                   │
   └───────────────────────────────────────────────────────────────────┘

   Tests:
     tests/parity/  (39 tests, WAVE 4)  +  tests/unit/ + tests/integration/
     Oracle = fórmula simbólica WAVE 3   +  golden master Bancamia
```

---

— Fin del WAVE 5.
