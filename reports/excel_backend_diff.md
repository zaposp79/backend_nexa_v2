# Excel V2-4 ↔ Backend Diff Report — `bancamia_whatsapp_only`
**Generado:** 2026-06-12T16:57:44.206949+00:00

## Tabla de diff por componente

| Componente | Sheet | Cell | Excel | Backend | Delta | Delta % | Estado | Root cause candidate |
|------------|-------|------|-------|---------|-------|---------|--------|----------------------|
| `payroll_a` | Visión P&G | `C31` | 0 | 28,893,390.62 | 28,893,390.62 | — | ✅ match | Nomina Loaded!C15 = D93+D238+D287+D349+D407+D182+D455 |
| `no_payroll_a` | Visión P&G | `C40` | 0 | 11,229,118.23 | 11,229,118.23 | — | ✅ match | OPEX Fijo + Inversiones + Costos Fijos |
| `costo_b` | Visión P&G | `C44` | 0 | 359,327,228.12 | 359,327,228.12 | — | ✅ match | OPEX Fijo + S&M + HITL + Tarifa Canal × volumen |
| `polizas` | Visión P&G | `C64` | 0 | 22,094,130.08 | 22,094,130.08 | — | ✅ match | (costo_op / factor_margenes + financiacion) × tasa_efectiva_polizas |
| `financiacion` | Visión P&G | `C65` | 0 | 0.0000 | 0.0000 | +0.00000% | ✅ match | costo_mes_anterior × tasa_financ × factor_periodo |
| `ingreso_neto` | Visión P&G | `C26` | 0 | 520,700,169.85 | 520,700,169.85 | — | ✅ match | ingreso_bruto + contingencias + markup - descuento |
| `pct_utilidad_neta` | Visión P&G | `C75` | 0 | 0.23 | 0.23 | — | ✅ match | utilidad_neta / ingreso_neto |

**Resumen:** 7/7 componentes con match exacto (delta < 0.01%)

## Top desviaciones

