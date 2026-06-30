# Reglas de Negocio — Cadena A (Excel V2-7) — F6

## Alcance y limitaciones
- **Cubre:** reglas de negocio implícitas y explícitas de Cadena A identificadas en auditorías Fases 2-4 (activación, ventana temporal, derivación, agregación, constantes mágicas, supresión de error), con implementación backend y estado.
- **NO cubre:** paridad de valor (bloqueado); cadenas B/C; reglas no observadas en la evidencia capturada.
- **Cómo usar:** referencia de "qué regla aplica y dónde". **No es certificación de paridad.**

Estado: `Equivalente` · `Divergencia` · `No encontrado` · `Pendiente`.

## 1. Activación (gates de cadena/canal)
| Regla | Implementación Excel | Backend | Estado | GAP |
|-------|----------------------|---------|--------|-----|
| Canal "Activado" si tiene FTE y la cadena está activa | `IF(AND(FILTER(Panel!M19:M25,K=canal)>0, Panel!M17=TRUE),"Activado",0)` (Nomina/No payroll/Pólizas col A/B) | flags estructurados `CadenasActivas` + `perfil.activo`/FTE>0 | Divergencia mecanismo (valor coincide) | — |
| Cadena A activa (inbound/outbound) | `Panel!M17` / `M30` (True/False) | `CadenasActivas.cadena_a` | Equivalente | — |
| Gate de relevancia de vista por canal | CTS `IF(servicio="SAC","✓ Habilitado","—")` | `cost_to_serve.canal_view_habilitado` | Equivalente (intencional) | GAP-CTS-05 |

## 2. Ventana temporal
| Regla | Implementación Excel | Backend | Estado | GAP |
|-------|----------------------|---------|--------|-----|
| Mes activo solo dentro de [inicio, fin] del contrato | `IF(AND(mes>=$C$4, $C$5>=mes), valor, 0)` (Nomina D93, No payroll D107, todas las celdas mensuales D:BK) | iteración `pyg.py range(1, meses_contrato+1)` | Equivalente | — |
| Indexación salarial desde mes C7 | `IF(MONTH(D92)>=$C$7, INDEX('Ta…tabla), …)` | `nomina.py:140 factor_indexacion_base × calcular_factor_aumento(mes, pct, mes_aplicacion)` (utils.py:47) | Equivalente | — |
| Ventana de costo en Pólizas | `IF('Costos Totales'!E8 <= (Panel!C11 + Nomina Loaded!C3 - 1), …, 0)` | gating por mes | Equivalente | — |

## 3. Derivación
| Regla | Implementación Excel | Backend | Estado | GAP |
|-------|----------------------|---------|--------|-----|
| Margen por servicio | `Panel!C63 = FILTER(Rot!B29:B34, A29:A34=C5)` → Captura de Datos = 0.21 | `get_margen_minimo(servicio)` = 0.21 (storage) **pero ingreso usa `panel.margen` input** | Divergencia (uso) | GAP-CADENA-A-FASE4 |
| Ramp-up operacional por servicio×mes | `Rot!B38:BI43` (Captura: 0.9,0.95,1,1…) → P&G C15 = INDEX | `utils.py:64 calcular_rampup` → `get_rampup` (storage) — **bit-a-bit verificado F4** | Equivalente | — |
| Crucero | `Panel!C17 = 8000*(1+5.1%)` = 8408 | `panel.tarifa_crucero` (input, ej. 8422) | Divergencia (const vs input; ~0.17%) | — |
| Estaciones de trabajo | `Condiciones A!E19 = E17(FTE) × E18(presencia 0.6)` | `no_payroll.py:152 sum(fte × pct_presencia)` | Equivalente | — |
| Ingreso desde costo | `C47 = C40 / factor_margenes × [ramp-up en P&G]` | `ProfitabilityCalculator.calcular_ingreso_desde_costo(costo, factor, rampup)` | Equivalente | — |

## 4. Agregación
| Regla | Implementación Excel | Backend | Estado | GAP |
|-------|----------------------|---------|--------|-----|
| Payroll consolidado/canal = Σ 7 componentes | `Nomina Loaded!D15 = D93+D238+D287+D349+D407+D182+D455` | `ResultadoNomina` acumulado (suma componentes) | Equivalente | — |
| No-payroll consolidado = Σ 3 componentes | `No payroll!D14 = D107+D186+D248` | `ResultadoNoPayroll` acumulado | Equivalente | — |
| Costo Cadena A = Payroll + No payroll + financiero | `Tarifas!C40 = SUM(C41:C46)` | `pyg costo_a = payroll_a + no_payroll_a` (+ ica/gmf/pólizas en financiero) | Equivalente | — |
| factor_margenes | `(1-C63)(1-C67)(1-C68)(1-C69)(1+C70)` | `utils.py:31 calcular_factor_margenes(panel)` | Equivalente | — |
| Anualización / total contrato | `× n meses` (P&G suma meses; Tarifas C40/C50/C60 sobre n) | `vision_tarifas × n` (corregido P1, antes ×12) | Equivalente (post-fix) | GAP-A-02 (resuelto) |
| Costo total acumulado (financiero) | `P&G!BK30 = BK31+BK45+BK55+BK65` (incluye financiero) | `sum(m.costo_total)` excluye financiero | **Divergencia cálculo** | GAP-PYG-01 |

## 5. Constantes mágicas
| Constante | Implementación Excel | Backend | Estado | GAP |
|-----------|----------------------|---------|--------|-----|
| Volumetría 1 FTE | `HME!G35 = 752.815013404826` | `grep 752.81` = 0 coincidencias | **No encontrado** | — |
| Crucero base | `Panel!C17 = 8000*(1+5.1%)` | `tarifa_crucero` input (sin constante) | Divergencia (const vs input) | — |
| Tasa comisión adm | Pólizas D188 = `pct_poliza × 1.42` | `costos_financieros.py tasa_comadm` | Pendiente verificación | GAP-PYG-04 |

## 6. IFERROR / supresión de error
| Ubicación | Fórmula | Riesgo | Backend |
|-----------|---------|--------|---------|
| Tarifas G21, G55, C41-C46 | `IFERROR(…, 0/"-")` | Oculta `#N/A` de FILTER si canal/servicio no existe en catálogo → default silencioso | backend no replica supresión (lanza/loguea según caso) |
| Visión Imprimible B19, B36, I36 | `IFERROR(…, 0/"-")` | idem (presentación) | n/a |
| Panel C63 (vía FILTER) | si servicio C5 ∉ Rot!A29:A34 → error suprimido aguas abajo | Riesgo: C5 es texto libre (sin validación de lista) | `get_margen_minimo` lanza si servicio ausente |

## Reglas críticas que divergen (resumen para decisión)
1. **Margen: fuente** — Excel deriva de tabla servicio (Rot, 0.21); backend usa input (`panel.margen`). Storage tiene el valor correcto pero no se cablea al ingreso. Impacto +9.63%. (GAP-CADENA-A-FASE4; warning instrumentado).
2. **Costo acumulado: financiero** — Excel BK30 incluye Componente Financiero; backend lo excluye del acumulado. Impacto +97.5% en contribución acumulada. (GAP-PYG-01).
3. **Activación: mecanismo** — Excel usa string "Activado" derivado de FILTER; backend usa flags estructurados. Valor coincide (no-gap funcional), pero mecanismo distinto.
