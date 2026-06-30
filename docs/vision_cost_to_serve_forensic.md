# Forensic Analysis: Vision Cost To Serve
## Excel V2-4 ↔ Backend Gap Analysis

**Fecha:** 2026-05-20  
**Hoja Excel:** `Vision Cost To Serve` (sheet index 24)  
**Dimensiones:** A1:DN268 (118 columnas, 268 filas)  
**Referencia backend:** `calculators/cost_to_serve.py`, `domain/models.py:ResultadoCostToServe`

---

## 1. Mapa de Secciones

La hoja tiene **9 secciones** distintas:

| # | Sección | Filas | Estado backend |
|---|---------|-------|----------------|
| 01 | Ficha del Deal | 7–13 | ✅ Completa (via `panel` + `ficha_deal`) |
| 02 | Economics KPIs | 15–20 | ⚠️ Parcial (falta H019, N020, escenario label) |
| 03 | Visión General por Servicio | 23–55 | ❌ Incompleta (K50 incorrecto, sub-componentes ausentes) |
| 04 | Visión General por Canal | 58–83 | ❌ Completamente ausente |
| 05 | Visual Detallada por Canal | 87–120 | ❌ Completamente ausente |
| 06 | Cadena B/C por Dirección | 127–133 | ❌ Completamente ausente |
| 07 | Estructura del Equipo (escenarios) | 122–168 | ❌ Completamente ausente |
| 08 | Reglas de Negocio | 177–200 | ⚠️ Parcial (sin valores monetarios) |
| 09 | Evaluación de Riesgo | 204–244 | ✅ Completa (RiesgoCalculator) |

---

## 2. Inventario Celda por Celda — Sección 02: Economics

| celda_excel | label_excel | formula_excel | campo_backend_actual | falta_backend | notas |
|-------------|-------------|---------------|---------------------|---------------|-------|
| B019 | INGRESO MENSUAL | `=IFERROR('Vision Tarifas_Modelo_Cobro'!$C$72,0)` | `kpis.ingreso_mensual` | ✅ | Match exacto |
| H019 | COST TO SERVE MENSUAL | `='Vision Tarifas_Modelo_Cobro'!C40+C50+C60` | — | ❌ | Suma avg monthly de 3 cadenas. No existe en JSON |
| N019 | MARGEN DEL DEAL | `='Panel de Control General'!C63` | `kpis.margen` | ✅ | |
| T019 | VALOR TOTAL DEL CONTRATO | `='Visión P&G'!BK26` | `kpis.valor_total_deal` | ✅ | |
| B020 | Escenario 1 (label) | hardcoded `'Escenario 1'` | — | ❌ | Label del escenario activo de staffing |
| H020 | Subtitle cts_mensual | hardcoded string | — | ❌ | Descripción textual, no dato crítico |
| N020 | Status margen | `IF(margen > max_margen, "✓ Excede máximo", ...)` | — | ❌ | Comparación con máximo de parametrización |
| T020 | Label duración | `"Acumulado en " & meses & " meses"` | — | ❌ | Texto dinámico, computable en frontend |

**Valores caso bancamia:**
- H019 = 301,965,088.76 (monthly average total cost across all chains)

---

## 3. Inventario Celda por Celda — Sección 03: Visión General por Servicio

### 3.1 Participaciones por cadena

| celda | label | formula | campo_backend | falta | notas |
|-------|-------|---------|---------------|-------|-------|
| C031 | Part. Cadena A | `='Panel de Control General'!$K$51` | `cts.participacion_a` | ✅ | `K51 = K50/J50` |
| G031 | Part. Cadena B | `='Panel de Control General'!$L$51` | `cts.participacion_b` | ✅ | `L51 = L50/J50` |
| K031 | Part. Cadena C | `='Panel de Control General'!$M$51` | — | ❌ | Siempre 0 hoy, pero campo ausente en JSON |

### 3.2 Cadena A — desglose (col C = valor absoluto, col D = % del total cts_a)

**⚠️ BUG CRÍTICO: K50 incorrecto**

El Excel calcula K50 así (PCG K50 = SUM K42:K49):
```
K42_canal = IF(outbound_activa, SUMPRODUCT(J30:J37 × N_outbound × match_canal), 0)
           + IF(inbound_activa,  SUMPRODUCT(J17:J23 × N_inbound  × match_canal), 0)
```
Donde `J` = volumen del canal, `N` = fracción atribuible a Cadena A.

**Resultado caso bancamia:**
- K50_excel = 4,534.89 (volumen ponderado × participación Cadena A)
- K50_backend = `2 × FTE_base = 12` → **incorrecto por factor ~378×**

| celda | label | formula_excel | valor_excel | campo_backend | valor_backend | falta | delta |
|-------|-------|---------------|-------------|---------------|---------------|-------|-------|
| C034 | CTS Cadena A total | `=C35+C45` | 72,437.70 | `cts.cts_cadena_a` | 3,265,896.56 | ❌ | ~8.38× (denominador K50 incorrecto) |
| C035 | Payroll | `=SUM(C37:C43)` | 24,551.52 | — | — | ❌ | Ausente |
| C036 | Nómina loaded | SUM(NL_D100:BK100) / K50 | 24,287.66 | — | — | ❌ | Ausente |
| C037 | Salario Fijo | SUM(NL salario_fijo rows / K50) | 23,102.65 | — | — | ❌ | Ausente |
| C038 | Salario Variable | SUM(NL salario_var rows / K50) | 1,185.01 | — | — | ❌ | Ausente |
| C039 | Capacitación Inicial | SUM(NL cap_inicial rows / K50) | 88.94 | — | — | ❌ | Ausente |
| C040 | Capacitación Rotación | SUM(NL cap_rot rows / K50) | 53.23 | — | — | ❌ | Ausente |
| C041 | Exámenes Médicos | SUM(NL examenes rows / K50) | 73.40 | — | — | ❌ | Ausente |
| C042 | Estudios de Seguridad | SUM(NL estudios rows / K50) | 0.00 | — | — | ❌ | Ausente |
| C043 | Crucero | SUM(NL crucero rows / K50) | 48.28 | — | — | ❌ | Ausente |
| D035 | % Payroll / CTS_A | `=IFERROR(C35/$C$34,0)` | 33.89% | — | — | ❌ | Derivable |
| D037 | % Salario Fijo | `=IFERROR(C37/$C$34,0)` | 31.89% | — | — | ❌ | Derivable |
| D038 | % Salario Variable | `=IFERROR(C38/$C$34,0)` | 1.64% | — | — | ❌ | Derivable |
| C045 | No Payroll | `=SUM(C46:C48)` | 47,886.18 | `cts.desglose_a.no_payroll` | ~761 | ❌ | K50 bug |
| C046 | OPEX Fijo | SUM(NP opex rows / K50) | 45,756.36 | — | — | ❌ | Ausente |
| C047 | Inversiones | SUM(NP inv rows / K50) | 412.74 | — | — | ❌ | Ausente |
| C048 | Costos Fijos x Estación | SUM(NP costos_est rows / K50) | 1,717.08 | — | — | ❌ | Ausente |
| D045 | % No Payroll / CTS_A | `=IFERROR(C45/$C$34,0)` | 66.11% | — | — | ❌ | Derivable |

### 3.3 Cadena B — desglose (col G = valor, col H = % del total cts_b)

| celda | label | formula_excel | valor_excel | campo_backend | falta | notas |
|-------|-------|---------------|-------------|---------------|-------|-------|
| G034 | CTS Cadena B total | `=G35+G41` | 119,566.96 | `cts.cts_cadena_b` | ✅ | Match 0.0004% |
| G035 | Componente Fijo | `=SUM(G36:G38)` | 63,652.07 | — | ❌ | Ausente |
| G036 | OPEX fijo canal | SUM(CF E60:BL60 / L50) | 58,812.81 | — | ❌ | De hoja "Costo Fijo" |
| G037 | Inversiones canal | SUM(CF D151:BK151 / L50) | 0.20 | — | ❌ | Casi siempre 0 |
| G038 | S&M (Service & Maint.) | SUM(CF E189:BL189 / L50) | 4,839.07 | — | ❌ | De hoja "Costo Fijo" |
| G041 | Componente Variable | `=SUM(G42:G45)` | 55,914.89 | — | ❌ | Ausente |
| G042 | Tarifa | SUM(CV F49:BM49 / L50) | 1,500.00 | — | ❌ | Tarifa × volumen |
| G043 | OPEX Variable | SUM(CV E87:BL87 / L50) | 0.00 | — | ❌ | Siempre 0 hoy |
| G044 | Tasa de Escalamiento | SUM(CV H132:BO132 / L50) | 0.00 | — | ❌ | Reservado |
| G045 | HITL | `=G41-G42-G43-G44` | 54,414.89 | — | ❌ | Hardcoded input Cadena B |
| H035 | % Comp. Fijo / CTS_B | `=IFERROR(G35/$G$34,0)` | 53.24% | — | ❌ | Derivable |
| H041 | % Comp. Variable | `=IFERROR(G41/$G$34,0)` | 46.76% | — | ❌ | Derivable |

### 3.4 Cadena C — desglose (col K = valor, col L = %)

| celda | label | campo_backend | falta | notas |
|-------|-------|---------------|-------|-------|
| K034 | CTS Cadena C total | — | ❌ | Ausente (siempre 0 en este caso) |
| K035 | Tarifa Proveedor | — | ❌ | Ausente |
| K036 | Costo integración | — | ❌ | Ausente |
| K037–K043 | Sub-componentes | — | ❌ | Ausente |

### 3.5 CTS Ponderado

| celda | formula_excel | valor_excel | campo_backend | valor_backend | falta |
|-------|---------------|-------------|---------------|---------------|-------|
| G049 | `=(C34×C31)+(G34×G31)+(K34×K31)` | 91,202.11 | `cts.cts_ponderado` | ~393,174 | ❌ BUG (K50 incorrecto en C34) |

---

## 4. Inventario — Sección 04: Visión General por Canal (COMPLETAMENTE AUSENTE)

Filas 64–83. Para cada canal (WhatsApp, Correo, WebChat, Mensajes, Voz, Otros, IVR):

| campo | formula_excel | campo_backend | falta |
|-------|---------------|---------------|-------|
| volumen_total_canal | FILTER(PCG!J17:J23, canal) | — | ❌ |
| part_cadena_a_canal | FILTER(PCG!N17:N23, canal) | — | ❌ |
| cts_a_canal | IF(part_A>0, SUMPRODUCT(payroll_canal_months)/L50, "No Activado") | — | ❌ |
| part_cadena_b_canal | FILTER(PCG!O17:O23, canal) | — | ❌ |
| cts_b_canal | SUMPRODUCT(costo_b_canal_months)/L50 | — | ❌ |
| part_cadena_c_canal | FILTER(PCG!P17:P23, canal) | — | ❌ |
| cts_c_canal | (similar) | — | ❌ |
| cts_ponderado_canal | `IF(num(E), E, 0)×part_A + IF(num(G), G, 0)×part_B + part_C×cts_c` | — | ❌ |

**Totales por fila (71 inbound, 83 outbound):**
- Total inbound: vol=7,516.89, cts_b_total=358,700.89, cts_pond≈0
- Total outbound: vol=18, costos≈0

---

## 5. Inventario — Sección 05: Visual Detallada por Canal (COMPLETAMENTE AUSENTE)

Filas 90–120. Para el canal seleccionado (ej. WhatsApp), desglosa Cadena A y B por dirección (Inbound/Outbound):

| campo | falta | notas |
|-------|-------|-------|
| participacion_inbound_a | ❌ | FILTER(PCG N17:N23, canal) |
| participacion_outbound_a | ❌ | FILTER(PCG N30:N37, canal) |
| cts_a_inbound_total | ❌ | Sum payroll+no_payroll for inbound direction of canal |
| cts_a_outbound_total | ❌ | Same for outbound |
| payroll_inbound | ❌ | Sub-breakdown identical a Sección 03 pero per-canal per-dirección |
| [8 sub-componentes payroll] | ❌ | por dirección |
| no_payroll_inbound | ❌ | |
| [3 sub-componentes no_payroll] | ❌ | |
| cts_b_inbound | ❌ | `=(C98×C95)+(J98×J95)+(P98×P95)` |
| cts_b_outbound | ❌ | |
| cts_ponderado_canal_inbound | ❌ | L115 |
| cts_ponderado_canal_outbound | ❌ | |

---

## 6. Inventario — Sección 06: Cadena B/C por Dirección (AUSENTE)

Filas 128–133:

| campo | formula_excel | valor_excel | falta |
|-------|---------------|-------------|-------|
| cadena_b_total | acumulado anual Cadena B | 358,700,885.66 | ❌ (backend tiene avg mensual) |
| cadena_b_componente_humano_inbound | SUM nóminas Cadena B inbound | 115,873,573.27 | ❌ |
| cadena_b_componente_tecnologico_inbound | SUM opex Cadena B inbound | 242,827,312.38 | ❌ |
| cadena_b_componente_humano_outbound | — | 0 | ❌ |
| cadena_c_total | — | 0 | ❌ |
| cadena_c_componente_humano | — | 0 | ❌ |
| cadena_c_componente_tecnologico | — | 0 | ❌ |

---

## 7. Inventario — Sección 07: Estructura del Equipo / Escenarios (AUSENTE)

Filas 137–168. Hasta 15 escenarios de staffing configurados en "Condiciones Cadena A":

| campo | formula_excel | falta | notas |
|-------|---------------|-------|-------|
| escenario_headers | FILTER(CondCadenaA!E16:S16, <>""​) | ❌ | nombres de escenarios |
| payroll_por_escenario | SUMPRODUCT(NL × match_scenario × match_direction) / meses | ❌ | |
| nomina_loaded_por_escenario | idem | ❌ | |
| salario_fijo_escenario | idem rows NL 72:88 | ❌ | |
| salario_variable_escenario | idem | ❌ | |
| [7 sub-comps payroll] | idem | ❌ | |
| no_payroll_por_escenario | idem NP rows | ❌ | |
| [3 sub-comps no_payroll] | idem | ❌ | |
| cadena_a_total_escenario | payroll + no_payroll | ❌ | I153=39,190,759 ≈ backend avg |
| peso_staff_total | (nomina_loaded + cadena_b_hum + cadena_c_hum) / (cad_b + cad_c + cad_a) | ❌ | |
| peso_staff_sin_agente | sin contribución agente básico | ❌ | |
| nomina_agente_basico | SUMPRODUCT(NL rows 117:131) / meses | ❌ | |

**Nota:** El escenario I (primero activo) = escenario actual del contrato. Backend ya computa el equivalente en `pyg_por_mes` pero no en este formato de comparación de escenarios.

---

## 8. Inventario — Sección 08: Reglas de Negocio

| celda | label | formula_excel | campo_backend | falta | notas |
|-------|-------|---------------|---------------|-------|-------|
| B182 | ALERTA gerencia | IF(T019 > umbral_aprobacion) | `evaluacion_riesgo.requiere_aprobacion` | ✅ (indirectamente) | |
| C182 | Texto alerta | string condicional | — | ❌ | Texto generado; puede ser frontend |
| C186 | Costo total acumulado | `=SUM(P&G C30:BJ30, C44:BJ44, C54:BJ54)` | — | ❌ | Sum total de costos en todos los meses |
| C192 | Margen objetivo % | FILTER(PCG!C63:C70, B192) | `reglas_negocio[0].aplicado` | ✅ | |
| D192 | Margen monto | `=$C$186×C192` | — | ❌ | Valor monetario del margen |
| C193 | Contingencia OP % | `='Panel de Control General'!C67` | `reglas_negocio[1].aplicado` | ✅ | |
| D193 | Contingencia OP monto | `=$C$186×C193` | — | ❌ | |
| C194 | Contingencia COM % | — | `reglas_negocio[2].aplicado` | ✅ | |
| D194 | Contingencia COM monto | — | — | ❌ | |
| C195 | Markup % | — | `reglas_negocio[3].aplicado` | ✅ | |
| D195 | Markup monto | — | — | ❌ | |
| C196 | Descuento % | — | `reglas_negocio[4].aplicado` | ✅ | |
| D196 | Descuento monto | — | — | ❌ | |
| C200 | Valor total deal | `=(C186+D192+D193+D194+D195)-D196` | `kpis.valor_total_deal` | ✅ | Semántica idéntica |

---

## 9. Análisis del Límite de Meses

### Excel
- Nomina Loaded: columnas F:BM = **60 meses** (col 6 a 65)
- Visión P&G: columnas C:BJ = **60 meses** (col 3 a 62)
- PCG C11 = `12` (hardcoded en este caso)
- La hoja soporta hasta 60 meses; activa solo los `meses_contrato` configurados

### Backend
- `panel.meses_contrato` controla la iteración en **todas las capas del engine**
- No hay límite hardcodeado de 12 en ningún calculator
- Confirmado: `len(pyg_por_mes) == panel.meses_contrato` siempre
- **Conclusión: NO hay bug de truncado a 12 meses. El backend soporta 1–60 meses.**

---

## 10. Bug Crítico: K50 Incorrecto

### Síntoma
| campo | Excel (V2-4) | Backend actual | Delta |
|-------|-------------|----------------|-------|
| K50 (denominador CTS_A) | 4,534.89 | 12.0 | ×378 |
| cts_a | 72,437.70 | 3,265,896.56 | ×45 |
| cts_ponderado | 91,202.11 | ~393,174 | ×4.3 |
| cts_b | 119,566.96 | 119,567.00 | 0.0004% ✅ |
| participacion_a | 0.6019 | 0.0119 | ×50 |

### Causa Raíz
El `_k50()` del backend usa la convención simplificada:
```python
def _k50(self) -> float:
    """K50 = 2 × FTE base (replica convención Excel).""" # ← INCORRECTO
    fte_base = sum(p.fte for p in self._perfiles if not p.es_soporte)
    return 2.0 * fte_base
```

La convención Excel REAL es (PCG K50 = SUM K42:K49):
```
K50 = Σ_canal [ volumen_canal_outbound × part_A_outbound + volumen_canal_inbound × part_A_inbound ]
```
Donde `volumen_canal` viene del PCG (J17:J23 para inbound, J30:J37 para outbound) y `part_A` es la fracción atribuible a Cadena A (N17:N23, N30:N37).

Para L50 (Cadena B, formula L42):
```
L50 = Σ_canal [ volumen_canal_outbound × part_B_outbound + volumen_canal_inbound × part_B_inbound ]
```

**Nota:** El `cts_b` aún es correcto por coincidencia — L50_excel=3000 ≈ L50_backend (sum vol_cadena_b) porque en este caso la mayoría del volumen Cadena B es inbound.

---

## 11. Escenarios a Validar

| escenario | estado |
|-----------|--------|
| Canal individual (1 canal inbound) | K50 bug presente |
| Multi-canal (3 canales, inbound+outbound) | K50 bug presente |
| Consolidado | K50 bug presente |
| Ramp-up (meses 1-3 con factor rampup) | Backend correcto; CTS usa averages correctamente |
| Indexación anual (meses 13+) | Backend soporta >12 meses; no hay cap |
| Con financiación | No afecta CTS (financiación va en P&G, no en CTS_A/B) |
| Con contingencias | No afecta CTS directamente (va en P&G) |
| 60 meses | Backend soporta; sin cap |

---

## 12. Contrato JSON Actual vs Requerido

### Actual (`cost_to_serve` en JSON de salida)
```json
{
  "cts_cadena_a": 3265896.56,      ← K50 incorrecto
  "cts_cadena_b": 119566.96,       ← correcto
  "cts_ponderado": 393173.68,      ← incorrecto (derivado de cts_a incorrecto)
  "participacion_a": 0.0119,       ← incorrecto
  "participacion_b": 0.9881,       ← incorrecto
  "fte_cadena_a": 12.0,            ← semánticamente incorrecto (es 2×FTE, no K50)
  "vol_cadena_b": 1000.0,          ← correcto (L50)
  "desglose_a": {
    "nomina": 2501434.71,          ← calculado sobre K50 incorrecto
    "no_payroll": 764461.85        ← calculado sobre K50 incorrecto
  }
}
```

### Requerido (alineado con Excel V2-4)
```json
{
  "kpis_economics": {
    "ingreso_mensual": 355764509.40,
    "cts_mensual_total": 301965088.76,   ← NUEVO: sum avg costs 3 cadenas
    "margen": 0.1339,
    "valor_total_deal": 5471188699.14,
    "escenario_label": "Escenario 1",
    "margen_status": "Excede máximo"     ← comparación con límite parametrización
  },

  "vision_general": {
    "servicio": "Cobranzas",
    "participacion_a": 0.6019,
    "participacion_b": 0.3981,
    "participacion_c": 0.0000,
    "k50_cadena_a": 4534.89,
    "l50_cadena_b": 3000.0,
    "m50_cadena_c": 0.0,

    "cadena_a": {
      "cts_total": 72437.70,
      "payroll": {
        "total": 24551.52,
        "pct": 0.3389,
        "nomina_loaded": 24287.66,
        "salario_fijo": 23102.65,
        "salario_variable": 1185.01,
        "cap_inicial": 88.94,
        "cap_rotacion": 53.23,
        "examenes": 73.40,
        "estudios_seguridad": 0.00,
        "crucero": 48.28
      },
      "no_payroll": {
        "total": 47886.18,
        "pct": 0.6611,
        "opex_fijo": 45756.36,
        "inversiones": 412.74,
        "costos_fijos_estacion": 1717.08
      }
    },

    "cadena_b": {
      "cts_total": 119566.96,
      "componente_fijo": {
        "total": 63652.07,
        "pct": 0.5324,
        "opex": 58812.81,
        "inversiones": 0.20,
        "s_m": 4839.07
      },
      "componente_variable": {
        "total": 55914.89,
        "pct": 0.4676,
        "tarifa": 1500.00,
        "opex_variable": 0.00,
        "tasa_escalamiento": 0.00,
        "hitl": 54414.89
      }
    },

    "cadena_c": {
      "cts_total": 0.0,
      "tarifa_proveedor": 0.0,
      "costo_integracion": 0.0,
      "opex": 0.0,
      "inversiones": 0.0,
      "equipo_integracion": 0.0,
      "costo_variable": 0.0,
      "tasa_escalamiento": 0.0,
      "opex_variable": 0.0,
      "hitl": 0.0
    },

    "cts_ponderado": 91202.11
  },

  "vision_por_canal": {
    "inbound": [
      {
        "canal": "WhatsApp",
        "volumen_total": 5516.89,
        "participacion_a": 0.8187,
        "cts_a": 6531793.18,
        "participacion_b": 0.1813,
        "cts_b": 240192.98,
        "participacion_c": 0.0,
        "cts_c": "No Activado",
        "cts_ponderado": 5391368.03
      }
    ],
    "outbound": [
      {
        "canal": "WhatsApp",
        "volumen_total": 5.0,
        "participacion_a": 1.0,
        "cts_a": 0,
        "participacion_b": 0.0,
        "cts_b": "No Activado",
        "participacion_c": 0.0,
        "cts_c": "No Activado",
        "cts_ponderado": 0
      }
    ],
    "totales": {
      "inbound": { "volumen": 7516.89, "participacion_a": 0.9479, "cts_b": 358700.89 },
      "outbound": { "volumen": 18, "participacion_a": 0.0, "cts_b": 0 }
    }
  },

  "cadena_b_c_por_direccion": {
    "cadena_b": {
      "total_acumulado": 358700885.66,
      "inbound": {
        "total": 358700885.66,
        "componente_humano": 115873573.27,
        "componente_tecnologico": 242827312.38
      },
      "outbound": { "total": 0, "componente_humano": 0, "componente_tecnologico": 0 }
    },
    "cadena_c": {
      "total_acumulado": 0,
      "inbound": { "total": 0, "componente_humano": 0, "componente_tecnologico": 0 },
      "outbound": { "total": 0, "componente_humano": 0, "componente_tecnologico": 0 }
    }
  },

  "reglas_negocio": {
    "costo_total_acumulado": 4822374777.42,
    "reglas": [
      { "id": "margen_objetivo", "label": "Margen objetivo", "pct": 0.1339, "monto": 645715982.70, "status": "ok" },
      { "id": "contingencia_operativa", "label": "Contingencia Operativa", "pct": 0.02, "monto": 96447495.55, "status": "ok" },
      { "id": "contingencia_comercial", "label": "Contingencia Comercial", "pct": 0.0, "monto": 0, "status": "ok" },
      { "id": "markup", "label": "Mark up", "pct": 0.0, "monto": 0, "status": "ok" },
      { "id": "descuento", "label": "Descuento volumen", "pct": 0.0, "monto": 0, "status": "ok" }
    ],
    "valor_total_deal": 5471188699.14
  }
}
```

---

## 13. Tabla de Brechas Priorizadas

| prioridad | brecha | requiere_nuevo_calc | requiere_serializer | requiere_modelo | requiere_param_storage | riesgo |
|-----------|--------|---------------------|---------------------|-----------------|------------------------|--------|
| 🔴 P0 | K50 incorrecto → cts_a, cts_ponderado, participacion_a erróneos | ✅ fix bug | ✅ | — | — | CRÍTICO |
| 🔴 P0 | desglose_a: 10 sub-componentes ausentes | ✅ extend | ✅ | ✅ | — | CRÍTICO |
| 🔴 P0 | desglose_b: 8 sub-componentes ausentes | ✅ extend | ✅ | ✅ | — | CRÍTICO |
| 🔴 P0 | cts_mensual_total (H019) ausente | — | ✅ derivable de pyg | ✅ | — | ALTO |
| 🟡 P1 | participacion_c y cts_cadena_c ausentes | — | ✅ | ✅ | — | MEDIO |
| 🟡 P1 | monetary values reglas_negocio | ✅ extend engine | ✅ | ✅ | — | MEDIO |
| 🟡 P1 | costo_total_acumulado (C186) ausente | — | ✅ | ✅ | — | MEDIO |
| 🟠 P2 | vision_por_canal (sección 04) ausente | ✅ nuevo sub-calc | ✅ | ✅ | — | ALTO |
| 🟠 P2 | cadena_b/c por dirección (sección 06) | ✅ extend | ✅ | ✅ | — | MEDIO |
| 🔵 P3 | visual_detallada_por_canal (sección 05) | ✅ nuevo sub-calc | ✅ | ✅ | — | MEDIO |
| 🔵 P3 | staffing_scenarios (sección 07) | ✅ nuevo calc | ✅ | ✅ | — | BAJO |
| 🔵 P3 | margen_status (N020) | — | ✅ | — | ✅ (límites min/max) | BAJO |

---

## 14. Plan de Implementación (secuencial)

### Fase A: Corregir K50 y expandir DesgloseCTSCadenaA (P0)
1. Fijar `_k50()` en `CostToServeCalculator`: usar volumen ponderado por participación
2. Fijar `_l50()` para consistencia (verificar contra L50 Excel)
3. Expandir `DesgloseCTSCadenaA` con 10 sub-campos
4. Expandir `DesgloseCTSCadenaB` (nuevo) con 8 sub-campos
5. Agregar `DesgloseCTSCadenaC` (nuevo)
6. Calcular todos los sub-campos desde `pyg_por_mes` (la data ya existe en el engine)
7. Agregar `cts_cadena_c`, `participacion_c`
8. Agregar `cts_mensual_total` (H019) = sum avg costs de las 3 cadenas

### Fase B: Serializer y contrato JSON (P0→P1)
1. Expandir `_cost_to_serve_to_dict()` con todos los nuevos campos
2. Agregar `vision_general` wrapper con `k50`, `l50`, `m50`
3. Agregar monetary values a `reglas_negocio`
4. Agregar `costo_total_acumulado` (sum de todos los meses en P&G)

### Fase C: Vision por Canal (P2)
1. Nuevo sub-calculator: `_calcular_vision_por_canal()` en engine
2. Para cada canal activo: atribuir costos A, B, C por participación
3. Nuevo modelo: `CTSPorCanal`, `VisionCTSPorCanal`

### Fase D: Cadena B/C por Dirección (P2)
1. Extender `ParametrosCadenaB` con flag inbound/outbound por canal
2. Calcular `componente_humano` y `componente_tecnologico` por dirección

### Fase E: Staffing Scenarios (P3)
1. Nuevo modelo: `EscenarioStaffing`
2. Calculator: para cada escenario en `condiciones_cadena_a`, recalcular payroll
3. Exposición en `ResultadoCostToServe`

### Fase F: Tests y contratos
1. Tests unitarios para K50 corregido
2. Tests de snapshot para todos los valores vs Excel V2-4
3. Tests de contrato para el nuevo JSON completo
4. Tests de escenarios >12 meses

---

## 15. Invariantes que NO se pueden romper

1. `pyg_por_mes` no cambia — es el input a CTS, no el output
2. Todos los `@property` del `PyGMensual` siguen sin tocar
3. `kpis` no cambia (ingreso_mensual, margen, valor_total_deal son correctos)
4. `7/7 Excel match @ 0.00000%` se preserva — K50 fix solo afecta CTS, no P&G ni KPIs

---

*Documento generado mediante ingeniería inversa exhaustiva de Excel V2-4, hoja "Vision Cost To Serve" (rows 1–268, 118 columnas).*
