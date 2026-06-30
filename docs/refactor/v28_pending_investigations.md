# V2-8 Pending Investigations — CHECKPOINT A1

**Fecha:** 2026-06-10  
**Objetivo:** Resolver los 3 ítems pendientes antes de Paso B: `crucero`, `cons_costo_de_financiacion`, y completar la decisión de `tasa_ica` (cubierta en `v28_ica_resolution.md`).

---

## Ítem 1 — `crucero` (Panel!C17)

### Pregunta
¿Es Panel!C17 un valor literal o una fórmula derivada (ej. `=ROUNDDOWN(SMMLV, ...)`)?

### Evidencia

| Check | Resultado |
|-------|-----------|
| `data_only=True` → Panel!C17 | **8408** |
| `data_only=False` → Panel!C17 | **8408** |
| Tasas!C5 (SMMLV 2026 ajuste) | 0.2378 (% de incremento, no el valor absoluto) |
| Hoja Maestra E134 | `=+'Panel de Control General'!C17` (referencia directa, no cálculo) |

**Conclusión: `crucero` es un LITERAL INPUT en V2-8 (8408).** No hay fórmula de derivación.

### Contexto adicional

El SMMLV mensual 2026 en Colombia = $1,423,500 COP. El valor 8408 en el motor representa la unidad interna de cálculo del "crucero" (no es el SMMLV en pesos). La diferencia con request.json (8422) refleja simplemente que el deal V2-8 usa una versión actualizada de este parámetro.

Condiciones Cadena A (`E134`) lo lee directamente desde Panel; no hay dependencia de Tasas ni de cálculo externo.

### Veredicto

| Ítem | Resultado |
|------|-----------|
| ¿Es literal o fórmula? | **LITERAL** (8408 hardcoded en Panel!C17) |
| ¿Debemos actualizar? | **SÍ — VALUE_UPDATE aprobado** |
| Cambio en request.json | `datos_operativos.crucero`: 8422 → **8408** |
| Riesgo | Bajo — cambio directo en input, sin impacto estructural |

---

## Ítem 2 — `cons_costo_de_financiacion` (Panel!C21)

### Pregunta
Si `cons_costo_de_financiacion = False`, ¿se deshabilita el módulo completo de financiación o solo cierta parte? Listar funciones afectadas.

### Evidencia — Excel V2-8

| Check | Resultado |
|-------|-----------|
| `data_only=True` → Panel!C21 | **"No"** |
| `data_only=False` → Panel!C21 | **"No"** (literal, sin fórmula) |
| Referencias a Panel!C21 en otras hojas | **Ninguna confirmada** (falsos positivos de `$C$210` en Nomina Loaded) |

**Panel!C21 es un input literal. El Excel V2-8 NO tiene fórmulas que lean este cell en ninguna hoja de cálculo del motor.** La lógica de gating vive exclusivamente en el backend Python.

### Evidencia — Backend Python

**Flujo del flag:**
```
request.json.datos_operativos.cons_costo_de_financiacion = True  (actual)
    ↓
user_input_loader.py:311
    "activa_financiacion": ops.get("cons_costo_de_financiacion", True)
    ↓
PanelDeControl.activa_financiacion = True
    ↓
CostosFinancierosCalculator._calcular_financiacion()
```

**La única función que lee `activa_financiacion`:**

```python
# modules/calculator_motor/formulas/costos_financieros/calculator.py:294-296
def _calcular_financiacion(self, costo_operativo: float, factor_periodo: int) -> float:
    if not self._panel.activa_financiacion:
        return 0.0                          # ← ÚNICO punto de gating
    return factor_periodo * self._panel.tasa_mensual_financ * costo_operativo
```

### Impacto de cambiar False (cascada)

| Componente | Cambio cuando `activa_financiacion = False` |
|------------|---------------------------------------------|
| `_calcular_financiacion()` | Retorna **0.0** para todos los meses (única función gateada) |
| `financiacion` | **0.0** para los 24 meses del contrato |
| `_calcular_polizas()` | Base = `(costo + 0) / fm` → ligeramente menor |
| `_calcular_ica()` | Base = `(costo/fm + polizas + 0)` → ligeramente menor |
| `_calcular_gmf()` | Base = `(costo + polizas + 0)` → ligeramente menor |
| `_calcular_comision_administracion()` | Sin cambio (no depende de financiacion) |
| `CostosFinancierosMes.financiacion` | **0.0** |
| `P&G.costos_financieros` | Reducido exactamente en `financiacion` (otros componentes bajan marginalmente) |

**Lo que NO cambia:**
- ICA, GMF, pólizas, comisión admin **siguen calculando** (no se deshabilitan)
- `CostosFinancierosCalculator` sigue ejecutándose íntegramente
- No hay impacto en `NominaCalculator`, `CadenaCCalculator`, `KPIsCalculator`

### El módulo de financiación NO se deshabilita completamente

`cons_costo_de_financiacion = False` solo pone **`financiacion = 0`** en los 24 meses. Los demás componentes del módulo (ICA, GMF, pólizas) se reducen marginalmente porque la financiación ya no forma parte de sus bases. El total `costos_financieros` baja, pero solo en la parte de `financiacion`.

### Veredicto

| Ítem | Resultado |
|------|-----------|
| ¿Es literal o fórmula en V2-8? | **LITERAL** ("No" hardcoded en Panel!C21) |
| ¿El Excel gatea alguna hoja por este cell? | **No** — ninguna referencia en fórmulas del motor |
| ¿Qué se deshabilita en backend? | Solo `_calcular_financiacion()` → `financiacion = 0` |
| ¿Se deshabilita todo el módulo? | **No** — ICA/GMF/pólizas siguen activos |
| Cambio en request.json | `datos_operativos.cons_costo_de_financiacion`: `true` → **`false`** |
| Riesgo | Medio — afecta totales de P&G pero está bien contenido en `CostosFinancierosCalculator` |

---

## Resumen — Estado Paso B pendiente de aprobación

| Key | Cambio | Clasificación | Decisión |
|-----|--------|---------------|----------|
| `datos_operativos.crucero` | 8422 → 8408 | VALUE_UPDATE | **ESPERANDO APROBACIÓN** |
| `datos_operativos.cons_costo_de_financiacion` | `true` → `false` | VALUE_UPDATE | **ESPERANDO APROBACIÓN** |
| `datos_operativos.tasa_ica` | 0.0097 → 0.01 | VALUE_UPDATE | Ver `v28_ica_resolution.md` → **ESPERANDO APROBACIÓN** |

---

## CHECKPOINT A1 — 3 ítems para aprobación del usuario

Los dos reportes (`v28_ica_resolution.md` + este archivo) completan la investigación solicitada. Los 3 ítems pendientes son:

1. **`tasa_ica`**: 0.0097 → 0.01 (Panel!C34 literal, Tasas no usadas por motor)
2. **`crucero`**: 8422 → 8408 (Panel!C17 literal, no fórmula derivada)
3. **`cons_costo_de_financiacion`**: `true` → `false` (solo zeroes `financiacion`, no deshabilita módulo)

**Si apruebas los 3, procedo a Paso B con el set completo: 9 VALUE_UPDATEs + 4 STRUCTURE_EXTENSIONs + estos 3.**
