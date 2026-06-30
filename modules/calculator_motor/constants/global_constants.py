"""
Constantes del motor financiero NEXA.

Valores que NO varían por deal, parametrización ni cliente.
Cambios aquí impactan TODOS los cálculos globalmente.

Regla arquitectónica: Si un valor NO cambia entre deals, NO debe estar
en parametrización ni en input — debe ser una constante aquí.
"""

# ────────────────────────────────────────────────────────────────────────────
# Indexación y Ajustes Anuales
# ────────────────────────────────────────────────────────────────────────────

# Mes en que aplica el ajuste anual (indexación salarial/tecnológica)
# Valor: 1 = enero (estándar fiscal Colombia)
# Fuente Legal: Ley 1393 de 2010 Art. 3 (reajuste SMMLV)
# Usado en: SimulationContextBuilder, NominaCalculator, CadenaCCalculator
MES_INICIO_AJUSTE_ANUAL = 1

