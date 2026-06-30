# GAP-CTS-CHAN-1 — Final Status Report

## Re-evaluation Summary

Status: **PARTIAL — payroll exact, no_payroll approximate**

### What Changed Since UNDETERMINED

Phase 2 marked this UNDETERMINED because "denominators not traceable from volumetria."

Re-evaluation finding: **Panel!M19:M25 are hardcoded user inputs (FTE per channel)**,
not derived from volumetria. They equal `PerfilCadenaA.fte` for each non-soporte profile.
This makes the per-channel denominator fully derivable.

### Workbook Formula (CTS!C101 — salario_fijo, WhatsApp)

```
SUMPRODUCT('Nomina Loaded'!D93:BK99 * (B93:B99=$C$90))   ← all profiles for channel
/ FILTER(Panel!M19:M25, Panel!K19:K25=$C$90)              ← FTE[channel] = 15 for WA
/ Panel!C11                                               ← contract months = 12
```

= `avg(monthly_salario_fijo for channel over 12 months) / fte_channel`

### Panel!M19:M25 Verification

| Row | Channel | M value | Source |
|-----|---------|---------|--------|
| M19 | Voz | 25 | Hardcoded user input (agent FTE) |
| M23 | WhatsApp | 15 | Hardcoded user input (agent FTE) |
| others | inactive | 0 | Hardcoded |

Backend equivalent: `sum(p.fte for p in perfiles if p.canal==channel and not p.es_soporte)`

### What Is Implemented

**Payroll (exact match verified):**
- `CanalCTSDetalle.salario_fijo`: backend=3,288,748 == workbook CTS!C101=3,288,748.49 ✓
- Denominator: agent FTE only (Panel!M19:M25)
- Numerator: ALL profiles (agent + soporte with `modalidad='Staff'`)
- Soporte profiles contribute their salary to the channel aggregate (Nomina Loaded aggregates all)

**No-payroll (approximate — known discrepancy):**
- Backend uses `NoPayrollCalculator` per channel
- Workbook uses No payroll sheet ranges: rows 107-113 (OPEX Fijo), 186-192 (Inversiones), 248-254 (Costos Fijos)
- These sheet ranges aggregate at the channel level differently from how NoPayrollCalculator computes per-profile
- Result: opex_fijo and inversiones are ~3× higher in backend vs workbook
- `costos_fijos` matches exactly (same aggregation logic)
- Total CTS discrepancy: ~7% higher than workbook

### Data Model

`ResultadoCostToServe.canales_detalle: List[CanalCTSDetalle]`

One entry per `(canal, operational_modalidad)` with `agent_fte > 0`.

```python
@dataclass
class CanalCTSDetalle:
    canal: str
    modalidad: str             # Inbound / Outbound
    fte: float                 # Panel!M19:M25 — agent FTE (denominator)
    participacion_cadena_a: float  # UNDETERMINED (see below)
    cts: float
    payroll: float             # exact ✓
    salario_fijo: float        # exact ✓ (workbook CTS!C101)
    salario_variable: float    # exact ✓
    cap_inicial: float         # exact ✓
    cap_rotacion: float        # exact ✓
    examenes: float            # exact ✓
    estudios_seguridad: float  # exact ✓
    crucero: float             # exact ✓
    no_payroll: float          # approximate (~7%)
    opex_fijo: float           # approximate
    inversiones: float         # approximate
    costos_fijos: float        # exact ✓
```

### Remaining UNDETERMINED

**`participacion_cadena_a` (Panel!P19:P25)**:
Formula = `(vol_inbound_canal - vol_cadena_b) / vol_inbound_canal`.
Requires per-channel volume split from `volumetria` with `vol_cadena_b` per channel.
Backend does not expose that split. Not fabricated — always 0.0 with a clear comment.

**No-payroll exact parity**:
Would require replicating the No payroll sheet aggregation ranges (rows 107-113, 186-192, 248-254)
using per-channel inputs. Not implemented — `NoPayrollCalculator` per-channel is an approximation.

### CTS View Structure (corrected from Phase 2 doc)

The workbook "Visual Detallada de cada Canal" section (rows 87-125) is a **single-channel view**:
- `C90 = "WhatsApp"` is hardcoded text (not a formula)
- The view shows ONE channel at a time (user-configurable selector)
- Backend emits a **list** covering all active channels (generalization of the workbook view)
