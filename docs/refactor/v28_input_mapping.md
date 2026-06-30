# V2-8 Input Mapping — Paso A (CHECKPOINT A)

> **Estado:** ✅ **PASO B APLICADO** — 14 commits en branch `refactor/modular-pure` (2026-06-10).
> Ver [`request_diff_v28.txt`](request_diff_v28.txt) para el diff completo.
> Ver [`golden_drift_v28_paso_b.md`](golden_drift_v28_paso_b.md) para el log de goldens.

## Resumen ejecutivo

| Tipo | Panel+Reglas | Pólizas (campo-nivel) |
|------|:---:|:---:|
| MATCH | 9 | 25 |
| VALUE_UPDATE | 11 | 11 |
| STRUCTURE_EXTENSION | 4 | — |
| EXCEL_LIKELY_BUG | — | 3 |
| UNKNOWN_SOURCE | — | 1 |

- **Total inputs Panel mapeados:** 24
- **Total pólizas revisadas:** 10
- **Structural gaps (deal-level):** escenarios_comerciales + condiciones_cadena_a/b/c (ver §5 — decisión humana requerida)

---

## §1 Panel de Control General → datos_operativos / reglas_negocio

| V2-8 Hoja!Celda | Etiqueta | Valor V2-8 | req.json path | Valor actual | Tipo | Acción propuesta |
|-----------------|----------|-----------|---------------|--------------|------|-----------------|
| `Panel!C5` | Servicio | `SAC` | `datos_operativos.servicio` | `Cobranzas` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.servicio` de `Cobranzas` → `SAC` |
| `Panel!C6` | Cliente | `METROCUADRADO COM SAS` | `datos_operativos.cliente` | `Bancamia` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.cliente` de `Bancamia` → `METROCUADRADO COM SAS` |
| `Panel!C7` | Antigüedad | `Cliente Antiguo` | `—` | `—` | **STRUCTURE_EXTENSION** | Agregar key: Nueva key datos_operativos.antiguedad; no existe hoy ⚠ Nueva key datos_operativos.antiguedad; no existe hoy |
| `Panel!C8` | Tipo cliente | `Grupo Aval` | `datos_operativos.tipo_cliente` | `No Grupo Aval` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.tipo_cliente` de `No Grupo Aval` → `Grupo Aval` |
| `Panel!C9` | Período pago (días) | `30` | `—` | `—` | **STRUCTURE_EXTENSION** | Agregar key: Nueva key datos_operativos.periodo_pago; no existe hoy ⚠ Nueva key datos_operativos.periodo_pago; no existe hoy |
| `Panel!C10` | Fecha Inicio | `2026-07-01` | `datos_operativos.fecha_inicio` | `2026-01-01` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.fecha_inicio` de `2026-01-01` → `2026-07-01` ⚠ IMPORTANTE: afecta gate SUMIFS P&G en V2-8 (ver Nota Fechas) |
| `Panel!C11` | Duración meses | `24` | `datos_operativos.duracion_meses` | `24` | **MATCH** | Ninguna |
| `Panel!C12` | Ciudad | `Bogota ` | `datos_operativos.ciudad` | `Bogota` | **MATCH** | Ninguna |
| `Panel!C13` | Sede | `Bogota - Toberin` | `datos_operativos.sede` | `Toberin` | **MATCH** | Ninguna ⚠ V2-8='Bogota - Toberin'; req='Toberin' (sufijo); motor usa req.sede |
| `Panel!C16` | Tarifa diaria cap. | `20000` | `datos_operativos.tarifa_diaria_capacitacion` | `20000` | **MATCH** | Ninguna |
| `Panel!C17` | Crucero | `8408` | `datos_operativos.crucero` | `8422` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.crucero` de `8422` → `8408` |
| `Panel!C18` | Horas formación mes | `8` | `datos_operativos.horas_formacion_mes` | `8` | **MATCH** | Ninguna |
| `Panel!C19` | % Ausentismo | `0.065` | `datos_operativos.pct_ausentismo` | `0.065` | **MATCH** | Ninguna |
| `Panel!C20` | % Rotación | `0.0815` | `datos_operativos.pct_rotacion` | `0.085` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.pct_rotacion` de `0.085` → `0.0815` |
| `Panel!C21` | Considera financiación | `False` | `datos_operativos.cons_costo_de_financiacion` | `True` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.cons_costo_de_financiacion` de `True` → `False` ⚠ V2-8='No'→False; req=True |
| `Panel!C28` | Ciudad proporción (Bgta) | `1` | `datos_operativos.ciudades_recurso[0].proporcion` | `1.0` | **MATCH** | Ninguna |
| `Panel!C34` | ICA | `0.01` | `datos_operativos.tasa_ica` | `0.0097` | **VALUE_UPDATE** | Paso B: cambiar `datos_operativos.tasa_ica` de `0.0097` → `0.01` ⚠ cross-check Tasas: Bogota base=Tasas!B37=0.00966; Bogota total(+bomberos)=Tasas!F37=0.01966; Panel=0.01; req=0.0097 — NINGUNO coincide exactamente |
| `Panel!C35` | GMF | `0.004` | `datos_operativos.tasa_gmf` | `0.004` | **MATCH** | Ninguna |
| `Panel!C63` | Margen obj Cadena A | `0.21` | `reglas_negocio.margen_objetivo` | `0.18` | **VALUE_UPDATE** | Paso B: cambiar `reglas_negocio.margen_objetivo` de `0.18` → `0.21` |
| `Panel!D63` | Margen obj Cadena B | `0.3` | `—` | `—` | **STRUCTURE_EXTENSION** | Agregar key: Nueva key reglas_negocio.margen_objetivo_cadena_b=0.30; req solo tiene un margen_objetivo ⚠ Nueva key reglas_negocio.margen_objetivo_cadena_b=0.30; req solo tiene un margen_objetivo |
| `Panel!C67` | Contingencia Operativa | `0` | `reglas_negocio.contingencia_operativa.valor` | `0.025` | **VALUE_UPDATE** | Paso B: cambiar `reglas_negocio.contingencia_operativa.valor` de `0.025` → `0` |
| `Panel!C68` | Contingencia Comercial | `0` | `reglas_negocio.contingencia_comercial.valor` | `0.04` | **VALUE_UPDATE** | Paso B: cambiar `reglas_negocio.contingencia_comercial.valor` de `0.04` → `0` |
| `Panel!C69` | Mark up | `0` | `reglas_negocio.markup.valor` | `0.0` | **MATCH** | Ninguna |
| `Panel!C70` | Descuento volumen | `0` | `—` | `—` | **STRUCTURE_EXTENSION** | Agregar key: Nueva key reglas_negocio.descuento_volumen=0; no existe hoy en req.json ⚠ Nueva key reglas_negocio.descuento_volumen=0; no existe hoy en req.json |

---

## §2 Pólizas (Panel de Control General, filas 38-55)

> Columnas: C=activa, D=pct\_poliza, E=pct\_atribuible, F=aplica\_extensión
> La columna **Tasas ref.** muestra el valor de `Tasas,TRM,Polizas` para cross-check.

| Fila | Nombre póliza | V2-8 activa | req activa | Tipo activa | V2-8 pct | req pct | Tasas ref | Tipo pct | V2-8 pct_atr | req pct_atr | Tipo pct_atr | V2-8 ext | req ext | Tipo ext | Nota |
|------|---------------|:-----------:|:----------:|:-----------:|:-------:|:-------:|:---------:|:--------:|:----------:|:-----------:|:-----------:|:-------:|:-------:|:--------:|------|
| 38 | Póliza de Seriedad  | False | True | **VALUE_UPDATE** | 0.005 | 0.005 | 0.005 | **MATCH** | 0.1 | 0.1 | **MATCH** | False | False | **MATCH** |  |
| 39 | Póliza de Cumplimiento | True | True | **MATCH** | 0.0063 | 0.0062 | 0.0062 | **EXCEL_LIKELY_BUG** | 0.2 | 0.2 | **MATCH** | False | False | **MATCH** | ⚠ Panel=0.0063 ≠ Tasas=0.0062; motor usa Panel (literal); req.json usa Tasas-aligned value=0.0062. DECIDIR en CHECKPOINT A cuál es canónico. |
| 40 | Poliza de Salarios | True | True | **MATCH** | 0.0128 | 0.0119 | 0.0119 | **EXCEL_LIKELY_BUG** | 0.2 | 0.1 | **VALUE_UPDATE** | False | False | **MATCH** | ⚠ Panel=0.0128 ≠ Tasas=0.0119; motor usa Panel (literal); req.json usa Tasas-aligned value=0.0119. DECIDIR en CHECKPOINT A cuál es canónico. |
| 41 | Poliza de Calidad | True | True | **MATCH** | 0.0128 | 0.0119 | 0.0119 | **EXCEL_LIKELY_BUG** | 0.2 | 0.2 | **MATCH** | False | True | **VALUE_UPDATE** | ⚠ Panel=0.0128 ≠ Tasas=0.0119; motor usa Panel (literal); req.json usa Tasas-aligned value=0.0119. DECIDIR en CHECKPOINT A cuál es canónico. |
| 42 | Poliza de rc cruzada | False | True | **VALUE_UPDATE** | 0.0275 | 0.0275 | 0.0275 | **MATCH** | 0.1 | 0.4 | **VALUE_UPDATE** | False | False | **MATCH** |  |
| 43 | poliza de IRF | False | True | **VALUE_UPDATE** | 0.0275 | 0.0275 | 0.0275 | **MATCH** | 0.1 | 0.1 | **MATCH** | False | False | **MATCH** |  |
| 44 | Póliza de Responsabilidad | False | True | **VALUE_UPDATE** | 0.0069 | 0.0069 | 0.0069 | **MATCH** | 0.1 | 0.4 | **VALUE_UPDATE** | False | False | **MATCH** |  |
| 45 | Comisión de Administraciòn (1,18% sobre ventas Gcomercial-Operaciones) | True | True | **MATCH** | 0.0118 | 0.0118 | 0.0118 | **MATCH** | 1 | 1.0 | **MATCH** | False | False | **MATCH** |  |
| 46 | Otros impuestos | False | True | **VALUE_UPDATE** | 0.01 | 0.01 | None | **MATCH** | 0 | 0.0 | **MATCH** | False | False | **MATCH** |  |
| 50 | Responsabilidad Civil Protección de Datos | False | True | **VALUE_UPDATE** | None | 0.04 | None | **UNKNOWN_SOURCE** | None | 0.4 | **VALUE_UPDATE** | False | False | **MATCH** | ⚠ Panel!D no tiene valor (celda vacía) |

---

## §3 Fecha de Inicio — nota especial

| Campo | V2-8 Panel!C10 | request.json | Clasificación |
|-------|---------------|--------------|---------------|
| fecha_inicio | `2026-07-01` | `2026-01-01` | **VALUE_UPDATE** |

> **Impacto en motor V2-8:** La hoja Visión P&G en V2-8 usa
> `SUMIFS` con gate de fecha para seleccionar el escenario activo.
> Si `fecha_inicio` queda fuera del rango calculado en Hoja Maestra,
> el SUMIFS retornará 0 → ingresos/contingencias = 0 en P&G.
> **Hoja Maestra Escenarios NO tiene columnas de fechas** — el gate
> vive en la fórmula de `Visión P&G` (ver Stage 2 P&G fix).
> Cambiar a `2026-07-01` es necesario para que P&G produzca valores.

---

## §4 EXCEL_LIKELY_BUG — Discrepancias internas V2-8 (Panel vs Tasas TRM)

Las siguientes pólizas tienen valores literales en Panel que **difieren**
del valor de referencia en `Tasas, TRM, Polizas`.
Panel es la fuente que el motor usa (literal input, no fórmula).
Tasas TRM es la tabla de referencia.

| Póliza | Panel!D (motor usa) | Tasas!B (referencia) | Diferencia | Recomendación |
|--------|--------------------:|---------------------:|:----------:|---------------|
| Póliza de Cumplimiento (D39) | 0.0063 | 0.0062 | +0.0001 | Decidir en CHECKPOINT A: ¿Panel correcto o typo? |
| Poliza de Salarios (D40) | 0.0128 | 0.0119 | +0.0009 | Decidir en CHECKPOINT A: ¿Panel correcto o typo? |
| Poliza de Calidad (D41) | 0.0128 | 0.0119 | +0.0009 | Decidir en CHECKPOINT A: ¿Panel correcto o typo? |

**ICA adicional:**

| Fuente | Valor | Nota |
|--------|------:|------|
| Panel!C34 (input deal) | 0.01 | Valor ingresado por usuario para este deal |
| Tasas!B37 (Bogota base tarifa) | 0.00966 | Tarifa base sin sobretasas |
| Tasas!F37 (Bogota total: base+bomberos) | 0.01966 | Incluye 1% bomberos |
| request.json tasa_ica | 0.0097 | Aproximación al base Bogota |

> ICA Bogota: ninguna fuente coincide exactamente. Confirmar cuál aplicar en CHECKPOINT A.

---

## §5 Structural Gaps (deal-level) — decisión humana requerida

Estos gaps NO pueden resolverse con VALUE_UPDATE. Requieren decisión:
**a)** reemplazar request.json con datos V2-8 (implica regenerar goldens),
**b)** diferir Stage 2 hasta que el deal real del cliente esté en V2-8.

### §5a escenarios_comerciales

**V2-8 Hoja Maestra Escenarios (3 escenarios):**

| # | Escenario | Modalidad | Canal | Modelo cobro | FTE | Comp. Fijo | Comp. Variable | Costo Cad A |
|---|-----------|-----------|-------|--------------|----:|:----------:|:--------------:|------------:|
| Escenario 1 | Escenario 1 | Inbound | Voz 1 | Variable | 130 | 0 (0) | Transacción (1) | 731,079,608 |
| Escenario 2 | Escenario 2 | Inbound | WhatsApp | Fijo | 50 | 0 (0) | Transacción (1) | 247,418,950 |
| Escenario 3 | Escenario 3 | Inbound | Voz 2 | Fijo | 80 | 0 (0) | Transacción (1) | 461,006,066 |

**request.json escenarios_comerciales (actuales):**

| # | Modalidad | Canal | Modelo cobro | Comp. Fijo | Prop. | Comp. Variable | Prop. |
|---|-----------|-------|--------------|:----------:|------:|:--------------:|------:|
| 1 | Inbound | WhatsApp | FTE | Tiempo | 1.0 |  | 0.0 |
| 2 | Outbound | WhatsApp | FTE | Tiempo | 1.0 |  | 0.0 |
| 3 | Outbound | Correo | FTE | Tiempo | 1.0 |  | 0.0 |

> **Veredicto:** `REQUEST_STRUCTURE_GAP` (deal-level). Canales completamente distintos
> (V2-8: Voz1+WhatsApp+Voz2; req: WhatsApp+Correo). Modelos cobro distintos.
> Decisión requerida antes de Paso B.

### §5b Condiciones Cadena A

**V2-8 tiene 3 perfiles columna (1 por escenario):**

| Escenario | Modalidad | Canal | FTE | Salario base | Comisión perfil | Estaciones pres. |
|-----------|-----------|-------|----:|-------------:|----------------:|-----------------:|
| Escenario SAC Actual | Inbound | Voz 1 | 130 | 1,750,905 | 600,000 | 78 |
| Escenario WhatsApp Actual | Inbound | WhatsApp | 50 | 1,750,905 | 600,000 | 30 |
| Crecimiento inhouse | Inbound | Voz 2 | 80 | 1,750,905 | 600,000 | 48 |

**request.json condiciones_cadena_a.perfiles (actuales):**

| Perfil | Modalidad | Canal | FTE |
|--------|-----------|-------|----:|
| Inbound 10 | Inbound | WhatsApp | 10 |
| Inbound 15 personas | Inbound | Correo | 15 |
| Inbound 20 personas | Inbound | WebChat | 20 |

> **Veredicto:** `REQUEST_STRUCTURE_GAP` (deal-level). V2-8 tiene 3 escenarios por columna;
> req.json tiene 3 perfiles por fila con canales distintos (WhatsApp/Correo/WebChat).
> Estructura incompatible; no parcheable por VALUE_UPDATE solo.

### §5c Condiciones Cadena B

**V2-8 OPEX items (Condiciones Cadena B):**

| Rubro | Modalidad | Canal | Tipo cobro | Valor |
|-------|-----------|-------|------------|------:|
| Plataformas y licencias | Inbound | Voz 2 | Unitario | 250 |

**V2-8 Equipo Soporte FTE:** 3

**V2-8 CAPEX items:**

| Rubro | Modalidad | Canal | Valor | Cantidad | Meses diferir |
|-------|-----------|-------|------:|---------:|--------------:|
| Infraestructura y cloud | Inbound | Voz 2 | 2500000 | 60 | 24 |

> **Veredicto:** `REQUEST_STRUCTURE_GAP`. V2-8 Cadena B tiene OPEX para canal Voz2;
> req.json tiene diferentes rubros/canales.

### §5d Condiciones Cadena C

**V2-8 tarifas proveedor:**

| Proveedor | Servicio | Modalidad | Canal | Tipo cobro | Valor | Cantidad |
|-----------|----------|-----------|-------|------------|------:|---------:|
| Accenture | Nexa AI | Inbound | Voz 1 | Unitario | 5130.66 | 170000 |

**V2-8 OPEX Cadena C:**

| Descripción | Modalidad | Canal | Valor | Cantidad |
|-------------|-----------|-------|------:|---------:|
| Consumo variable (metering) | Inbound | Voz 1 | 117 | 190000 |

> **Veredicto:** `REQUEST_STRUCTURE_GAP`. V2-8 Cadena C usa Accenture/Nexa AI/Voz1;
> req.json condiciones_cadena_c actualmente vacío (tarifa_proveedor_canal.items=[]).
> Este es un cambio significativo de deal.

---

## §6 STRUCTURE_EXTENSION — keys nuevas dentro de objetos existentes

Los siguientes inputs V2-8 no tienen key en req.json pero pueden **agregarse**
dentro de un objeto top-level existente (sin nueva key top-level, con aprobación):

| V2-8 Cell | Label | Valor V2-8 | Propuesta key nueva | Objeto existente |
|-----------|-------|-----------|---------------------|-----------------|
| `Panel!C7` | Antigüedad | `Cliente Antiguo` | Nueva key datos_operativos.antiguedad; no existe hoy | (top-level existente) |
| `Panel!C9` | Período pago (días) | `30` | Nueva key datos_operativos.periodo_pago; no existe hoy | (top-level existente) |
| `Panel!D63` | Margen obj Cadena B | `0.3` | Nueva key reglas_negocio.margen_objetivo_cadena_b=0.30; req solo tiene un margen_objetivo | (top-level existente) |
| `Panel!C70` | Descuento volumen | `0` | Nueva key reglas_negocio.descuento_volumen=0; no existe hoy en req.json | (top-level existente) |

---

## §7 Confirmaciones (sin cambio necesario)

- `Riesgo`: NO tiene celdas de input del deal. Solo parametrización estática (pesos de calificación de riesgo operativo/cliente). Sin acción.
- `Pólizas - Costo Financiacion`: NO tiene celdas de input. Hoja de cálculo/reporte; referencia Panel y Costos Totales. Sin acción.
- `Tasas, TRM, Polizas`: Tabla de referencia (IPC, SMLV, ICA por ciudad). Bogota: base=Tasas!B37=0.00966, total con sobretasas=Tasas!F37=0.01966. Estos son parámetros de parametrización, no inputs del deal.

---

---

## Paso B aplicado — commits y estado

| # | Commit | Cambio | Excel V2-8 | Goldens |
|---|--------|--------|------------|---------|
| 1 | 3ad1215 | add `datos_operativos.antiguedad = "Cliente Antiguo"` | Panel!C7 | 63/63 |
| 2 | 5288e66 | add `datos_operativos.periodo_pago = 30` | Panel!C9 | 63/63 |
| 3 | 395390e | add `reglas_negocio.margen_objetivo_cadena_b = 0.30` | Panel!D63 | 63/63 |
| 4 | 1cd9ad7 | add `reglas_negocio.descuento_volumen = 0` | Panel!C70 | 63/63 |
| 5 | a4aaaeb | `pct_rotacion` 0.085 → 0.0815 | Panel!C20 | 63/63 |
| 6 | 01abc18 | `crucero` 8422 → 8408 | Panel!C17 | 63/63 |
| 7 | 58957a3 | `tasa_ica` 0.0097 → 0.01 | Panel!C34 | 63/63 |
| 8 | 4034baa | `polizas[Cumplimiento].pct_poliza` 0.0062 → 0.0063 | Panel!D39 | 63/63 |
| 9 | a04df3b | `polizas[Salarios].pct_poliza` 0.0119 → 0.0128 | Panel!D40 | 63/63 |
| 10 | 246f5af | `polizas[Calidad].pct_poliza` 0.0119 → 0.0128 | Panel!D41 | 63/63 |
| 11 | 8927ee2 | `margen_objetivo` 0.18 → 0.21 | Panel!C63 | 63/63 |
| 12 | 6cd0575 | `contingencia_operativa.valor` 0.025 → 0 | Panel!C67 | 63/63 |
| 13 | b486fd5 | `contingencia_comercial.valor` 0.04 → 0 | Panel!C68 | 63/63 |
| 14 | a4f1c73 | `cons_costo_de_financiacion` true → false | Panel!C21 | 63/63 |

**Parity runner post-Paso B:** `INPUT_DEAL_MISMATCH` persiste — esperado.
Campos deferred (servicio/cliente/tipo_cliente/fecha_inicio) = deal-level, decisión 1 CHECKPOINT A.

---

## CHECKPOINT A — Decisiones requeridas antes de Paso B

1. **escenarios_comerciales + condiciones_cadena_a/b/c** (§5):
   - Opción a: reemplazar request.json con deal V2-8 (SAC/METROCUADRADO/Voz1)
     → regeneración total de 63 goldens necesaria
   - Opción b: diferir hasta que el deal real esté en V2-8

2. **EXCEL_LIKELY_BUG pólizas** (§4):
   - Cumplimiento D39=0.0063 vs Tasas B22=0.0062 → ¿cuál es canónico?
   - Salarios D40=0.0128 vs Tasas B23=0.0119 → ¿cuál es canónico?
   - Calidad D41=0.0128 vs Tasas B24=0.0119 → ¿cuál es canónico?

3. **ICA discrepancia** (§4): Panel!C34=0.01 vs Tasas Bogota=0.00966/0.01966 vs req=0.0097

4. **STRUCTURE_EXTENSION** (§6): Aprobar key por key antes de Paso B.

5. **VALUE_UPDATE** (§1): Una vez resueltas las decisiones anteriores,
   los VALUE_UPDATE restantes pueden aplicarse en Paso B.
