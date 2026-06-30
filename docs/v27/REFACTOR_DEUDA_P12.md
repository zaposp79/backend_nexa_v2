# Deuda técnica registrada — resolver en P12 (consolidación)

## D9 — calcular_factor_aumento en shared_calc/utils.py

**Archivo:** `modules/shared_calc/utils.py:56-61`  
**Función:** `calcular_factor_aumento`

**Situación:**  
La función es un wrapper de backward-compat (WAVE 9 strangler fig) que delega
mediante un lazy import a `PayrollCalculator` (que P5a movió a
`modules/cadena_a/payroll/calculators.py`):

```python
# modules/shared_calc/utils.py:56-61
def calcular_factor_aumento(mes: int, pct_aumento: float, mes_aplicacion: int) -> float:
    from nexa_engine.modules.cadena_a.payroll.calculators import PayrollCalculator
    return PayrollCalculator.calcular_factor_aumento(mes, pct_aumento, mes_aplicacion)
```

El import es lazy (dentro de la función), por lo que no crea un import circular
en carga de módulo. No rompe el gate en P5a. Sin embargo, viola el DAG conceptual:
`shared` → runtime-dep → `cadena_a`.

**Acción en P12:**  
Copiar inline la lógica de `calcular_factor_aumento` (3 líneas matemáticas puras,
sin estado, sin deps externas) y eliminar el lazy import:

```python
# Lógica a copiar desde PayrollCalculator.calcular_factor_aumento:
def calcular_factor_aumento(mes: int, pct_aumento: float, mes_aplicacion: int) -> float:
    if mes < mes_aplicacion:
        return 1.0
    n = (mes - mes_aplicacion) // 12 + 1
    return (1.0 + pct_aumento) ** n
```

Verificar que la lógica copiada produce resultados idénticos (test_calculators_utils.py
ya tiene cobertura completa: meses 1-12, 13-24, 25-36, pct=0, mes_aplicacion=1).

**Impacto:** solo `modules/shared_calc/utils.py` — 0 cambio de comportamiento.
