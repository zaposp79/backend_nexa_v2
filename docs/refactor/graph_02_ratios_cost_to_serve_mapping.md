# Graph 2 — Ratios Cost to Serve: Excel → Backend Mapping

**Target:** `Graficos!P4:BH29`  
**Status:** STEP_02_IMPLEMENTED — Block A (P4:AF29) and Block B (AR4:BH29) done. Cargos Adicionales deferred.

**Denominator rule:** `SUMIFS(col, roles, "<>"&"Agente Básico 1")` — excludes "Agente Básico 1" from column sum only; its own ratio row is still computed normally.  
**selected_ratio_column:** Always "Total" (VCT!C125 = "Total" static). `ratio_actual` = BH column ratios.  
**Cargos Adicionales (P29/Q29:AE29):** Deferred — backend source (Nomina Loaded reducers) not confirmed.  
**Session:** GRAPH_02_RATIOS_COST_TO_SERVE_MAPPING  
**Date:** 2026-06-14

---

## 1. Executive Verdict

Graph 2 is **implementable** but requires a new intermediate output from `NominaCalculator`: per-role loaded cost per scenario. The core computation already runs inside the engine (`NominaCalculator._calcular_perfil` is called per profile per month). The gap is that these intermediate per-profile costs are summed into a canal aggregate and never accumulated into a per-role × per-scenario matrix.

**Implementation complexity:** Medium-high. No new formula layer is needed — the calculation already exists — but a new result model and accumulation loop are required. Graph 2 must NOT be implemented until this mapping is approved.

---

## 2. Excel Source Map

```
GRAPH_02_EXCEL_MAP

graph name:     Ratios Vision Cost To Serve
source sheet:   Graficos
source range:   P4:BH29
sub-blocks:
  Block A — Absolute costs:  P4:AF29
  Lookup block:              AH4:AN29
  Block B — Ratios:          AR4:BH29
header rows:
  Row 4: scenario headers (ArrayFormula FILTER from Condiciones Cadena A!E8:S8)
  P4="Rol", AF4="Total", AN4="CATEGORIA", AR4="Rol", BH4="Total"
category rows:
  AH5:AH28 = ArrayFormula: =FILTER($AN$5:$AN$28, $AM$5:$AM$28=AI5)
  → values: "Operaciones", "Recursos humanos", "Otros" (static label table in AM:AN)
role rows:
  P5:P28  = 'Condiciones Cadena A'!D104:D123 + D123..D127 (20 roles from CCA)
  AR5:AR29 = ArrayFormula: =P5:P29 (mirror of P column)
  Note: P5:P28 references Condiciones Cadena A!D104 through D123 (20 rows).
        Rows 25-28 source additional roles (Validador, Aprendiz SENA, Inclusión, Especialista).
special row:
  P29 = "Cargos Adicionales" (hardcoded static label)
formula cells:
  Q5:AE28  = IF(col_header<>"", SUMIFS(NL!col$43:col$66, NL!$B$43:$B$66, $P5)
                                + SUMIFS(NL!col$155:col$178, NL!$B$155:$B$178, $P5), 0)
             where NL = 'Nomina Loaded', col shifts C→D→E per scenario
  Q29:AE29 = ='Nomina Loaded'!C81  (direct ref, per scenario column: C→D→E)
  AF5:AF29 = =SUM(Q5:AE5)  (row total across all scenario columns)
  AS5:BG28 = =Q5/SUMIFS(Q$5:Q$29,$P$5:$P$29,"<>"&$AR$24)
             denominator = column sum excluding "Agente Básico 1" (P24=AR24)
  BH5:BH29 = =AF5/SUMIFS(AF$5:AF$29,$P$5:$P$29,"<>"&$AR$24)
  AJ5:AJ28 = =IFERROR(INDEX($AS$5:$BH$29, MATCH(AI5,$AR$5:$AR$29,0),
                             MATCH('Vision Cost To Serve'!$C$125,$AS$4:$BH$4,0)), 0)
             → picks ratio column matching the label in VCT!C125

array formulas present:
  Q4  = FILTER('Condiciones Cadena A'!$E$8:$S$8, E8:S8<>"")  [scenario headers]
  AS4 = same as Q4 (mirrored for Block B)
  AH5 = FILTER($AN$5:$AN$28, $AM$5:$AM$28=AI5)               [category lookup]
  AR5 = =P5:P29                                                [role mirror]
  B69 of Nomina Loaded = ArrayFormula (Reductor 1 dynamic aggregation)
  B70 of Nomina Loaded = static "Reductor 2"; cols C-E = ArrayFormula sums

named ranges: none found relevant to P4:BH29

Vision Cost To Serve!C125:
  value = "Total" (static hardcoded string, not a formula result)
  → AJ lookup always selects the BH (Total) column of Block B

referenced sheets:
  - 'Condiciones Cadena A' → E8:S8 (scenario labels), D104:D123 (role names)
  - 'Nomina Loaded'        → B43:B66, C43:E66 (section 1 costs), B155:B178, C155:E178 (section 2),
                             B69:B80 (reducers: Reductor 1 + Reductor 2), C81:E81 (Cargos Adicionales aggregates)
  - 'Vision Cost To Serve' → C125 (= "Total" static)

confidence: HIGH
```

---

## 3. Formula/Range Table

| Range | Type | Formula / Source | Backend analog |
|---|---|---|---|
| Q4 (header) | ArrayFormula | `FILTER('CCA'!E8:S8, E8:S8<>"")` | `escenario.canal + modalidad` label |
| P5:P28 | Ref | `='Condiciones Cadena A'!D104` .. D123 | Role names from HR parametrization |
| P29 | Static | `"Cargos Adicionales"` | `cargos_adicionales` FTE input → cost |
| Q5:AE28 | Formula | `SUMIFS(NL!col$43:66,NL!$B$43:66,$P5) + SUMIFS(NL!col$155:178,...)` | **GAP: per-role cost not exposed** |
| Q29:AE29 | Direct ref | `='Nomina Loaded'!C81` (= SUM reducers C69:C80) | **GAP: Cargos Adicionales cost not in PricingResult** |
| AF5:AF29 | Formula | `SUM(Q5:AE5)` | Derivable from Block A |
| AH5:AH28 | ArrayFormula | `FILTER($AN$5:$AN$28,$AM$5:$AM$28=AI5)` | Static constant table per role |
| AJ5:AJ28 | Formula | `INDEX(ratios, MATCH(role, roles, 0), MATCH(VCT!C125, headers, 0))` | Lookup into Block B, always "Total" col |
| AS5:BG28 | Formula | `Q5/SUMIFS(Q$5:Q$29,$P$5:$P$29,"<>"&$AR$24)` | Derivable once Block A exists |
| BH5:BH29 | Formula | `AF5/SUMIFS(AF$5:AF$29,...,"<>"&$AR$24)` | Derivable once Block A exists |

**Section 1 of Nomina Loaded (`B43:B66`, `C43:E66`):**  
Loaded total monthly cost per role per scenario. Each cell already computed from `Inputs de Nomina` sheet (salary × FTE × loading factor). Maps to `NominaCalculator._calcular_perfil` results.

**Section 2 of Nomina Loaded (`B155:B178`, `C155:E178`):**  
Additional costs (SENA, complementary). Currently maps to SENA-type profiles (`APRENDIZ_SENA` cargo_tipo) in the backend.

**Cargos Adicionales (`Nomina Loaded!C81:E81`):**  
`=SUM(C69:C80)` — aggregates Reductor 1 + Reductor 2 + blanks.  
Reductor 1 (`B69` = ArrayFormula) appears to capture the cost of the `cargos_adicionales` FTE input. Not currently exposed as a separate cost line in `PricingResult`.

---

## 4. Dependency Map

| Dependency | Excel source | Business meaning | Backend candidate | Confidence |
|---|---|---|---|---|
| Scenario labels | `CCA!E8:S8` | Active deal scenarios ("Escenario SAC Actual", etc.) | `PerfilCadenaA.canal` + `.modalidad` → label reconstruction | MEDIUM |
| Role list (24 roles) | `CCA!D104:D123 + ext` | HR roles defined for the deal | `PerfilCadenaA.nombre` (per profile) — role name = nombre for support profiles | HIGH |
| Per-role loaded cost, section 1 | `NL!C43:E66` | Monthly loaded payroll cost (salario cargado × FTE × factor) | `NominaCalculator._calcular_perfil()` intermediate — NOT surfaced per-role | MEDIUM |
| Per-role cost, section 2 | `NL!C155:E178` | SENA/complementary cost per role | `NominaCalculator._calcular_perfil()` for APRENDIZ_SENA profiles | MEDIUM |
| Cargos Adicionales cost | `NL!C81` = SUM reducers | FTE cargos_adicionales translated to COP cost | Derived from `cargos_adicionales × ratio` support cost — **not directly in output** | LOW |
| Denominator (excl. Agente Básico 1) | `SUMIFS(col, roles, "<>"&$AR$24)` | Column total excluding principal agent role | Derivable: `sum(per_role_costs) - cost["Agente Básico 1"]` | HIGH |
| Category per role | `AH col = FILTER(AN, AM=AI)` | Operaciones / Recursos humanos / Otros | Static constant map (no backend equivalent needed) | HIGH |
| Current scenario label | `VCT!C125 = "Total"` (static) | Which scenario column AJ picks | Fixed: always "Total" | HIGH |

---

## 5. Backend Equivalent Map

### Existing values

| Value | Location | Notes |
|---|---|---|
| Aggregate nomina per canal per month | `EscenarioCanalFacts.nomina_por_mes[].total` | Sum across all roles, not per-role |
| Per-profile nomina (intermediate) | `NominaCalculator._calcular_perfil(perfil, mes)` | Called inside `calcular_para_mes` loop — result is added to aggregate, not stored |
| Profile role name | `PerfilCadenaA.nombre` | For support profiles, nombre encodes the role (e.g. "Soporte — Supervisor") |
| Canal / scenario label | `PerfilCadenaA.canal` + `.modalidad` | Partially reconstructs Excel scenario label |
| `cargos_adicionales` | `PerfilCadenaA.cargos_adicionales` | FTE input modifier — NOT a cost output |
| Category of role | — | Not stored; is a static lookup table (Operaciones/RR.HH./Otros) |

### Missing values (gaps)

| Gap ID | Value needed | Classification |
|---|---|---|
| **G1** | `Dict[str, Dict[str, float]]` = `{rol_nombre: {escenario_label: total_cargado_mes_1}}` | `MISSING_INTERMEDIATE_OUTPUT` |
| **G2** | Scenario label string ("Escenario SAC Actual") per (canal, modalidad) | `MISSING_INTERMEDIATE_OUTPUT` — label not stored |
| **G3** | Cargos Adicionales as monthly COP cost per scenario | `MISSING_INTERMEDIATE_OUTPUT` — only FTE exists in output |
| **G4** | Role → Category mapping (Operaciones / Recursos humanos / Otros) | `EXCEL_ONLY_UNMAPPED` — static table, can be a constant in code |

### Gap detail

**G1 — per-role loaded cost:**  
`NominaCalculator.calcular_para_mes()` iterates `perfiles` and calls `_calcular_perfil(p, mes)` for each, returning one `ResultadoNomina` per profile. The results are summed into one aggregate. No per-profile/per-role accumulation is done. A new method `calcular_desglose_por_rol(perfiles, mes) -> Dict[str, float]` that returns `{perfil.nombre: resultado.total}` would cover this, without changing existing behavior.

**G2 — scenario label:**  
`PerfilCadenaA.canal = "SAC"`, `.modalidad = "Inbound"` — the Excel label "Escenario SAC Actual" is a free-text label in `CCA!E8:S8`, not stored anywhere. The mapping `(canal, modalidad) → scenario_label` is implicitly defined by `CCA!E8:S8` order. For graph rendering, the label can be reconstructed as `f"Escenario {canal} {modalidad}"` or stored on `PerfilCadenaAInput.nombre` if needed.

**G3 — Cargos Adicionales COP cost:**  
In the Excel, `Nomina Loaded!B69` (Reductor 1) is an ArrayFormula that aggregates the cost of the additional FTE (`cargos_adicionales` field) across support roles. The backend computes this cost inside `context_builder_perfiles_soporte_mixin.py` at profile-build time (line ~206: `fte_base_soporte = fte_base + perfil_base.cargos_adicionales`), but the resulting COP cost is never stored separately. It can be derived at graph-build time as the difference between total support cost with and without `cargos_adicionales`.

**G4 — Role category (static):**  
The AH column in Excel is `FILTER($AN$5:$AN$28, $AM$5:$AM$28=AI5)` — a lookup against a static table in columns AM/AN. The table is hardcoded in the Excel. A Python constant dict `ROL_CATEGORIA = {"Director de cuentas": "Operaciones", ...}` handles this with zero parametrization dependency.

---

## 6. Recommended Implementation Plan

### Ownership

```
modules/calculator_motor/formulas/graphics/
  graph_02_ratios_cost_to_serve.py   ← new file (formulas only)
  models.py                          ← extend: add GraficoRatiosCTSResult

modules/calculator_motor/formulas/payroll/
  nomina.py                          ← extend: add calcular_desglose_por_rol()

modules/vision_imprimible/builders/
  vision_datasets_builder.py         ← extend: _build_graficos() calls graph_02
```

### Result path (consistent with Graph 1)

```python
PricingResult.datasets_vision.graficos.ratios_cost_to_serve: Optional[GraficoRatiosCTSResult]
```

### New model (draft, subject to approval)

```python
@dataclass
class EscenarioCostoRoles:
    escenario_label: str                     # "Escenario SAC Actual"
    costos_por_rol: Dict[str, float]         # {rol_nombre: total_cargado_mes_1}
    cargos_adicionales: float                # Nomina Loaded row 81 equivalent

@dataclass
class GraficoRatiosCTSResult:
    roles: List[str]                                    # ordered: P5:P28
    categorias: Dict[str, str]                          # {rol: "Operaciones"|"RR.HH."|"Otros"}
    escenarios: List[EscenarioCostoRoles]               # one per active scenario
    total_por_rol: Dict[str, float]                     # {rol: sum across scenarios} = AF col
    ratios_por_escenario: Dict[str, Dict[str, float]]   # {escenario: {rol: ratio}}
    ratios_total: Dict[str, float]                      # {rol: total_ratio} = BH col
    ratio_actual: Dict[str, float]                      # AJ col (always "Total" col = ratios_total)
    agente_basico_excluido: str = "Agente Básico 1"     # denominator exclusion role
```

### Files to add or change

| File | Change | Risk |
|---|---|---|
| `formulas/payroll/nomina.py` | Add `calcular_desglose_por_rol(perfiles, mes) -> Dict[str, float]` | Low — new method, doesn't touch existing `calcular_para_mes` |
| `formulas/graphics/models.py` | Add `EscenarioCostoRoles`, `GraficoRatiosCTSResult`; add field to `GraficosResult` | Low — additive |
| `formulas/graphics/graph_02_ratios_cost_to_serve.py` | New file: `build_ratios_cost_to_serve(escenarios_perfiles, calc_nomina) -> GraficoRatiosCTSResult` | Medium — new logic |
| `vision_imprimible/builders/vision_datasets_builder.py` | Call graph_02 builder from `_build_graficos()` | Low — additive |
| `tests/unit/test_graph_02_ratios_cts.py` | New test with verified Excel values (section 8) | Low |

### Tests

Minimum test set:
1. `TestDesglosePorRol` — `NominaCalculator.calcular_desglose_por_rol()` returns correct `{nombre: total}` per profile.
2. `TestRatiosDenominator` — denominator excludes "Agente Básico 1" correctly.
3. `TestRatioBH29` — Cargos Adicionales ratio = 0.2033 for Total column (verified value).
4. `TestEscenarioLabelMapping` — (canal, modalidad) → label reconstruction.
5. `TestGraficoRatiosCTSBuilder` — end-to-end with mock profiles, verifies shape of result.

---

## 7. Verified Excel Values (from cached data)

For the canonical deal (`request.json` + active OP):

**Block A — Absolute costs (Total = AF column):**

| Role | AF total (COP) |
|---|---|
| Director de cuentas | 12,224,539.88 |
| Director de Performance | 21,927,455.77 |
| Jefe de Operación | 13,656,798.63 |
| Supervisor | 73,767,312.82 |
| Agente Básico 1 | 925,853,204.28 |
| Aprendiz SENA | 39,738,285.01 |
| Especialista de Proyectos | 466,627.31 |
| Cargos Adicionales | 52,936,753.40 |

**Block A — Per-scenario (Director de cuentas, row 5):**

| Scenario | Cost (COP) |
|---|---|
| Escenario SAC Actual (Q) | 6,213,243.56 |
| Escenario WhatsApp Actual (R) | 2,187,761.82 |
| Crecimiento inhouse (S) | 3,823,534.50 |

**Block B — Ratios (Total col = BH), selected:**

| Role | BH ratio |
|---|---|
| Director de cuentas | 0.04695 |
| Director de Performance | 0.08422 |
| Supervisor | 0.28333 |
| Cargos Adicionales | 0.20332 |

**Denominator (Total col, excluding Agente Básico 1):**  
`SUM(AF5:AF29) - AF24` = total_all - 925,853,204.28

**VCT!C125 = "Total"** (static string, hardcoded — AJ always picks BH column).

**Scenario column mapping:**

| Col | Label |
|---|---|
| Q / AS | Escenario SAC Actual |
| R / AT | Escenario WhatsApp Actual |
| S / AU | Crecimiento inhouse |
| T:AE / AV:BG | Empty (0 / #DIV/0! — no more active scenarios) |
| AF / BH | Total |

---

## 8. Risks and Deferred Items

| Risk | Severity | Notes |
|---|---|---|
| Scenario label reconstruction | Medium | "Escenario SAC Actual" ≠ `canal="SAC"`. Label format must be confirmed against CCA!E8:S8 content. Could use a static map or store label on request. |
| Nomina Loaded section 2 mapping | Medium | `NL!B155:B178` = same role names but section 2 covers SENA/complementary costs. Backend profiles with `APRENDIZ_SENA` must contribute to `"Aprendiz SENA"` role bucket. |
| Cargos Adicionales → Reductor 1 math | Medium | Excel Reductor 1 is an ArrayFormula with non-trivial aggregation. Backend equivalent is `fte_base_soporte × (cargos_adicionales / fte_base) × salario_cargado` — needs verification against NL!C81 value (32,770,371 for SAC). |
| `#DIV/0!` in inactive scenario columns | Low | AV:BG show `#DIV/0!` for zero-denominator columns. Backend must guard: if denominator=0 → ratio=0 or None. |
| 24 vs 20 roles source discrepancy | Low | P5:P28 maps to 24 roles but CCA!D104:D123 = 20. Rows P25:P28 (Validador, Aprendiz SENA, Inclusión, Especialista de Proyectos) come from additional CCA rows D124:D127. Must verify all 24 are in backend profile set. |

---

## 9. Checkpoint

```
CHECKPOINT_REQUIRED

No Graph 2 code was implemented.
No runtime code was changed.
No storage, Excel, request, golden fixtures, or baselines were modified.
Only docs/refactor/graph_02_ratios_cost_to_serve_mapping.md was created/updated.
Implementation must not start until this mapping is reviewed and approved.
```

---

## 10. STEP 03 — Wired to datasets_vision.graficos.ratios_cost_to_serve

**Status:** ✅ COMPLETE

**Result path:** `PricingResult.datasets_vision.graficos.ratios_cost_to_serve`

**Implementation notes:**
- `VisionDatasetsBuilder._build_graficos()` now calls `build_ratios_cost_to_serve()` after building Graph 1.
- `NominaCalculator` is constructed locally from `solicitud.parametros_nomina` + `solicitud.parametros_calculo` (same pattern as `engine.py:740`).
- Input sources: `solicitud.perfiles_cadena_a`, `solicitud.escenarios`, `mes=1`.
- Graph 2 is skipped (set to `None`) when `solicitud.escenarios` or `solicitud.perfiles_cadena_a` is empty.
- No new formulas implemented — reuses `build_ratios_cost_to_serve()` from Step 01/02.
- Graph 1 (`bandas_vision_final`) is preserved and unchanged.

**Persistence:** `DatasetsVision.as_dict()` → `GraficosResult.as_dict()` already serializes `ratios_cost_to_serve`; no additional persistence code needed.

**Public endpoint exposure:** `datasets_vision.graficos.ratios_cost_to_serve` is included in the serialized `PricingResult` and returned through existing result endpoints (backward-compatible optional field).

**Tests added:** `TestVisionDatasetsBuilderGraph02Wiring` (5 tests) in `tests/unit/test_graph_02_ratios_cts.py`.
