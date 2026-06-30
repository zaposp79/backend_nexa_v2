# Grafo de Dependencias entre Hojas (Excel V2-7) — F3

## Alcance y limitaciones
- **Cubre:** grafo de dependencias entre hojas, derivado de las referencias `'Hoja'!Celda` extraídas en las auditorías previas (Visión Imprimible, P&G, Tarifas, CTS, Cadena A Fases 1-3). Dirección: `A → B` = "A consume/referencia a B".
- **NO cubre:** paridad de valor; dependencias internas celda-a-celda (ver `REVERSE_TRACE_VISION_IMPRIMIBLE.md` y `FORMULA_REGISTRY_CADENA_A.md`); cadenas B/C en detalle.
- **Cómo usar:** entender el orden de cálculo y el impacto de un cambio aguas arriba. **No es certificación.**
- Relacionados pre-existentes: `MAPA_DEPENDENCIAS.md`, `CERTIFICATION_FORMULA_DEPENDENCY_MAP.md` (este doc es la vista consolidada Cadena-A-first).

## Grafo (dirección: consumidor → fuente)

```
Visión Imprimible
  → Vision Tarifas_Modelo_Cobro   (B19=C72, B36=C33, B38=G47, D38=G55, escenarios C20:G21, C29)
  → Visión P&G                    (H19=BK30/E6)
  → Vision Cost To Serve          (T19=C200, H87=C200/C9)
  → Riesgo                        (B87=E17, B90=E16, B92=E18, criterios E3:E12/D3:D12/N3:N12)
  → Panel de Control General      (ficha §01, contingencias §07: C63:E70)

Vision Cost To Serve
  → Visión P&G                    (C186=Σ P&G!C31:BJ31,C45:BJ45,C55:BJ55 ; T19=P&G!BK27)
  → Vision Tarifas_Modelo_Cobro   (B19=C72, H19=C40+C50+C60, B20=C29)
  → Panel de Control General      (reglas C63:C73 — 1321 refs)
  → Nomina Loaded, No payroll, Costos Totales, Costo Fijo/Variable/Cadena C, Condiciones Cadena A

Visión P&G
  → Costos Totales                (payroll/no payroll consolidado)
  → Nomina Loaded                 (filas 93-112, 182-475: componentes payroll)
  → No payroll                    (filas 107-125, 186, 248)
  → Costo Fijo, Costo Variable    (Cadena B)
  → Costo Cadena C                (Cadena C)
  → Pólizas - Costo Financiacion  (ICA/GMF/Comisión/Pólizas/Financiero, filas 12-456)
  → Condiciones Cadena A          (C14 estaciones = E19:S19)
  → Rot, Ausent y Rentabilidad    (C15 ramp-up = INDEX B38:BI43 ; C63 margen)
  → Panel de Control General      (C63/C67-C70/C73 reglas; C5 servicio; C10/C11 fechas)

Vision Tarifas_Modelo_Cobro      (⚠ 0 refs a P&G y 0 a CTS — independiente en Excel)
  → Panel de Control General      (escenarios C81:C113; margen C63/D63/E63; reglas C67:C70; activación M/N/O 17/30, matrices M/S/K 19:39)
  → Hoja Maestra Escenarios       (facturación C47/C95…; tarifas G21/G31/G33; totales C259-C284; offset +48/escenario)
  → Nomina Loaded                 (filas 15-33 consolidado, por canal×modalidad)
  → No payroll                    (filas 14-32 consolidado)
  → Costo Fijo, Costo Variable    (Cadena B)
  → Costo Cadena C                (Cadena C, filas 40-85)
  → Pólizas - Costo Financiacion  (subset por cadena/canal)
  → Condiciones Cadena A          (C37 FTE = SUMIFS E17:S17)

Hoja Maestra Escenarios
  → Panel de Control General      (escenarios C81:C113; activación N/M; L19:L39)
  → Condiciones Cadena A          (C13 FTE = SUMIFS E17:S17)
  → Nomina Loaded                 (C259 = SUMPRODUCT D15:BK33)
  → No payroll                    (C260)
  → Pólizas - Costo Financiacion  (C261-C264)
  → Vision Tarifas_Modelo_Cobro   (G31 ← Tarifas!C77 ; G33 ← Tarifas!C133)   [acoplamiento bidireccional]

Nomina Loaded
  → Panel de Control General      (M19:M25 activación, K19:K25 canal, C4/C5/C7 ventana+indexación)
  → Tasas, TRM, Polizas           (INDEX tabla de indexación — destino INDEX('Ta…'), no extraído)
  (Región 1 filas 15-33 = Σ regiones componente 93/182/238/287/349/407/455)

No payroll
  → Panel de Control General      (M19:M25, K19:K25, C4/C5/C7)
  (Región 1 filas 14-32 = Σ componentes 107/186/248)

Pólizas - Costo Financiacion
  → Costos Totales                (E37 base costo, E8/E35 índice mes)
  → Panel de Control General      (M17/M19:M25 activación; C34 ICA, C35 GMF; C63/C67-C70 factor; C11 meses)
  → Nomina Loaded                 (C3 offset)
  (E198 LET → config pólizas filas 173-185 con vigencia G>=mes)

Condiciones Cadena A
  → (inputs: modalidad/canal/FTE/presencia E14:S19) — hoja raíz de staffing A

Rot, Ausent y Rentabilidad        (hoja raíz)
  → (inputs: margen por servicio B29:B34; ramp-up B38:BI43; índice mes B37:BI37)

Panel de Control General
  → Rot, Ausent y Rentabilidad    (C63 = FILTER B29:B34 por servicio C5)
  (resto: inputs directos del deal)
```

## Hojas raíz (sin dependencias salientes relevantes / solo inputs)
- `Condiciones Cadena A` — staffing input.
- `Rot, Ausent y Rentabilidad` — margen por servicio + ramp-up (matrices input).
- `Panel de Control General` — inputs del deal (excepto C63 → Rot).
- `Tasas, TRM, Polizas` — tablas de tasas/indexación (destino de `INDEX('Ta…')`, **no extraído en detalle**).

## Observaciones de orden de cálculo
1. **Cadena de ingreso A**: Condiciones A + Rot/Ausent → Nomina/No payroll → (Tarifas | P&G) → CTS → Visión Imprimible.
2. **Tarifas es independiente de P&G/CTS en Excel** (0 refs); el acoplamiento `Tarifas↔HME` es bidireccional (HME!G31/G33 leen Tarifas!C77/C133).
3. **Pólizas tiene acoplamiento interno**: ICA/GMF (E12/E93) suman Pólizas (E198) + Financiero (E378) en su base → orden ICA←Pólizas←config.
4. **Dependencia no extraída**: tabla de indexación destino de `INDEX('Ta…')` en Nomina/No payroll (probable `Tasas, TRM, Polizas`).
