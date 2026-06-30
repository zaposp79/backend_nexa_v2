# V2-8 ICA Resolution — CHECKPOINT A1

**Fecha:** 2026-06-10  
**Objetivo:** Determinar qué valor usa el motor V2-8 para `tasa_ica` y cuál debe quedar en `request.json`.

---

## Las 4 fuentes en juego

| Fuente | Celda | Valor | Tipo |
|--------|-------|-------|------|
| Panel de Control General | C34 | **0.01** | Literal input (no fórmula) |
| Tasas, TRM, Polizas — Bogotá base | B37 | 0.00966 | Tabla de referencia |
| Tasas, TRM, Polizas — Bogotá total | F37 | 0.01966 | `=SUM(B37:E37)` (suma base + recargos) |
| request.json actual | `datos_operativos.tasa_ica` | 0.0097 | Input backend actual |

---

## Qué fórmulas del motor V2-8 usan ICA

### Pólizas - Costo Financiacion (confirmado)

`AB12` (ICA Cadena A, Escenario 1, mes inicial):
```
=IF(AB$10<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),
  (
    ('Costos Totales'!AB37+AB198+AB378+AB223) /
    ((1-'Panel de Control General'!$C$63) *
     (1-'Panel de Control General'!$C$67) *
     (1-'Panel de Control General'!$C$68) *
     (1-'Panel de Control General'!$C$69) *
     (1+'Panel de Control General'!$C$70))
  ) * 'Panel de Control General'!$C$34,
0)
```

**El multiplicador final es `Panel!$C$34` = 0.01.** No hay referencia a `Tasas!B37` ni `Tasas!F37`.

El mismo patrón se repite en todas las filas ICA del sheet (`AB13, AB14, ..., AB49-56, AC76-81, ...`).

### Nomina Loaded (falsos positivos descartados)

Las coincidencias en `Nomina Loaded AC345, BC345, ...` son índices de tasa salarial:
```
=...*(IF(MONTH(AC$344)>=$C$7, INDEX('Tasas, TRM, Polizas'!$B$8:$G$17, MATCH($C$6,...), ...), ...))
```
Esto es indexación de nómina (tabla `B8:G17` = tasas salariales anuales por ciudad), no la tasa ICA del negocio.

### Búsqueda de `Panel!C34` en toda la hoja

La búsqueda con patrón `$C$34` en todas las hojas del workbook confirmó que la única referencia directa al cell Panel!C34 en fórmulas de cálculo es en `Pólizas - Costo Financiacion`. Las demás coincidencias son referencias internas de otras hojas a sus propias celdas C34.

---

## Rol de Tasas!B37 y Tasas!F37

| Celda | Valor | Descripción | Usada en motor V2-8 |
|-------|-------|-------------|---------------------|
| Tasas!B37 | 0.00966 | Tarifa base ICA Bogotá | **NO** |
| Tasas!C37 | 0.01 | Recargo bomberos Bogotá | NO |
| Tasas!D37 | 0 | Recargo estampilla Bogotá | NO |
| Tasas!E37 | 0 | Otro recargo | NO |
| Tasas!F37 | 0.01966 | Total Bogotá (`=SUM(B37:E37)`) | **NO** |

Las celdas `Tasas!B37:F37` son **tabla de referencia visual**, no leídas por ninguna fórmula de cálculo del motor. El deal V2-8 usa `Panel!C34 = 0.01` como override explícito.

---

## Backend — cómo fluye tasa_ica

```
request.json
  datos_operativos.tasa_ica = 0.0097
      ↓
UserInputLoader.cargar_desde_dict()      # user_input_loader.py:39
      ↓
PanelDeControl.tasa_ica = 0.0097
      ↓
CostosFinancierosCalculator._calcular_ica()
  base_ingreso_neto = (costo / factor_margenes) + polizas + financiacion
  return base_ingreso_neto * self._panel.tasa_ica   # ← 0.0097 hoy
```

El Excel V2-8 usa 0.01. El backend usa 0.0097. Delta = +0.0003 (≈ 3%).

---

## Veredicto

| Ítem | Resultado |
|------|-----------|
| ¿Panel!C34 es literal o fórmula? | **LITERAL** (0.01, verificado `data_only=True` y `data_only=False`) |
| ¿Tasas!B37 es usada en motor? | **NO** — solo tabla de referencia |
| ¿Tasas!F37 (0.01966) es usada en motor? | **NO** — solo suma visual |
| ¿Qué valor usa el motor V2-8? | **0.01 (Panel!C34)** |
| ¿Hay conflicto Panel vs Tasas? | No hay conflicto; Panel sobreescribe con valor del deal |
| Acción para request.json | **VALUE_UPDATE**: `datos_operativos.tasa_ica` 0.0097 → **0.01** |

---

## Nota sobre Tasas!F37 = 0.01966

Este valor (base 0.00966 + bomberos 0.01 + otros 0) representa la tarifa oficial ICA Bogotá con **todos los recargos**. El deal V2-8 usa 0.01 — que coincide exactamente con el recargo de bomberos — posiblemente porque este deal específico aplica solo la tarifa de bomberos sin la base. Sin embargo, el motor V2-8 lee `Panel!C34` directamente, y Panel!C34=0.01 es un input del deal. **No es responsabilidad de este análisis interpretar el origen del 0.01**; el motor lo consume como dato.

---

## Pendiente post-CHECKPOINT A1

| Ítem pendiente | Descripción |
|----------------|-------------|
| `tasa_ica`: 0.0097 → 0.01 | Aprobado en **Paso B** (junto a los otros VALUE_UPDATEs) |
| Nota en parity report | "Panel!C34=0.01 sobreescribe Tasas para este deal. Tasas!B37=0.00966 y F37=0.01966 son referencia, no leídas por motor." |
