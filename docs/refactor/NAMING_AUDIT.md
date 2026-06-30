# NAMING AUDIT — NEXA Backend
**Fecha:** 2026-05-31  
**Versión Excel referencia:** V2-7  
**Autor:** Audit automatizado + revisión manual  

---

## METODOLOGÍA

Antes de renombrar cada variable se verificó:
1. Significado funcional real (código + fórmulas)
2. Origen en Excel (hoja y celda)
3. Impacto en API (pública / interna)
4. Mapeo a visión (CTS / Tarifas / P&G / Imprimible)

Variables no trazables al Excel → NO se renombraron.

---

## VEREDICTO GLOBAL

| Categoría | Estado | Acción |
|---|---|---|
| Nomenclatura de negocio en español | ✅ Bien alineada | Sin cambios |
| Modelos de resultados (`Resultado*`) | ✅ Descriptivos | Sin cambios |
| Campos de visión (`Desglose*`, `Resumen*`) | ✅ Correctos | Sin cambios |
| **Abreviaciones ambiguas** | ❌ 6 casos críticos | **Renombrar** |
| Terminología cadenas (A/B/C) | ✅ Consistente | Sin cambios |
| Sufijos por canal (`_a`, `_b`, `_c`) | ⚠️ Aceptable | Sin cambios (contexto claro) |
| Lenguaje (Español vs Inglés en spec) | ⚠️ Tensión | Ver nota §1 |

---

## NOTA §1 — LENGUAJE: ESPAÑOL SE MANTIENE

La especificación de refactor incluye ejemplos en inglés (`monthly_revenue`, `cost_to_serve`).  
**Decisión: nomenclatura permanece en español** por las siguientes razones trazables:

1. La **fuente de verdad (Excel V2-7)** usa español: `Ingreso Bruto`, `Costo Total`, `Contribución`
2. Las **visiones de negocio** están en español: Vision P&G, Vision CTS, Vision Tarifas
3. Cambiar a inglés **rompería la trazabilidad Excel ↔ Backend** (principio clave del sistema)
4. El API ya expone términos en español; cambiarlos rompe contratos con consumidores existentes

Excepción aceptable: términos de industria sin traducción estándar (`hitl`, `fte`, `opex`, `capex`).

---

## HALLAZGOS POR CATEGORÍA

### CATEGORÍA A — ABREVIACIONES SIN EXPANDIR (CRÍTICO ❌)

Estas generan ambigüedad real: un desarrollador nuevo no puede inferir el significado.

| # | Nombre actual | Propuesto | Módulo | Línea | Significado funcional | Excel | Impacto API |
|---|---|---|---|---|---|---|---|
| A-1 | `cap_inicial` | `capacitacion_inicial` | `results.py:26`, `visions.py` | ~48 ocurrencias | Costo de capacitación inicial amortizado en mes 1 | Nomina Loaded → col Capacitación Inicial | ⚠️ Interno |
| A-2 | `cap_rotacion` | `capacitacion_rotacion` | `results.py:27`, `visions.py` | ~48 ocurrencias | Costo mensual de capacitación por rotación continua | Nomina Loaded → col Capacitación Rotación | ⚠️ Interno |
| A-3 | `sm` (campo en `ResultadoCadenaB`) | `soporte_mantenimiento` | `results.py:55` | ~15 ocurrencias | Costo mensual de equipo de Soporte & Mantenimiento | Cadena B → S&M Staff | ⚠️ Interno |
| A-4 | `comadm_a` | `comision_admin_cadena_a` | `results.py:130,173` | ~12 ocurrencias | Comisión de administración atribuible a Cadena A | Vision Tarifas → Comisión Adm. | ⚠️ Interno |
| A-5 | `costo_fin_a_vt` | `costo_financiero_vt_cadena_a` | `results.py:134,175` | ~10 ocurrencias | Costo financiero de Cadena A para base de Vision Tarifas | Vision Tarifas → Financiero A | ⚠️ Interno |
| A-6 | `s_m` (campo en `DesgloseCTSCadenaB`) | `soporte_mantenimiento` | `visions.py:64` | ~8 ocurrencias | Igual que A-3 — inconsistencia de nombre entre modelos | CTS → S&M | ⚠️ Interno |

**Todos son campos internos (no expuestos en API pública).** Riesgo bajo.

---

### CATEGORÍA B — ACEPTABLES SIN CAMBIO (✅)

Estos nombres son correctos; renombrarlos reduciría, no mejoraría, la claridad.

| Nombre | Razón de no cambio |
|---|---|
| `hitl` | Término de industria (Human-in-the-Loop). Renombrar a `humano_en_el_loop` sería peor. |
| `fte` | Full-Time Equivalent — universal en RRHH/BPO. Excel usa FTE. |
| `opex`, `capex` | Estándar financiero internacional, reconocido en contexto. |
| `ica`, `gmf` | Siglas de impuestos colombianos (ICA = Impuesto de Industria y Comercio, GMF = Gravamen). |
| `pyg` en clases | `VisionPyG`, `PyGMensual` — P&G es abreviación de dominio usada en Excel. |
| `cts_*` | Abreviación de Cost-to-Serve establecida en el dominio. |
| `_ch` sufijo | Sufijo de canal en `TarifaCanal` — contexto de clase lo hace claro. |
| `pct_*` prefijo | Convención uniforme para porcentajes (consistent en todo el sistema). |
| `acum_*` prefijo | Prefijo de acumulado — uniforme en todo `PyGMensual`. |

---

### CATEGORÍA C — INCONSISTENCIAS MENORES (⚠️ DOCUMENTAR, no cambiar)

| Inconsistencia | Ubicación | Nota |
|---|---|---|
| `sm` vs `s_m` | `ResultadoCadenaB.sm` vs `DesgloseCTSCadenaB.s_m` | Unificar a `soporte_mantenimiento` (cubre A-3 y A-6) |
| `desglose_a` (CTS) vs `ResultadoCadenaB` | Distinción conceptual correcta: desglose = presentación, resultado = cálculo | Mantener distinción |
| `costos_fijos` vs `costos_fijos_estacion` | Uno es total, otro es por estación — nombres correctos | Sin cambio |

---

### CATEGORÍA D — FUERA DE SCOPE (🚫 NO TOCAR)

| Nombre | Razón |
|---|---|
| `ingreso_bruto`, `ingreso_neto` | Alineados exactamente con Excel P&G. Renombrar a `gross_revenue` rompe trazabilidad. |
| `contribucion` | Término de contabilidad de gestión español — preciso. |
| `utilidad_neta` | Preciso. `net_profit` sería confuso en contexto colombiano. |
| `salario_base`, `salario_cargado` | Terminología de nómina colombiana estándar. |
| `meses_contrato` | Claro y alineado con Excel Panel de Control. |
| `tmo_segundos` | TMO = Average Handle Time. Sufijo `_segundos` indica unidad — correcto. |
| `pct_presencia` | Porcentaje de presencia operativa — preciso. |
| `escalamiento` | Costo de escalamiento de capacidad — término del dominio. |

---

## IMPACTO ESTIMADO CHANGES A-1 a A-6

| Change | Archivos afectados (estimado) | Tests a actualizar | Riesgo |
|---|---|---|---|
| A-1 `cap_inicial` → `capacitacion_inicial` | ~8 archivos | ~15 tests | Bajo |
| A-2 `cap_rotacion` → `capacitacion_rotacion` | ~8 archivos | ~15 tests | Bajo |
| A-3 + A-6 `sm`/`s_m` → `soporte_mantenimiento` | ~6 archivos | ~8 tests | Bajo |
| A-4 `comadm_a` → `comision_admin_cadena_a` | ~5 archivos | ~5 tests | Bajo |
| A-5 `costo_fin_a_vt` → `costo_financiero_vt_cadena_a` | ~4 archivos | ~4 tests | Bajo |

**Total estimado:** ~15 archivos modificados, ~47 tests actualizados, 0 cambios de lógica.

---

## MAPA Excel ↔ Backend ↔ API ↔ Visión

### Costos de Nómina (Cadena A)

| Excel (Nomina Loaded) | Backend (ResultadoNomina) | API Key | Visión |
|---|---|---|---|
| Salario Fijo | `salario_fijo` | `salario_fijo` | CTS → Nomina |
| Comisiones | `comisiones` | `comisiones` | CTS → Nomina |
| **Capacitación Inicial** | `cap_inicial` ← ❌ | `cap_inicial` | CTS → Nomina |
| **Capacitación Rotación** | `cap_rotacion` ← ❌ | `cap_rotacion` | CTS → Nomina |
| Exámenes Médicos | `examenes` | `examenes` | CTS → Nomina |
| Estudios Seguridad | `seguridad` | `seguridad` | CTS → Nomina |
| Crucero | `crucero` | `crucero` | CTS → Nomina |

### Costos Cadena B

| Excel (Cadena B) | Backend (ResultadoCadenaB) | API Key | Visión |
|---|---|---|---|
| OPEX Fijo | `opex_fijo` | `opex_fijo` | CTS → B |
| Inversiones | `inversiones` | `inversiones` | CTS → B |
| **S&M Staff** | `sm` ← ❌ | `sm` | CTS → B |
| Costo Variable | `costo_variable` | `costo_variable` | CTS → B |
| Escalamiento | `escalamiento` | `escalamiento` | CTS → B |
| HITL | `hitl` | `hitl` | CTS → B |

### Financieros (CostosFinancierosMes)

| Excel | Backend | API Key | Visión |
|---|---|---|---|
| Financiación | `financiacion` | `financiacion` | P&G → Costos Fin. |
| Pólizas | `polizas` | `polizas` | P&G → Costos Fin. |
| ICA | `ica` | `ica` | P&G → Costos Fin. |
| GMF | `gmf` | `gmf` | P&G → Costos Fin. |
| Comisión Adm. Cadena A | `comadm_a` ← ❌ | `comadm_a` | Vision Tarifas |
| Costo Fin. VT Cadena A | `costo_fin_a_vt` ← ❌ | `costo_fin_a_vt` | Vision Tarifas |

---

## CRITERIO DE ÉXITO PARA ESTA REFACTOR

- [ ] Los 6 campos abreviados renombrados
- [ ] 0 cambios de lógica / fórmulas
- [ ] Tests pasan al 100% (mismas cantidades de pass/fail que pre-refactor)
- [ ] `BUSINESS_GLOSSARY.md` creado
- [ ] Ningún campo de API pública renombrado sin alias de retrocompatibilidad
