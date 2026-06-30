# Gap Registry — V2-7

## Estado: VACÍO

No quedan gaps económicos sin resolver.

---

## Historial de gaps cerrados

| Gap ID | Descripción | Onda | Resolución |
|--------|-------------|------|-----------|
| GAP-PYG-HIER-1 | Sub-componentes payroll Cadena A no expuestos | W18.F5 Phase 2 | VisionPyGBuilder.filas_detalle con 7 sub-componentes ✓ |
| GAP-PYG-HIER-2 | Sub-componentes Cadena B (parcial) | W18.F5 Phase 2 | 6/7 campos; OPEX Variable = no existe en ResultadoCadenaB |
| GAP-PYG-HIER-3 | Sub-componentes Cadena C | W18.F5 Phase 2 | 7 campos desde ResultadoCadenaC ✓ |
| GAP-PYG-HIER-4 | Contribución por Puesto | W18.F5 Phase 2 | estaciones=24 == workbook C14 ✓ |
| GAP-CTS-HIER-1 | Campo crucero no en DesgloseCTSCadenaA | W18.F5 Phase 2 | crucero=11.17 == workbook fila 43 ✓ |
| GAP-CTS-ACT-1 | IF(C27="SAC") tratado como cosmético | W18.F5.D/E | Modelo servicio-driven completo; catálogo Listas Desplegables!A4:A9 ✓ |
| GAP-CTS-CHAN-1 | CTS por canal no implementado | W18.F5 Phase 2 | CanalCTSDetalle implementado; payroll exact match workbook ✓ |
| VT!C50 | oracle_mapping usaba total B en vez de por-escenario | W18.F5.C | Extractor corregido: canales[0].cadena_b_atribuible ✓ |
| VT!C65 | oracle_mesh_mapping apuntaba a celda equivocada | W18.F5.C | Checkpoint eliminado (C65=Pólizas C, no total) |
| Labels PyG | Labels no coincidían con Excel exacto | W18.F5.C | Renombrados: "Ingreso Bruto", "Costo Total", "Costos Financieros", etc. |
| polizas_a/b/c | Filas sin equivalente en Excel "Visión P&G" | W18.F5.C | Eliminadas de _ROW_DEFINITIONS |
| Tmp debug tests | 4 archivos _tmp.py dejados de debugging | W18.F5.C | Eliminados |
| Contract validator | cadenas is required para pólizas | Early | Eliminada validación obsoleta |
| VT voz_frac=0 | WhatsApp sin fallback cuando no hay canal Voz | Early | Fallback a todos los canales implementado |

## Elementos DISPLAY_ONLY (formalmente excluidos, no son gaps)

Ver CERTIFICATION_DISPLAY_ONLY_REGISTRY.md
