# Excel Definitivos — Snapshot Literal (2026-06-10)

## Archivos procesados

- `OP_productiva_2026-05-11-10-35-25.xlsx` (OP, 29 KB)
- `HR_productiva_2026-05-11-09-52-29.xlsx` (HR, 51 KB)
- `GN_productiva_2026-05-11-10-25-28.xlsx` (GN, 20 KB)

---

## OP — Sheets modificados

### OP-Poliza
**Headers (3 columnas):** `['Poliza', 'Porcentaje', 'PorcentajeExigido']`
- Data rows: 9
- **Contrato anterior:** `[Poliza, Valor]` (2 columnas)
- **Contrato nuevo:** `[Poliza, Porcentaje, PorcentajeExigido]` ✅

### OP-PolizaFija (NUEVO)
**Headers (2 columnas):** `['Poliza', 'Porcentaje']`
- Data rows: 2
- **Contrato anterior:** NO EXISTÍA
- **Contrato nuevo:** OP_POLIZA_FIJA ✅

### OP-Costo (NUEVO)
**Headers (2 columnas):** `['CostoOperativo', 'Valor']`
- Data rows: 5
- **Contrato anterior:** NO EXISTÍA
- **Contrato nuevo:** OP_COSTO ✅

### OP-MargenObjetivo (NUEVO)
**Headers (2 columnas):** `['Cadena', 'Porcentaje']`
- Data rows: 3
- **Contrato anterior:** NO EXISTÍA
- **Contrato nuevo:** OP_MARGEN_OBJETIVO ✅

### Sheets eliminados del contrato
- OP-HITLCadenaB (no existe en Excel)
- OP-Tasa (no existe en Excel)
- OP-DatosOperativos (no existe en Excel)

---

## HR — Sheets modificados

### HR-EquipoHITL
**Headers (1 columna):** `['EquipoHITL']`
- Data rows: 6
- **Contrato anterior:** `[EquipoHITL, ratio]` (2 columnas)
- **Contrato nuevo:** `[EquipoHITL]` (1 columna, type = CATALOG_BY_COLUMN) ✅
- **Cambio de tipo:** SheetType.TABLE_ROWS → SheetType.CATALOG_BY_COLUMN

**Consumer impact:** ✅ Cero referencias a `ratio` encontradas en código

---

## GN — Sheets modificados

### GN-LV
**Headers (23 columnas):**
```
['Ciudad', 'Localidad', 'Servicio', 'CategoriaServicio', 'CentroCosto', 
 'Componente', 'Poliza', 'ComponenteFijo', 'HardwareSoftware', 'PeriodoPago', 
 'Cadena', 'ComponenteVariable', 'ModeloCombro', 'Modalidad', 'ReglaNegocio', 
 'Canal', 'Metrica', 'Cliente', 'TipoCobro', 'TipoCliente', 'Rubro', 
 'UnidadMedida', 'Divisa']
```
- Data rows: 26
- **Contrato anterior:** 22 columnas (SIN Divisa)
- **Contrato nuevo:** 23 columnas (CON Divisa al final) ✅

---

## Resumen de cambios

| Módulo | Cambios | Status |
|--------|---------|--------|
| **OP** | Actualizar OP-Poliza (3 cols), agregar OP-PolizaFija, OP-Costo, OP-MargenObjetivo | ✅ Completado |
| **HR** | Eliminar columna `ratio` de HR-EquipoHITL, cambiar a CATALOG_BY_COLUMN | ✅ Completado |
| **GN** | Agregar columna `Divisa` al final de GN-LV | ✅ Completado |

---

## Validaciones ejecutadas

- ✅ Contratos actualizados
- ✅ Cero referencias a `ratio` en código
- ✅ OP-BillingComponente eliminado de uso (no existía en código)
- ⏳ Tests en progreso
