# GAP-SALARIO-CARGADO — Divergencia en salario_cargado por FTE Cadena A

> Registrado durante paridad oracle AMERICAS / Captura de Datos.
> **Decisión de negocio pendiente.** NO modificar código hasta resolución.

## Descripción

El backend calcula `salario_cargado` para el perfil "Inbound 25" (Voz/Inbound)
usando el **HR-catalog** de storage (salario base + cargas sociales desde
parámetros maestros). El Excel V2-7 lo calcula en **Nomina Loaded** iterando
las cargas sociales sobre el salario imponible real de cada perfil.

## Valores medidos (deal AMERICAS / Captura de Datos, 12m, 25 FTE Voz)

| Origen | Salario cargado / FTE | Payroll 25 FTE / mes | Σ 12 meses |
|---|---:|---:|---:|
| **Excel** (`NominaLoaded!C93 / 25`) | **3.288.748,49** | **82.218.712,28** | **986.624.547,40** |
| **Backend** (`PerfilCadenaA.salario_cargado`) | **2.900.432,62** | **72.510.815,46** | **870.129.785,52** |
| **Diferencia / FTE** | **388.315,87** | **9.707.896,82/mes** | **116.494.761,88** |

## Impacto en el oracle de Cadena A

| Celda | Δ% atribuible | Magnitud |
|---|---:|---:|
| C41 payroll A | **+1,453%** (+15,1M) | causa directa |
| C40 costo A total | +0,119% (post-fix C42) | derivado de C41 |
| C47 ingreso A | +0,119% | derivado de C40 |
| C43 ICA A | +0,652% | derivado (base mayor) |
| C44 GMF A | +0,524% | derivado |
| BK31 acum deal-wide | parte del +12,57% | combinado con otros gaps |

## Causa raíz

El Excel `NominaLoaded` calcula la nómina cargada completa aplicando:
prestaciones de ley (salud 8,5%, pensión 12%, SENA 2%, ICBF 3%, caja 4%,
ARL, vacaciones 4,17%, prima 8,33%, cesantías 8,33%, intereses cesantías 1%)
sobre el salario imponible real. El backend usa `salario_cargado` del
HR-catalog que puede diferir en el % efectivo de cargas sobre ese perfil.

El Excel R39 (Inputs Nomina) muestra `salario_base=1.750.905` y
`variable=122.563,35 (comisión=10%)`. El backend también parte de esos inputs
pero la nómina cargada resultante (2.900.432/FTE) es distinta a la del Excel
(3.288.748/FTE). La diferencia (~13,4%) sugiere que el backend no aplica todas
las cargas que el Excel sí aplica para este tipo de perfil.

## Decisión pendiente

**¿Qué metodología es autoritativa para el salario_cargado?**

- **Opción A — Excel (Nomina Loaded):** la nómina cargada debe replicar la
  secuencia de cargas sociales del Excel. Requiere revisar
  `domain/payroll/calculators.py` y los parámetros de carga de HR-catalog
  para este tipo de empleado (Agente Básico / Empleado Estándar).

- **Opción B — HR-catalog (backend):** el backend define la base normativa;
  el Excel puede estar configurado diferente para este deal específico.
  Documentar la diferencia como variación del deal, no como bug.

**Sin decisión: NO modificar `domain/payroll/calculators.py` ni
`storage/parametrization/hr/`.**

## Referencias

- Oracle: `test_cases/input/americas_captura_datos.json`
- Calculator: `domain/payroll/calculators.py`, `input/context_builder.py:_construir_perfil_a`
- Storage: `storage/parametrization/hr/*.json` (salario por rol + cargas)
- Excel: `Nomina Loaded!C93:C112` (salario por canal/perfil, mes 1 contrato)
