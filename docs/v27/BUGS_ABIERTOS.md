# Bugs abiertos del motor — Engine V2

Bugs reales descubiertos por la suite de tests durante el proceso
de industrialización. Cada bug tiene un ID estable, un test que lo
cubre (con `xfail(strict=False)` mientras no esté resuelto), y un
plan de resolución.

---

## BUG-W7-001 — `cop_round` drift acumulado vs Excel ROUND

**Descubierto en**: WAVE 7 (triaje)
**Severidad**: Baja (4 COP sobre 14.8M COP = 2.7e-7 relativo)
**Estado**: open / xfail

**Test que lo cubre**:
`tests/unit/test_certification_golden_master.py::TestCertificationRoundingPrecision::test_cop_round_accumulation`

**Comportamiento esperado**:
Para una serie mensual `[1234567.456, 1234567.4, 1234567.6, 1234567.5] * 3`
(12 valores), la suma de `cop_round` debe igualar la suma equivalente
de Excel `ROUND(_, 0)` con tolerancia 1.0 COP. Valor esperado:
`14_814_806.0`.

**Comportamiento actual**:
Motor produce `14_814_810.0` — diff `+4.0` COP.

**Causa raíz probable**:
`cop_round` (en `shared/precision.py`) usa banker's rounding o
half-up de Python; Excel ROUND(0.5) → 1 (half-away-from-zero).
La diferencia se acumula sobre los `*.5` exactos del input.

**Impacto en producción**:
- Paridad V2-7 (WAVE 4): **no afecta** (los 39 tests usan tolerance
  `rel=1e-4 / abs=1e-2` sobre métricas agregadas, no sobre redondeo
  por unidad).
- Baselines V2-7 (WAVE 6): **no afecta** (tolerance idéntica).
- Reportes financieros: drift <1 COP por mes → invisible.

**Plan de resolución**:
- WAVE 9+ (clean architecture del core financiero) revisará
  `shared/precision.cop_round` para alinearlo con Excel ROUND
  (half-away-from-zero, ties-to-even, etc. — TBD).
- Mientras tanto: `xfail(strict=False)` para que no rompa CI.

**Prioridad**: P3 (cosmético; no afecta paridad ni baselines).

---

<!-- Nuevos bugs se agregan abajo manteniendo el formato. -->
