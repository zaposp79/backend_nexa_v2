# Registro de Fórmulas — Cadena A (Excel V2-7) — F5

## Alcance y limitaciones
- **Cubre:** catálogo de fórmulas literales de Cadena A extraídas en las auditorías Fases 1-3 (Panel, Condiciones A, Rot/Ausent, Nomina Loaded, No payroll, Pólizas subset A, Hoja Maestra Escenarios), con equivalente backend cuando fue identificado.
- **NO cubre:** paridad de valor (bloqueado); cadenas B/C; fórmulas no extraídas (marcadas "no documentado").
- **Cómo usar:** referencia de "qué fórmula calcula este campo" + dónde vive en backend. **No es certificación.**

Estado backend: `Equivalente` · `Divergencia` · `No encontrado` · `Pendiente verificación`.

## Capa 1 — Panel de Control General
| Celda | Fórmula literal | Inputs | Output | Backend (archivo:fn) | Estado |
|-------|-----------------|--------|--------|----------------------|--------|
| C7 | `=IF(C6="CLIENTE NUEVO","Cliente Nuevo","Cliente Antiguo")` | C6 | tipo cliente | `panel.antiguedad_cliente` (input) | Divergencia |
| C17 | `=8000*(1+5.1%)` = 8408 | const | tarifa crucero | `panel.tarifa_crucero` (input) | Divergencia (const vs input) |
| C63 | `=FILTER(Rot!$B$29:$B$34,(Rot!$A$29:$A$34=C5))` | Rot!B29:B34, C5 | margen A | `panel.margen` (input) / `get_margen_minimo` | Divergencia (uso) — GAP-CADENA-A-FASE4 |
| C67/C68/C69/C70/C73 | `0` (input literal) | — | reglas | `panel.op_cont/com_cont/markup/descuento/imprevistos` | Equivalente |
| M17/M30 | `True`/`False` | — | activación A | `CadenasActivas.cadena_a` | Equivalente |
| M18 | `FTE` (lista FTE/Volumen) | — | unidad cobro | `perfil.modelo_cobro` | Equivalente |

## Capa 2 — Condiciones Cadena A
| Celda | Fórmula literal | Inputs | Output | Backend | Estado |
|-------|-----------------|--------|--------|---------|--------|
| E14:S14 / E15:S15 / E16:S16 | modalidad / canal / nombre (input) | — | metadata perfil | `PerfilCadenaA.modalidad/canal/nombre` | Equivalente |
| E17:S17 | FTE (input, ej. 25/15) | — | FTE | `PerfilCadenaA.fte` | Equivalente |
| E18:S18 | `0.6` (input presencia) | — | pct presencia | `PerfilCadenaA.pct_presencia` | Equivalente |
| E19:S19 | `=E17*E18` | E17, E18 | estaciones | `no_payroll.py:152 sum(p.fte*p.pct_presencia)` | Equivalente |

## Capa 3 — Rot, Ausent y Rentabilidad
| Celda | Fórmula/valor | Inputs | Output | Backend | Estado |
|-------|---------------|--------|--------|---------|--------|
| B29:B34 | margen por servicio (input: 0.21/0.105/0.14) | — | margen servicio | `get_margen_minimo(servicio)` (storage) | Equivalente (existe; no usado en ingreso) |
| B38:BI43 | ramp-up por servicio×mes (input: Captura 0.9,0.95,1,1…) | — | factor ramp-up | `utils.py:64 calcular_rampup` → `get_rampup` (storage) | Equivalente (bit-a-bit verificado F4) |
| B37:BI37 | índice mes (1,2,3…) | — | columna mes | iteración `range(1,meses+1)` | Equivalente |

## Capa 4 — Nomina Loaded
| Celda | Fórmula literal | Inputs | Output | Backend | Estado |
|-------|-----------------|--------|--------|---------|--------|
| Región 1 D15 | `=D93+D238+D287+D349+D407+D182+D455` | 7 regiones componente | payroll consolidado/canal | `ResultadoNomina` acumulado (Σ componentes) | Equivalente |
| Región 2 C93 | `=SUMIFS($E$72:$E$88,$B$72:$B$88,$B$92,$C$72:$C$88,$B93)` | base salario | salario base/canal | `nomina.py::_salario_fijo` | Equivalente |
| Región 2 D93 | `=IF(AND(D$91>=$C$4,$C$5>=D$91),$C93,0)*(IF(MONTH(D$92)>=$C$7,INDEX('Ta…)…))` | C4/C5 ventana, C7 indexación | salario mensual | `nomina.py:140 factor_indexacion × calcular_factor_aumento` | Equivalente (INDEX → factor_aumento) |
| A15 (activación) | `=IF(AND(FILTER(Panel!M19:M25,K=canal)>0,M17),"Activado",…)` | Panel M17/M19:M25 | flag "Activado" | flags estructurados (`perfil.activo`/FTE) | Divergencia mecanismo |

## Capa 5 — No Payroll
| Celda | Fórmula literal | Inputs | Output | Backend | Estado |
|-------|-----------------|--------|--------|---------|--------|
| Región 1 D14 | `=D107+D186+D248` | 3 componentes | no-payroll consolidado | `ResultadoNoPayroll` acumulado | Equivalente |
| Región 2 C107 | `=SUMIFS($E$87:$E$102,$B$87:$B$102,$B$106,$C$87:$C$102,$B107)` | base OPEX | OPEX fijo base/canal | `no_payroll.py` | Equivalente |
| Región 2 D107 | `=IF(AND(D$105>=$C$4,$C$5>=D$105),$C107,0)*(IF(MONTH(D$106)>=$C$7,INDEX…))` | C4/C5/C7 | OPEX mensual | `no_payroll.py` (ventana+indexación) | Equivalente |

## Capa 6 — Pólizas - Costo Financiación (subset A)
| Celda | Fórmula literal | Inputs | Output | Backend | Estado |
|-------|-----------------|--------|--------|---------|--------|
| B12 (activación) | `=IF(AND(FILTER(Panel!M19:M25,K=$D12)>0,Panel!M17=TRUE),"Activado",0)` | Panel M | flag | flags estructurados | Divergencia mecanismo |
| ICA E12 | `=IF(CostosTotales!E8<=…, ((CostosTotales!E37/((1-C63)(1-C67)(1-C68)(1-C69)(1+C70)))+E198+E378)*Panel!C34, 0)` | costo/fm, E198, E378, tasa_ica C34 | ICA A | `costos_financieros.py:181 _calcular_ica` | Equivalente |
| GMF E93 | `=IF(CostosTotales!E8<=…, (CostosTotales!E37+E198+E378)*Panel!C35, 0)` | costo, pól, fin, tasa_gmf C35 | GMF A | `costos_financieros.py:187 _calcular_gmf` | Equivalente |
| Pólizas E198 | `=LET(umbral,C11+NominaLoaded!C3, margenes,(1-C63)(1-C67)(1-C68)(1-C69)(1+C70), base_costo, IF(E196<umbral, CostosTotales!E37+E378, FILTER(…)), SUMPRODUCT($D$173:$D$185*$E$173:$E$185*($G$173:$G$185>=E196))*base_costo/margenes)` | config filas 173-185, vigencia | Pólizas A | `costos_financieros.py _calcular_polizas` / `polizas_usuario[]` | Divergencia mecanismo |
| Fin E378 | `0` | — | financiación A | `financiacion` (=0) | Equivalente |
| Comisión Adm (D188 tasa=pct×1.42) | SUMPRODUCT bloques 223-351 | base, fin | comisión adm | `costos_financieros.py:176 (base+fin)/fm×tasa_comadm` | Divergencia mecanismo — GAP-PYG-04 |

## Capa 7 — Hoja Maestra Escenarios
| Celda | Fórmula literal | Inputs | Output | Backend | Estado |
|-------|-----------------|--------|--------|---------|--------|
| C13 | `=IF(C5="Total",SUM(Cond.A!E17:S17),SUMIFS(Cond.A!E17:S17,canal=C8,modalidad=C7))` | Condiciones A FTE | FTE escenario | `vision_tarifas` SUMIFS por canal/modalidad | Equivalente |
| C16 | `=SUM(C17:C22)` | 6 componentes | costo comp. fijo | — | Pendiente verificación |
| C23 | `=C16/((1-$G$11)(1-$G$6)(1-$G$7)(1-$G$8)(1+$G$9))` | C16, factor G6:G13 | ingreso comp. fijo | `ProfitabilityCalculator.calcular_ingreso_desde_costo` | Equivalente (verificar G6:G13==Panel) |
| C47 | `=C23+C33+C43` | C23/C33/C43 | facturación A | `vision_tarifas.ingreso_cadena_a` | Pendiente verificación |
| G19 | `=(C47*D10)` | C47, D10 | ingreso comp fijo | — | Pendiente |
| G21 (tarifa fija) | `=IFERROR(IF(C10="FTE",G19/C13/Panel!C11,G19/L26/Panel!C11),0)` | G19, C13(FTE), C11(meses) | tarifa fija | `vision_tarifas tarifa_fijo_fte = facturacion/fte` | Divergencia (Excel /meses adicional) |
| G31 (tarifa variable) | `=IF(C11="Transacción",G29/FILTER(Panel!L19:L39,…)/Panel!C11, IF(OR(C11="Resultados",C11="Honorarios"),Tarifas!$C$77,0))` | C29, volumen, Tarifas!C77 | tarifa variable | `vision_tarifas tarifa_variable` | Pendiente (3 ramas) |
| G33 | `=IF(C11="Transacción",(SUM(C16,C26,C36)*D11)/G31,(G29+G31)/Tarifas!$C$133)` | C16/C26/C36, G31 | tarifa volumen/persona | — | Pendiente |
| G35 | `=IF(AND(unidad="FTE",M17,SUMPRODUCT(M17:O17×M17:O17)=1),752.815013404826,"")` | — | volumetría 1 FTE | (`grep 752.81` = 0) | **No encontrado** (constante mágica) |
| C259 | `=SUMPRODUCT('Nomina Loaded'!D15:BK33×(A="Activado"))` | Nomina Loaded región 1 | payroll A Total | `vision_tarifas`/agregado | Equivalente |
| C260-C264 | `=SUMPRODUCT(No payroll / Pólizas × "Activado")` | regiones consolidadas | no-payroll/ICA/GMF/pól/fin A Total | costos_financieros + no_payroll | Equivalente |

## Variables compartidas
- **factor_margenes** = `(1-C63)(1-C67)(1-C68)(1-C69)(1+C70)` → `utils.py:31 calcular_factor_margenes` — Equivalente.
- **C4/C5** (mes inicio/fin contrato), **C7** (mes inicio indexación), **NominaLoaded!C3** (offset) — internos de proyección mensual; no documentados individualmente en backend (embebidos en iteración por mes).

## No documentado (no extraído en evidencia previa)
- Fórmulas internas de `Costos Totales!E37/E8/E35`.
- Tabla destino de `INDEX('Ta…')` (indexación) — probable `Tasas, TRM, Polizas`.
- `HME!G6:G13` (factor márgenes local) — valores no extraídos.
- `Panel!L52` (volumen base), `Panel!L26` (divisor tarifa no-FTE).
