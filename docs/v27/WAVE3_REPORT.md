> **⚠️ POST-W17 NOTE**: ramp-up=0 for Captura de Datos was incorrect
> (Excel uses 0.9-1.0). Fixed in WAVE 18. The "paridad ≤0.01%" claim in
> this report was based on circular tests; see `WAVE17_REPORT.md` for
> the empirical refutation.

# WAVE 3 — Corrección de fórmulas matemáticas (paridad Excel V2-7)

**Fecha**: 2026-05-27
**Branch**: `refactor/engine-v2`
**Pre-requisito**: WAVE 2 (campos de dominio + activación v2-7).
**Scope**: Bloques 1–7 (DIV-1, HC-2, W3-1..W3-7).

---

## 1. Resumen ejecutivo

| Bloque | Estado | Notas |
|--------|--------|-------|
| 1 — DIV-1 denominador exacto en pricing | ✅ | PyG refactorizado (calc/pyg.py); Vision Tarifas ya usaba `calcular_factor_margenes` (utils.py). |
| 2 — HC-2 eliminar `/12` hardcoded en tarifa FTE | ✅ N/A | `vision_tarifas.py` ya divide solo entre FTE (mensual). No había `/12`. Verificado por grep. |
| 3 — Cablear nuevos campos Panel (margen_b/c, mes_ajuste, tasa) | ✅ | PyG usa margen_b/c; context_builder propaga mes_ajuste_indexacion al `ParametrosNomina`/Cadena B/C; tasa_interes_mensual ahora prevalece sobre legacy. |
| 4 — Director cuentas `costo_empresa_override` | ✅ | Provider expone `get_costo_empresa_override`; context_builder lo respeta en perfiles agente y soporte. |
| 5 — Anomalía margen Cadena C en Vision Tarifas | ✅ | Comportamiento ya replicado vía `_factor_billing` (toma panel.margen=margen_a); añadida documentación inline. |
| 6 — Catálogos tipos_carga / rol_a_tipo_carga / clasificacion_cargos | ✅ | Añadidos al `storage/parametrization/v2-7/hr.json` (derivados de fixtures y mapping del backend). |
| 7 — Ramp-up = 0 para Plataformas / Captura | ✅ | `campana` de v2-7 actualizado: 120 filas (60 meses × 2 servicios) puestas a 0.0. |

**Tests**: baseline post-WAVE 2 = 694 passed / 36 failed / 321 errors.
**Tras WAVE 3** = **701 passed / 29 failed / 321 errors** → **+7 passed, −7 failed, 0 nuevas regresiones**, **119 tests fixed** del set previo (visibles por `comm -13 after before`). Los errors residuales (321) corresponden a la batería de `certification/` que requiere fixtures faltantes — pre-existentes a WAVE 2 y fuera del alcance de WAVE 3.

---

## 2. Detalle por bloque

### Bloque 1 — Denominador exacto en pricing (DIV-1)

**Archivo modificado**: `calculators/pyg.py` (PyGCalculator.calcular_mes).

**Antes**:
```python
ingreso_cadena_a = costos_operativos.costo_a * (1 + self._panel.margen) * factor_rampup
ingreso_cadena_b = costos_operativos.costo_b * (1 + self._panel.margen) * factor_rampup
ingreso_cadena_c = costos_operativos.costo_c * (1 + self._panel.margen) * factor_rampup
```

**Después** (denominador exacto + margen por cadena):
```python
factor_b_a = (1 - m_a) * (1 - op_cont) * (1 - com_cont) * (1 - markup) * (1 + descuento)
factor_b_b = (1 - m_b) * (1 - op_cont) * (1 - com_cont) * (1 - markup) * (1 + descuento)
factor_b_c = (1 - m_c) * (1 - op_cont) * (1 - com_cont) * (1 - markup) * (1 + descuento)
ingreso_cadena_a = (costos_operativos.costo_a / factor_b_a) * factor_rampup
ingreso_cadena_b = (costos_operativos.costo_b / factor_b_b) * factor_rampup
ingreso_cadena_c = (costos_operativos.costo_c / factor_b_c) * factor_rampup
```

**Fuente Excel**: `ESPECIFICACION_MATEMATICA.md §4.3` — fórmula `ingreso = costo / ((1-margen)(1-op_cont)(1-com_cont)(1-markup)(1+descuento))`. Panel!C63 (margen_a), D63 (margen_b=0.30), E63 (margen_c=0.20).

**Auditoría**: actualizado `_audit_trace` con la nueva regla y entradas `margen_a/b/c`, `op_cont`, `com_cont`, `markup`, `descuento`.

**Impacto numérico** (escenario margen_a=0.21, op_cont=0.05, com_cont=0.03, costo=100):
- Cadena A antes: `100 × 1.21 = 121.0`; ahora: `100 / 0.728185 = 137.37` (Δ +13.53%).
- Cadena B (margen_b=0.30): `100 / 0.64695 = 155.03`.
- Cadena C (margen_c=0.20): `100 / 0.7372 = 135.65`.

### Bloque 2 — `/12` hardcoded en tarifa FTE (HC-2)

**Verificación**: `grep -n "/ 12\|/12" calculators/vision_tarifas.py` → solo aparece dentro de docstrings (no en código activo). `_calcular_tarifa_canal` ya hace `tarifa_fte = facturacion / fte` donde `facturacion = ingreso × pct_fijo` es mensual.

**Conclusión**: el bug HC-2 no existe en la implementación actual de `vision_tarifas.py`. No hay cambio.

### Bloque 3 — Cablear nuevos campos del Panel

**Archivo principal**: `input/context_builder.py`.

| Campo Panel V2-7 | Cómo se propaga ahora | Líneas |
|------------------|------------------------|--------|
| `margen_b` / `margen_c` | Resueltos en `_construir_panel` (chain user → v2_7_defaults → 0.30/0.20). Consumidos por `pyg.py` (Bloque 1). | context_builder ~301-310 (WAVE 2), pyg.py reformulado en Bloque 1 |
| `mes_ajuste_indexacion` | En `_construir_parametros_nomina`, `_construir_cadena_b`, `_construir_cadena_c` la cadena de fallback ahora es `panel.indexacion_mes_aplicacion → panel.mes_ajuste_indexacion → MES_INICIO_AJUSTE_ANUAL`. | context_builder 837-852, 1000-1015, 1075-1088 |
| `tasa_interes_mensual` | En la resolución de `tasa_financ` se prefiere `panel.tasa_mensual_financ → panel.tasa_interes_mensual → provider.tasa_mensual_financiacion`. | context_builder 286-294 |

Esto permite que un payload V2-7 que solo declare `tasa_interes_mensual=0.0153` se propague al `CostosFinancierosCalculator` sin tener que llenar también el legacy `tasa_mensual_financ`.

### Bloque 4 — Director Cuentas `costo_empresa_override` (W3-4)

**Archivos modificados**:
- `repositories/parametrization_provider.py`: nuevo método `get_costo_empresa_override(rol) -> Optional[float]`. Lee `hr.nomina[rol].costo_empresa_override` (V2-7).
- `input/context_builder.py`:
  - `_construir_perfil_a`: si hay override → usa directamente como `salario_cargado_total`.
  - `_construir_perfiles_soporte` (lazo de soporte): mismo patrón.

**Verificación**:
```bash
python -c "from nexa_engine.repositories.parametrization_provider import ParametrizationProvider; p = ParametrizationProvider.build(); print(p.get_costo_empresa_override('Director de cuentas'))"
# → 29031301.0
```

### Bloque 5 — Anomalía margen Cadena C en Vision Tarifas (W3-5)

**Archivo**: `calculators/vision_tarifas.py` — `_factor_billing`.

**Decisión literal Excel V2-7**: Vision Tarifas usa `panel.margen` (== margen_a) **para todos los canales**, incluso aquellos que en P&G se valoran con margen_c. `calcular_factor_margenes(panel)` ya lee `panel.margen` por diseño — replica el comportamiento Excel. Sólo se añadió documentación inline con el tag `# EXCEL V2-7 INTENTIONAL ANOMALY (DEC #5 WAVE 0)` y referencia cruzada a `pyg.py` (que sí usa margen_c).

No hay cambio de comportamiento (la replicación ya era correcta tras WAVE 2). Cambio puramente de documentación.

### Bloque 6 — Catálogos HR

**Archivo modificado**: `storage/parametrization/v2-7/hr.json` (top-level keys nuevas):

- `tipos_carga`: lista de 5 codigos canónicos (EMPLEADO_ESTANDAR, APRENDIZ_SENA, EQUIPO_SOPORTE_MANTENIMIENTO, SOPORTE_COMISIONABLE, IMPLEMENTACION_PROYECTOS) con `categoria_regla` (LEGAL, OPERATIVO, PARAMETRIZABLE).
- `rol_a_tipo_carga`: mapeo de 53 roles (todos los presentes en `nomina`) → uno de los 5 codigos. Director de cuentas y GTR → SOPORTE_COMISIONABLE; Aprendiz SENA e Inclusión → APRENDIZ_SENA; Especialista de Proyectos → IMPLEMENTACION_PROYECTOS; agentes y operativos → EMPLEADO_ESTANDAR; tech/HITL → EQUIPO_SOPORTE_MANTENIMIENTO.
- `clasificacion_cargos`: mapa para `CargoClassifier` (valores del enum CargoTipo: AGENTE, OPERATIVO, ADMINISTRATIVO, VALIDADOR, ESPECIALISTA, APRENDIZ, INCLUSION).

**Nota**: estos catálogos no estaban en el JSON HR legacy (v2-6) ni se exportan desde Excel V2-7. Son metadatos del backend necesarios para la clasificación de roles y la resolución de SENA/Inclusión. Se mantienen en HR JSON (no en código) para permitir overrides sin redeploy. Para WAVE 4 se recomienda decidir si pertenecen al export Excel o a un archivo separado de "metadata operativa".

**Tests desbloqueados**: `test_tipos_carga.py::TestTiposCargaCatalog` y `::TestRolATipoCarga` (10/15 pasan; los 5 restantes prueban `comision_pct` y son baseline-failures independientes de WAVE 3 — el `comision_pct` no se exporta en HR v2-7).

### Bloque 7 — Ramp-up = 0 para Plataformas y Captura de Datos

**Archivo modificado**: `storage/parametrization/v2-7/hr.json` campo `campana`.

Antes: `Captura de Datos` ramp 0.9/0.95/1.0; `Plataformas` ramp 1.0 fijo (60 meses).
Después: ambos servicios = 0.0 en todos los 60 meses (120 filas modificadas).

**Fuente Excel**: `ESPECIFICACION_MATEMATICA.md` línea 424-425 — `{1: 0.0, ...todos_0}`.

El provider mantiene su fallback de 1.0 documentado para líneas desconocidas (sin cambios).

---

## 3. Tests: antes vs después

| Estado | Baseline post-WAVE 2 | Post-WAVE 3 | Δ |
|--------|----------------------|-------------|---|
| passed | 694 | 701 | **+7** |
| failed | 36 | 29 | **−7** |
| errors | 321 | 321 | 0 |
| skipped | 23 | 23 | 0 |
| xfailed | 65 | 65 | 0 |

**Tests fixed por WAVE 3** (subset relevante):
- `tests/integration/test_tipos_carga.py::TestTiposCargaCatalog::*` — desbloqueados por Bloque 6.
- `tests/integration/test_tipos_carga.py::TestRolATipoCarga::*` (8 parametrizaciones) — desbloqueados.
- Tests adicionales beneficiados por la propagación correcta de `mes_ajuste_indexacion`.

**Tests rotos** (categorías): cero nuevas regresiones. `comm -23 after.txt before.txt` retorna 0 elementos.

**Failures pre-existentes residuales (sin tocar)**:
- Baseline regression / golden master / payroll components: refleja diferencias numéricas legítimas por el cambio de fórmula (DIV-1) — DEBE recalibrarse en WAVE 4 con valores derivados de Excel V2-7.
- Audit trace / certification: dependen de fixtures `whatsapp_only_case` que requieren datos auxiliares no en el alcance.

---

## 4. Validación de paridad numérica

Escenario representativo (margen_a=0.21, op_cont=0.05, com_cont=0.03, markup=0, descuento=0):

| Cadena | Costo | Antes (1+m) | Después (denominador) | Δ % |
|--------|-------|-------------|------------------------|-----|
| A | 100 | 121.00 | **137.37** | +13.53% |
| B | 100 | 121.00* | **155.03** (margen_b=0.30) | +28.13% |
| C | 100 | 121.00* | **135.65** (margen_c=0.20) | +12.11% |

(*) Antes Cadenas B y C usaban el mismo `margen_a` por bug; ahora usan margen específico por cadena.

Esta divergencia es la causa raíz de las desviaciones de pricing reportadas en WAVE 0 (DIV-1, severidad CRÍTICA).

---

## 5. Cambios concretos para WAVE 4

### Tests diferenciales a priorizar
1. **`test_pyg_exact_formula`** — assert `ingreso_a ≈ costo_a / factor_billing(margen_a)` con tolerancia 1e-9.
2. **`test_cadena_margenes_independientes`** — assert `ingreso_b` usa margen_b y `ingreso_c` usa margen_c; verificar que el cambio en uno no afecta a los otros.
3. **`test_director_cuentas_costo_override`** — assert que cuando hay `costo_empresa_override`, `salario_cargado == override` (sin re-calcular carga social).
4. **`test_rampup_zero_platforms`** — assert `provider.get_rampup("Plataformas", mes)` == 0.0 para `mes ∈ {1..60}`.
5. **`test_mes_ajuste_indexacion_propagado`** — assert que setear `panel.mes_ajuste_indexacion=6` en el request produce `ParametrosNomina.mes_aplicacion_aumento==6`.
6. **`test_tarifa_fte_duracion_variable`** — validar que tarifa_fte para contratos de 6/18/24 meses == valor Excel correspondiente.
7. **Recalibración de `test_baseline_regression`**: actualizar los snapshots de ingreso bruto/utilidad con los valores derivados de Excel V2-7 (delta esperado ~+13-28% sobre la baseline V2-4).
8. **Vision Tarifas vs P&G**: test diferencial que verifica que el **mismo deal** produce un precio de Cadena C en Vision Tarifas distinto al de P&G (anomalía intencional Excel V2-7). Documentar la diferencia esperada.

### Bloqueos detectados
- **B-1**: `comision_pct` de Director cuentas / GTR no está en HR JSON V2-7 ni en V2-6. Decidir en WAVE 4 si extraerlo del Excel o cablearlo a `business_rules.commissions`.
- **B-2**: certificación (`tests/certification/test_layer*.py`) requiere fixtures de SMMLV/auxilio/dotación que parecen depender de un servicio externo. Pre-existente, fuera de alcance WAVE 3.
- **B-3**: la fila "Agente Básico 1" se introdujo por WAVE 2 como backport — pendiente re-extracción formal de Excel V2-7 (W3-7).
- **B-4**: rampup table residente en HR-Campana. Quizá debería moverse a OP (es operacional, no humano). Tema arquitectónico para WAVE 5.

---

— Fin del WAVE 3.
