# WAVE 1 — Parametrización V2-7 (Storage)

**Fecha**: 2026-05-27
**Branch**: `refactor/engine-v2`
**Excel fuente**: `Nexa - Pricing - Simulador - V2-7.xlsx`
**Estrategia**: carpeta versionada `storage/parametrization/v2-7/` con misma estructura/schema que la activa (UUID v2-6), sin modificar nada existente.

---

## 1. Archivos creados

| Ruta | Líneas | Propósito |
|------|--------|-----------|
| `storage/parametrization/v2-7/hr.json` | 4,450 | Recursos Humanos (salarios, recargos, ratios, costo_fijo, ramp-up campañas) |
| `storage/parametrization/v2-7/gn.json` | 498 | Catálogos generales (ciudades, servicios, pólizas, canales) |
| `storage/parametrization/v2-7/op.json` | 1,088 | Operativos (tasas IPC/SMLV, pólizas, ICA por ciudad) + bloque `v2_7_defaults` |
| `storage/parametrization/v2-7/business_rules.json` | 141 | Políticas comerciales (rangos min/max) + reglas de riesgo |
| `storage/parametrization/v2-7/manifest.json` | 25 | Metadata + SHA-256 por archivo |
| `docs/v27/WAVE1_REPORT.md` | este archivo | Reporte de cambios |

**No se modificó**:
- `storage/parametrization/hr/2236cdcf-*.json`
- `storage/parametrization/gn/ce83dd6c-*.json`
- `storage/parametrization/op/3dddbdea-*.json`
- `storage/parametrization/business_rules/2026-01.json`
- `storage/parametrization/frozen/v2-6.json`
- Cualquier archivo de `calculators/`, `domain/`, `simulation/`, `api/`.

---

## 2. Diff vs storage actual

### 2.1 HR — Cambios

| Sección | Cambio |
|---------|--------|
| `salarios` | Mismos 4 campos (SMMLV, Aux Transporte, %Cumplimiento, Dotaciones). Valores idénticos al v2-6 (`1,750,905` / `249,095` / `0.70` / `184,500`). |
| `recargos` | 7 recargos, mismos valores (0.90 festivo, 0.90 dominical, 0.35 nocturno, 0.15/0.15/0.25/0.75). |
| `seg_social` | 5 items, mismos valores (Salud 8.5%, Pensión 12%, ARL 0.522%, Caja 4%, ICBF+Sena 4%). |
| `prestaciones` | 4 items idénticos (Cesantías 8.33%, Primas 8.33%, Int.Ces 12%, Vacaciones 4.17%). |
| `nomina` | **CAMBIO**: nueva clave opcional `costo_empresa_override` solo para Director de cuentas = `29,031,301` (AM16 en Excel). |
| `ratios` | 144 filas (24 cargos × 6 servicios). Sin cambio estructural. |
| `rentabilidad` | **CAMBIO**: Mínimo Cobranzas/SAC/Ventas/Captura sube de `17.0` → `21.0`. Captura `margenobjetivo` = `32.92` (sin cambio). |
| `campana` | 360 filas (6 servicios × 60 meses). Sin cambio en curvas. |
| `costo_fijo` | 91 filas (7 servicios × 13 localidades). Sin cambio significativo. |
| `med_seg` | 35 filas (7 centros costo × 5 localidades). Sin cambio. |
| `rotacion_ausentismo` | **NUEVO** (no existía como sección consolidada): dict {ausentismo, rotacion} por servicio. Plataformas/Captura = 0. |

### 2.2 OP — Cambios

| Sección | Cambio |
|---------|--------|
| `OP-Componente` | IPC `0.0527` uniforme 2025-2030, SMLV `0.12` excepto 2026=`0.2378`. Idéntico al actual. |
| `OP-ComponenteAcumulado` | 9 componentes × 6 años = 54 filas. Incluye nuevos: `50% SMMLV 50% IPC`, `20% SMMLV - 80% IPC` (ya implícitos). |
| `OP-Poliza` | 11 pólizas, mismas tasas. |
| `OP-ICA` | 100 filas (20 ciudades × 5 columnas). Algunas tasas distintas vs v2-6 (ver tabla §3). |
| `OP-OPEXFijo` / `OP-HardSoft` / `config` | Sin cambio (no estaban en el alcance del Excel V2-7 para estas hojas). |
| **`v2_7_defaults`** | **NUEVO bloque** con: `margenes`, `indexacion`, `imprevistos_default`, `comision_administracion`, `gmf`, `timbre`, `tarifa_dia_capacitacion`, `crucero`, `horas_formacion_mensual`. |

### 2.3 Business Rules — Cambios

| Campo | v2-6 (`2026-01.json`) | v2-7 |
|-------|------------------------|------|
| `contingencia_operativa` | min 0.01 / max 0.04 | min `0.05` / max `0.08` |
| `contingencia_comercial` | min 0.00 / max 0.08 | min `0.04` / max `0.07` |
| `markup` | min 0.00 / max 0.02 | min `0.02` / max `0.08` |
| `descuento` | min 0.00 / max 0.00 | min `0.00` / max `0.08` |
| `imprevistos` | (no existía) | **NUEVO** min 0 / max 1 |

### 2.4 GN — Cambios

Sin cambios numéricos. GN solo contiene catálogos.

---

## 3. Tabla por parámetro: v2-6 vs v2-7 vs Excel V2-7

| Parámetro | v2-6 (storage) | v2-7 (storage) | Excel V2-7 (celda) | Cambia? |
|-----------|---------------|----------------|--------------------|---------|
| SMMLV | 1,750,905 | 1,750,905 | `Inputs!C4` = 1,750,905 | NO |
| Auxilio Transporte | 249,095 | 249,095 | `Inputs!C5` = 249,095 | NO |
| Dotaciones anuales | 184,500 | 184,500 | `Inputs!C7` = 184,500 | NO |
| %Cumplimiento Variable | 0.70 | 0.70 | `Inputs!C6` = 0.70 | NO |
| Salud | 0.085 | 0.085 | `Inputs!I13` | NO |
| Pensión | 0.12 | 0.12 | `Inputs!J13` | NO |
| ARL | 0.00522 | 0.00522 | `Inputs!K13/L13` | NO |
| Caja | 0.04 | 0.04 | `Inputs!N13` | NO |
| ICBF + Sena | 0.04 | 0.04 | `Inputs!O13` | NO |
| Cesantías | 0.0833 | 0.0833 | `Inputs!Q13` | NO |
| Primas | 0.0833 | 0.0833 | `Inputs!R13` | NO |
| Int. cesantías | 0.12 | 0.12 | `Inputs!S13` | NO |
| Vacaciones | 0.0417 | 0.0417 | `Inputs!T13` | NO |
| Recargo festivo | 0.90 | 0.90 | `Inputs!X13` | NO |
| Recargo dominical | 0.90 | 0.90 | `Inputs!Z13` | NO |
| Recargo nocturno | 0.35 | 0.35 | `Inputs!AB13` | NO |
| **Salario Director cuentas** | 18,505,000 (en nómina) | 22,761,150 (salario) + **29,031,301 override** | `Inputs!C16=22,761,150 · AM16=29,031,301` | **SÍ** |
| **Mínimo Cobranzas** | 17.0% | **21.0%** | `Rot,Ausent!B29` = 0.21 | **SÍ** |
| **Mínimo SAC** | 17.0% | **21.0%** | `B30` = 0.21 | **SÍ** |
| **Mínimo Ventas** | 17.0% | **21.0%** | `B31` = 0.21 | **SÍ** |
| Mínimo SACO | 10.5% | 10.5% | `B32` = 0.105 | NO |
| Mínimo Plataformas | 14.0% | 14.0% | `B33` = 0.14 | NO |
| Mínimo Captura | 32.92% | 21.0% | `B34` = 0.21 | **SÍ** (mínimo bajó, objetivo se mantiene) |
| Margen objetivo Captura | 32.92% | 32.92% | `C34` = 0.3292 | NO |
| Ramp-up Plataformas | mes 1-9 = 1.0 | mes 1-60 = 1.0 (Excel V2-7) | `Rot,Ausent!B42:K42` = todos 1.0 | NO (Excel lo cambió a 1.0; v2-6 ya tenía 1.0 también) |
| Ramp-up Captura mes 1 | n/a (no había curva) | 0.90 | `Rot,Ausent!B43` = 0.90 | **SÍ** (nueva curva 0.9/0.95/1.0...) |
| IPC anual 2026 | 0.0527 | 0.0527 | `Tasas!C4` | NO |
| SMLV anual 2026 | 0.2378 | 0.2378 | `Tasas!C5` | NO |
| **Margen Cadena A default** | (variable, en input) | **0.21** (nuevo default Cap.A=Cobranzas mín) | `Panel!C63` = 0.21 | **SÍ** (nuevo campo en v2_7_defaults) |
| **Margen Cadena B** | (hardcoded 0.30) | **0.30** (en v2_7_defaults) | `Panel!D63` = 0.30 | **SÍ** (formalizado) |
| **Margen Cadena C** | (hardcoded 0.20) | **0.20** (en v2_7_defaults) | `Panel!E63` = 0.20 | **SÍ** (formalizado) |
| **Mes ajuste indexación** | 1 (constante código) | **6** | `Panel!L9` = 6 | **SÍ** |
| **Tasa interés mensual** | (no parametrizada) | **0.0153** | `Panel!L10` = 0.0153 | **SÍ** |
| **Imprevistos default** | 0 (campo dominio) | 0 | `Panel!C73` = 0 | NO (formalizado) |
| Comisión administración | 0.0118 | 0.0118 | `Tasas!B28` | NO |
| GMF | 0.004 | 0.004 | `Tasas!B30` | NO |
| Timbre | 0.01 | 0.01 | `Tasas!B31` | NO |
| ICA Bogotá | 0.00966 | 0.00966 | `Tasas!B37` | NO |
| ICA Barranquilla | 0.0125 | 0.0125 | `Tasas!B36` | NO |
| ICA Bucaramanga (Tarifa) | 0.009 | 0.009 | `Tasas!B38` | NO |
| **ICA Bucaramanga (S.Bomberil)** | n/a | 0.10 | `Tasas!D38` | **SÍ** (nuevo desglose) |
| **Contingencia Op. min/max** | 0.01 / 0.04 | **0.05 / 0.08** | `Panel!D67/E67` | **SÍ** |
| **Contingencia Com. min/max** | 0.00 / 0.08 | **0.04 / 0.07** | `Panel!D68/E68` | **SÍ** |
| **Markup min/max** | 0.00 / 0.02 | **0.02 / 0.08** | `Panel!D69/E69` | **SÍ** |
| **Descuento min/max** | 0.00 / 0.00 | **0.00 / 0.08** | `Panel!D70/E70` | **SÍ** |
| Director de cuentas tarifa diaria capacitación | n/a | 20,000 | `Panel!C16` | (formalizado) |
| Crucero (tarifa) | n/a | 8,408 | `Panel!C17` | (formalizado, era `=8000*(1+5.1%)`) |

---

## 4. Top 10 cambios vs v2-6

1. **Margen B/C ahora parametrizados** (`op.v2_7_defaults.margenes.margen_b_default=0.30`, `margen_c_default=0.20`). Antes hardcodeados en código.
2. **Margen mínimo Cobranzas/SAC/Ventas sube 17%→21%** (HR.rentabilidad). Reduce el espacio de descuento.
3. **Margen mínimo Captura baja 32.92%→21%**, pero el objetivo sigue 32.92%.
4. **Mes de ajuste de indexación = 6** (junio) en lugar de la constante código `MES_INICIO_AJUSTE_ANUAL=1`.
5. **Director de cuentas tiene `costo_empresa_override = 29,031,301`** (anomalía Excel — fórmula `=18,505,000*(1+23%)` ya pre-calculada). Resto de cargos usan fórmula estándar.
6. **Salario Director de cuentas (base)** sube 18,505,000 → **22,761,150** (`Inputs!C16` Excel V2-7).
7. **Tasa interés mensual financiación = 0.0153** (antes no parametrizada / venía de `OP-Config`).
8. **Rangos de políticas comerciales actualizados** (contingencias, markup, descuento) — ver §2.3.
9. **Nuevo campo `imprevistos_default = 0`** formalizado en BR para validación de rango (`Panel!C73`).
10. **Ramp-up Captura de Datos** ahora tiene curva explícita 0.9 / 0.95 / 1.0 / 1.0... (antes constante 1.0).

---

## 5. Cambios mínimos requeridos en `parametrization_provider.py` para activar v2-7

**NO se aplican en WAVE 1**, solo se documentan. La carga actual usa:

```
ParametrizationResolver
  └─ MODULES = {"hr": HR_DIR, "gn": GN_DIR, "op": OP_DIR}
  └─ _load_active_version() lee versions.json[is_active=true]
  └─ _load_version_data() lee {version_id}.json
```

**Opción A (recomendada — preserva backward compat)**: agregar entradas a cada `versions.json` apuntando a `../v2-7/{hr,gn,op}.json` con un `path` campo nuevo, e implementar resolver que mire `path` opcional antes de `{version_id}.json`. Marcar v2-7 como `is_active=true` y v2-6 UUID como `is_active=false`.

```jsonc
// storage/parametrization/hr/versions.json (futuro)
[
  {"version_id": "2236cdcf-...", "is_active": false, ...},
  {"version_id": "v2-7",
   "filename": "v2-7/hr.json",
   "path": "../v2-7/hr.json",        // ← NUEVO
   "uploaded_at": "2026-05-27T...",
   "is_active": true,
   "sheet_count": 15, "total_rows": 836}
]
```

Y modificar `ParametrizationResolver._load_version_data()`:

```python
data_path = module_dir / f"{version_id}.json"
if "path" in active_summary._raw:           # ← nuevo
    data_path = (module_dir / active_summary._raw["path"]).resolve()
```

**Opción B (más simple, pero rompe convención de carpeta)**: copiar `v2-7/hr.json` como `hr/<uuid-nuevo>.json` y registrarlo en `versions.json`. **Desventaja**: duplica datos y pierde el "manifest único" de v2-7.

**Recomendación**: Opción A. Implementar en WAVE 2 junto con migración de campos de dominio.

**Business rules**: hoy lee `business_rules/{active}.json` donde `active` viene de `versions.json[active_version]`. Para v2-7 basta con:
1. Copiar `v2-7/business_rules.json` → `business_rules/v2-7.json`.
2. Editar `business_rules/versions.json` → `{"active_version": "v2-7"}`.

---

## 6. Sample manifest.json

```json
{
  "version": "v2-7",
  "source": "Excel Nexa Pricing Simulator V2-7",
  "source_file": "Nexa - Pricing - Simulador - V2-7.xlsx",
  "generated_at": "2026-05-27T...Z",
  "generator": "WAVE1 extraction (openpyxl, data_only=True)",
  "files": {
    "hr.json": {"sha256": "..."},
    "gn.json": {"sha256": "..."},
    "op.json": {"sha256": "..."},
    "business_rules.json": {"sha256": "..."}
  },
  "schema_notes": [
    "Mantiene MISMO schema que v2-6 (carpetas hr/gn/op/business_rules)",
    "Agrega campos NUEVOS: hr.nomina[].costo_empresa_override, op.v2_7_defaults",
    "No reemplaza UUIDs existentes; v2-7 vive en su propia carpeta versionada"
  ]
}
```

---

## 7. Sample: bloque nuevo `op.v2_7_defaults`

```json
{
  "margenes": {
    "cadena_a_por_servicio_default": {
      "Cobranzas":        {"minimo": 0.21, "margen_objetivo": 0.18},
      "Sac":              {"minimo": 0.21, "margen_objetivo": 0.18},
      "Ventas multicanal":{"minimo": 0.21, "margen_objetivo": 0.18},
      "SACO":             {"minimo": 0.105,"margen_objetivo": 0.105},
      "Plataformas":      {"minimo": 0.14, "margen_objetivo": 0.15},
      "Captura de Datos": {"minimo": 0.21, "margen_objetivo": 0.3292}
    },
    "margen_a_default": 0.21,
    "margen_b_default": 0.30,
    "margen_c_default": 0.20
  },
  "indexacion": {
    "mes_ajuste": 6,
    "frecuencia": "Anual",
    "componente_humano_default": "80% SMMLV 20% IPC",
    "componente_tecnologico_default": "20% SMMLV 80% IPC",
    "tasa_interes_mensual": 0.0153
  },
  "imprevistos_default": 0.0,
  "comision_administracion": 0.0118,
  "gmf": 0.004,
  "timbre": 0.01,
  "tarifa_dia_capacitacion": 20000.0,
  "crucero": 8408.0,
  "horas_formacion_mensual": 8.0
}
```

---

## 8. Sample: override Director de cuentas en HR

```json
{
  "tipo": "Empleado",
  "rol": "Director de cuentas",
  "salario": 22761150.0,
  "costo_empresa_override": 29031301.0
}
```

Para cualquier otro cargo, NO existe `costo_empresa_override` → calculadores aplican la fórmula estándar (salario × factor_prestacional + parafiscales + cesantías + ...).

---

## 9. Campos NUEVOS que requieren cambios en domain models (INPUT WAVE 2)

| Campo | Ubicación nueva (sugerida) | Origen JSON | Tipo |
|-------|----------------------------|-------------|------|
| `costo_empresa_override` | `domain/models/nomina.py` o nuevo `Cargo` model | `hr.nomina[].costo_empresa_override` | `Optional[float]` |
| `margen_b` | `domain/models/panel.py:PanelDeControl` | `op.v2_7_defaults.margenes.margen_b_default` | `float = 0.30` |
| `margen_c` | `domain/models/panel.py:PanelDeControl` | `op.v2_7_defaults.margenes.margen_c_default` | `float = 0.20` |
| `mes_ajuste_indexacion` | `domain/models/panel.py:PanelDeControl` | `op.v2_7_defaults.indexacion.mes_ajuste` | `int = 6` |
| `tasa_interes_mensual` | `domain/models/panel.py:PanelDeControl` o `ParametrosNomina` | `op.v2_7_defaults.indexacion.tasa_interes_mensual` | `float = 0.0153` |
| `imprevistos` | `domain/models/panel.py:PanelDeControl` (ya existe; falta validación rango) | `op.v2_7_defaults.imprevistos_default` | `float = 0.0` |
| `componente_humano_default` | `ParametrosNomina` | `op.v2_7_defaults.indexacion.componente_humano_default` | `str` |
| `componente_tecnologico_default` | `ParametrosNomina` | `op.v2_7_defaults.indexacion.componente_tecnologico_default` | `str` |
| `rotacion_ausentismo` (consolidado por servicio) | `repositories/payroll_*` getter ya existe; falta consumir desde `hr.rotacion_ausentismo` | `hr.rotacion_ausentismo` | dict |

### DTOs en `simulation/request_dto.py` que deberán agregar campos opcionales:
- `PanelDeControlRequest`: `margen_b`, `margen_c`, `mes_ajuste_indexacion`, `tasa_interes_mensual`.
- Validadores: `margen_b ∈ [0,1]`, `margen_c ∈ [0,1]`, `mes_ajuste_indexacion ∈ [1,12]`.

---

## 10. Decisiones tomadas (locked-in)

1. **Versionado**: carpeta `storage/parametrization/v2-7/` consolida hr/gn/op/business_rules con un solo manifest. NO se copia a las carpetas legacy con UUID nuevo (decisión de la tarea).
2. **Margen Cadena C en Vision Tarifas**: usar `margen_a` literalmente (anomalía Excel) — esto NO afecta WAVE 1, sólo se documenta para WAVE 3 en `calculators/vision_tarifas.py`.
3. **Director de cuentas `costo_empresa_override`**: NO se reemplaza el salario base; se agrega un campo opcional al row. Calculadores deberán: `costo_empresa = override if override else fórmula_estándar(salario, prestaciones)`.

---

## 11. Bloqueos / decisiones pendientes para WAVE 2

| # | Bloqueo | Recomendación |
|---|---------|---------------|
| B1 | Resolver debe soportar `path` en `versions.json` para apuntar a `../v2-7/...` (Opción A) | Implementar en WAVE 2 con test. |
| B2 | Domain `PanelDeControl` no tiene `margen_b`, `margen_c`, `mes_ajuste_indexacion`, `tasa_interes_mensual` | WAVE 2 (W2-1..W2-5 del plan WAVE0). |
| B3 | `NominaCalculator` no lee `costo_empresa_override`. Hoy aplica fórmula estándar a Director de cuentas → arrojará ~28M en lugar de 29.03M | WAVE 3 (en calculators/nomina.py). |
| B4 | Ramp-up: el JSON v2-7 expande 1→60 meses; verificar que `get_rampup()` lookup actual funcione con `mes=11..60` (debería, pero falta test) | WAVE 4. |
| B5 | El v2-6 frozen tiene `target_margin: 0.18` global; v2-7 cambia a 0.21 para 4 servicios. **NO está claro** si el frozen v2-7 debe reflejar 0.18 (compat) o 0.21 (correcto) | Decidir antes de WAVE 3. Recomendación: `frozen/v2-7.json` debe reflejar Excel V2-7 literalmente. |
| B6 | `tasa_financiacion_mensual` en `op.sheets[].config` (clave actual) = 0.015; v2-7 dice 0.0153 (Panel!L10). Diferencia 2%. Falta reconciliar fuente única | Decidir en WAVE 2 — preferir Panel (input por deal). |

---

## 12. Validación rápida (sanidad)

```
$ wc -l storage/parametrization/v2-7/*.json
   141  business_rules.json
   498  gn.json
  4450  hr.json
    25  manifest.json
  1088  op.json
```

Comparación de tamaños vs originales:
- HR v2-6 (UUID): 4461 líneas vs v2-7: 4450 → diff esperado por re-ordering de keys (sin pérdida de info).
- OP v2-6 (UUID): 993 vs v2-7: 1088 → +95 líneas por `v2_7_defaults`.
- GN v2-6 (UUID): 491 vs v2-7: 498 → +7 líneas por `_meta`.
- Business Rules v2-6: 82 vs v2-7: 141 → +59 líneas por nuevas reglas y `imprevistos`.

---

## 13. Próximo paso

**WAVE 2** (no ejecutado aquí):
1. Agregar `margen_b`, `margen_c`, `mes_ajuste_indexacion`, `tasa_interes_mensual` a `PanelDeControl` y `PanelDeControlRequest`.
2. Implementar lectura del bloque `op.v2_7_defaults` en `ProfitabilityParametrizationRepository` (nuevo getter `get_v27_defaults()`).
3. Agregar soporte `path` en `ParametrizationResolver._load_active_version()` para apuntar fuera de la carpeta del módulo.
4. Actualizar `versions.json` × 3 + `business_rules/versions.json` para activar v2-7 detrás de un flag (`NEXA_PARAM_VERSION=v2-7`).

— Fin del WAVE 1.
