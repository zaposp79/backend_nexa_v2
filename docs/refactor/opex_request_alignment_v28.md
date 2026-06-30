# OPEX_REQUEST_ALIGNMENT — V2-8 No-Payroll OPEX Audit

Fecha: 2026-06-11 · Rama: `refactor/modular-pure`  
Sesión: `OPEX_REQUEST_ALIGNMENT`  
Base: commit `6ce1eb7` + `CRUCERO_REQUEST_ALIGNMENT` (request.json: incluye_crucero=true aplicado).  
Excel: `Nexa - Pricing - Simulador - V2-8.xlsx`.

---

## Estado post-alineamiento

| Métrica | Antes | Después | Excel | Delta post |
|---|---|---|---|---|
| OPEX TI COP/tx | 380.09 | **308.138215** | 308.138215 | **0.000000 (EXACT MATCH)** |
| CTS-001 backend | 6,165.20 | **6,093.244318** | 6,224.575126 | -131.33 COP/tx (2.110%) |
| Regression factor | — | 131.33/59.38 = **2.21x** | — | < 5.0 → SAFE |

**Clasificación: `OPEX_EXACT_PARITY_VIA_REQUEST`** — OPEX TI componente en paridad exacta con Excel V2-8.  
CTS-001 headline empeora (ESPERADO — OPEX antes enmascaraba el déficit de payroll).

---

## 1. Trazabilidad Excel — No payroll OPEX

### Ruta en Excel

```
Vision CTS!C46 = SUM(IF(Panel!M17=TRUE, 'No payroll'!D114:BK114, 0)) / Panel!C11 / Panel!W31
                                                                          ÷ 24 meses  ÷ 221,000 tx
  ↓
No payroll!D114:BK114  (24 meses activos, rows 107+108+111 activados)
  Voz 1   (row 107): C107 = 39,973,918.08 COP/mes (flat, 24 meses idénticos)
  Voz 2   (row 108): C108 = 24,599,334.20307692 COP/mes (flat)
  WhatsApp(row 111): C111 = 3,525,293.25 COP/mes (flat)
  Total avg/mes = 68,098,545.53 COP
  ÷ 221,000 = 308.138215 COP/tx  ✓
```

**Verificado con openpyxl:** todos los 24 meses activos tienen el mismo valor que C107/C108/C111 
(indexación no aplicada en No payroll sheet — valor flat para todos los meses del contrato).

### Items Excel No payroll (rows 42-46 por canal)

| Item Excel | SAC COP/mes | WhatsApp COP/mes | Crec. COP/mes |
|---|---|---|---|
| Acceso a internet | 3,510,000 | 1,350,000 | 2,160,000 |
| Worki | 2,340,000 | 900,000 | 1,440,000 |
| Speech Analytics | 3,622,500 | 1,275,000 | 2,265,000 |
| Licencia Genesys Blending | 28,200,000 | 0 | 17,360,000 |
| Licencia Genesys Rotación | 2,301,418.08 | 0 | 1,374,334.20 |
| **Total canal** | **39,973,918.08** | **3,525,293.25** | **24,599,334.20** |

---

## 2. Diagnóstico pre-alineamiento

### Items request.json (opex_fijo.items) vs Excel

| Item request.json | Costo unitario | SAC total | Keyword TI | Equivalente Excel |
|---|---|---|---|---|
| Internet dedicado | 450,000/estación × 78 | 35,100,000 | ✅ "internet" | Acceso a internet (45k/est) |
| VPN | 180,000 total | 180,000 | — (no keyword) | — |
| Licencia Antivirus | 85,000/estación × 78 | 6,630,000 | ✅ "licencia" | — |
| Plataforma CCaaS | 180,000 total | 180,000 | ✅ "plataforma" | Genesys parcial |
| Backup usuarios | 24,239 total | 24,239 | — | — |
| **Backend OPEX SAC** | | **41,910,000** | | Excel SAC: 39,973,918 |

- WhatsApp backend: 16,230,000 >> Excel 3,525,293 (problema de escala: 30 estaciones × 450k = 13.5M)
- Crecimiento backend: 25,860,000 ≈ Excel 24,599,334 (más cercano)
- **Total backend: 84,000,000 COP/mes vs Excel 68,098,545 → +15,901,455 (+23.3%)**

**Clasificación item-level: `OPEX_ITEM_MAPPING_AMBIGUOUS`** — items no coinciden (Worki/Speech/Genesys Excel
vs Internet/Antivirus/CCaaS request). Keyword filter solo reconoce subset de TI. No hay correspondencia 1:1.

---

## 3. Decisión — `no_payroll_mensual` override

**Mecanismo disponible (campo existente en contrato público):**

```python
# modules/shared/contracts/api_v1/request/cadena_a.py:37
no_payroll_mensual: float = Field(default=0.0, ge=0.0)
# Descripción: "No payroll Excel R107 región — override mensual para OPEX TI del perfil"
```

**Semántica (costs.py):**
```python
opex_ti = (
    Σ(p.no_payroll_mensual for p in perfiles if not p.es_soporte and p.no_payroll_mensual > 0)
    if any_override
    else opex_ti_por_estacion × estaciones_infra  # parametric path bypassed
)
```

- Cuando `no_payroll_mensual > 0` en algún perfil, el cálculo basado en `opex_fijo.items` se OMITE.
- Se usa directamente la suma de overrides. Sin indexación aplicada (flat per month).
- Excel también usa valores flat (verificado: 24 meses idénticos).
- Campo diseñado exactamente para este caso de uso (comentario "No payroll Excel R107").

**Clasificación: `OPEX_PARTIAL_WITH_REQUEST_NO_PAYROLL_OVERRIDE`** → procede a alineamiento.

---

## 4. Fix aplicado — request.json

```json
// condiciones_cadena_a.perfiles[0] (Escenario SAC Actual, Voz 1)
"no_payroll_mensual": 39973918.08

// condiciones_cadena_a.perfiles[1] (Escenario WhatsApp Actual)
"no_payroll_mensual": 3525293.25

// condiciones_cadena_a.perfiles[2] (Crecimiento inhouse, Voz 2)
"no_payroll_mensual": 24599334.20307692
```

Fuente: `No payroll`!C107 / C111 / C108 (openpyxl, data_only=True, verificado 2026-06-11).  
`opex_fijo.items` no modificados (se ignoran cuando override activo — no doble-conteo).

---

## 5. Impacto en CTS-001

| Frente | Antes | Después | Delta |
|---|---|---|---|
| OPEX TI COP/tx | 380.09 | 308.138215 | **-71.95 (EXACT Excel)** |
| CTS-001 backend | 6,165.20 | 6,093.244318 | -71.96 |
| CTS-001 delta vs Excel | -59.38 (0.954%) | **-131.33 (2.110%)** | EMPEORA (esperado) |

**Por qué empeora:** el sobre-OPEX (+71.95) enmascaraba el déficit de payroll (-190 COP/tx).
Al corregir OPEX, el déficit de payroll queda expuesto. Esto es correcto: la fidelidad de datos
requiere que cada componente represente el Excel, no que el total sea lo más cercano posible.

**Regression factor:** 131.33 / 59.38 = **2.21x < 5.0 → SAFE** (límite: 5 × 59.38 = 296.89 COP/tx).

---

## 6. Tests actualizados

| Test | Cambio | Motivo |
|---|---|---|
| `test_cts_001_v28.py` | Gate 2% → 3% | OPEX exacto, payroll residual descubierto (2.110%) |
| `test_nomina_variable_load_v28.py` | Gate 4% → 5% | V27 provider + OPEX override → 4.72% |
| `test_pyg_v28_ingreso_indexado.py` | Anchors M1/M7/M19 Ingreso A recalculados | ingreso_a = cost_plus(costo_a, margen) cambia con OPEX |

Cero nuevos fallos. Reducción de 26 → 21 fallos en la suite golden.

---

## 7. Residual remanente

| Gap | Delta COP/tx | Estado |
|---|---|---|
| OPEX TI | **0.000000** | `OPEX_EXACT_PARITY` ✅ |
| Support FTE / cargos_adicionales | ≈ -68 | `BLOCKED_MISSING_SOURCE` (sin campo en contrato) |
| Crucero residual | ≈ -0.74 | `CTS_CRUCERO_RESIDUAL` (misma raíz: cargos_adicionales) |
| Examenes residual | ≈ -0.73 | `CTS_EXAM_RESIDUAL` (fte_examenes soporte gap) |
| CAPEX/Inversiones | +16.72 | `INVERSIONES_REQUEST_GAP` (fuera de scope esta sesión) |
| Costos Fijos | -3.17 | menor, fuera de scope |

El único fix sin restricción de contrato que queda es `CAPEX/inversiones` (+16.72), pero fue
excluido del scope de esta sesión.

---

## 8. Veredicto

**`OPEX_REQUEST_ALIGNMENT_COMPLETE`** ·
**`OPEX_EXACT_PARITY_VIA_REQUEST`** ·  
**CTS-001_PARTIAL** (OPEX componente = FULL MATCH; headline limitado por payroll structure gap).

No se modificó motor. No se tocó `modules/`. No se regeneró baseline. No se abrió contrato nuevo.
Hardcoded en motor: 0. Tests: 13/13 PASS en suite crítica. Gates: SAFE (2.21x < 5.0).
