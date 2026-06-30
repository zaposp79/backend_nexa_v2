# CTS-001 INPUT_DEAL_MATCH — V2-8 METROCUADRADO SAC

> ⚠️ **CORRECCIÓN (2026-06-11):** La sección "Residual gap breakdown" de abajo (en especial
> el "CAPEX month-1 spike +119.72" y "no-payroll steady -34.26") fue **MAL diagnosticada**.
> El desglose real de no-payroll (Excel `Vision Cost To Serve`!C46-C48) es: OPEX Fijo +71.95,
> Inversiones/CAPEX +16.72, Costos Fijos -3.17. Excel SÍ amortiza CAPEX (C47=103.04 ≠ 0).
> Ver `docs/refactor/cts_residual_structural_audit_v28.md` para el desglose verificado y la
> matriz de clasificación. Además, el gap de payroll soporte NO es solo SENA/Incl: el grueso
> (~-138) es DOTACIÓN de FTE soporte (Excel ~71 vs backend 61.4).

## Status: CTS-001_PARTIAL_BEST (1.847% delta)

**Backend best:** 6,109.624708 COP/tx
**Excel anchor:** 6,224.575126 COP/tx (Vision CTS!C34)
**Delta:** -114.950418 COP/tx | -1.847%

## What was done

Scope: `tests/refactor/_v28_deal_provider.py` created. Patches ALL 20 regular
staff roles (W39-W58, 'Inputs de Nomina' column W) via `costo_empresa_override`
in the HR nomina data. Applies accent-stripped alias rows to work around the
engine's `.strip().lower()` lookup (no NFKD normalization in `provider_fin_op.py`).

Before: CTS = 5,992.50 COP/tx (V27 provider, delta = -232.07, 3.729%)
After:  CTS = 6,109.62 COP/tx (v28 deal provider, delta = -114.95, 1.847%)
Improvement: +117.12 COP/tx closed by the all-staff overrides.

## Residual gap breakdown

### 1. Payroll gap: -200.45 COP/tx (backend payroll 1,162.88M vs Excel 1,207.18M/month)

All 20 regular staff correctly overridden. Remaining gap is from SENA/Inclusión:
- `Aprendiz SENA`: engine uses `calcular_aprendiz(1,423,500)` = 2,084,268.54/FTE
- `Inclusión`: same formula, same base
- Excel implied base: ~1,749,203 COP (83.3% of SMMLV 2,100,000)
- No standard pct formula matches this (75%=1,575,000 → 2,274,900; 100%=2,100,000 → 2,935,506)

**Root cause:** Active HR upload has SENA salary = 1,423,500 (2025 SMMLV) while the
Excel V2-8 deal uses a higher base. Not fixable without knowing the exact Excel
SENA base, which is a deal-specific input not available in current `request.json`.

SENA FTE: 15.1554 total (3 channels × FTE = 7.58 + 2.91 + 4.66)
Inclusión FTE: 3.1826 total
Monthly gap from SENA+Incl: ~(15.1554+3.1826) × (Excel_cargado - 2,084,268.54)

### 2. No-payroll steady-state gap: -34.26 COP/tx (month 2+)

Month 2 no_payroll = 160.88M → 727.96 COP/tx vs Excel 762.22 COP/tx.
Some no-payroll component (infrastructure, exams, or other OPEX) is below
Excel's steady-state value. Not investigated further (requires knowing Excel
VCS!C46-C48 cell breakdown).

### 3. CAPEX month-1 spike: +119.72 COP/tx (inflates average)

Month 1 no_payroll = 796.08M (includes CAPEX setup), months 2-24 = 160.88M.
CTS calculator averages all 24 months → month-1 spike adds 119.72 COP/tx to average.
Excel VCS appears to show steady-state (constant) CTS = 762.22 for no-payroll.
Fix would require changing the CTS average computation in `modules/` → **out of scope**.

### Net: -200.45 - 34.26 + 119.72 = -114.99 ≈ -114.95 COP/tx ✓

## Kill-switch rationale

All three residual gap components require either:
- `storage/parametrization/` changes (SENA salary correction in active HR)
- `modules/` changes (CAPEX averaging in CTS calculator, or SENA override mechanism)
- Deal-level input data not currently in `request.json` (SENA salary from Excel)

Kill-switch "se requiere tocar modules/ → STOP" applies. CTS-001 closes as PARTIAL_BEST.

## Artifacts

- Provider: `tests/refactor/_v28_deal_provider.py`
- Golden test: `tests/golden/test_cts_001_v28.py` (< 3% gate, best = 1.847%)
- Previous evidence: `docs/refactor/cts_001_v28_evidence.md`, `cts_salary_audit_v28.md`
