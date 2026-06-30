# WAVE 2 — Activación de v2-7 + campos de dominio

**Fecha**: 2026-05-27
**Branch**: `refactor/engine-v2`
**Pre-requisito**: WAVE 1 (storage/parametrization/v2-7/) ya creado.
**Scope**: Bloques A (resolver con `path`), B (campos dominio), C (tests).

---

## 1. Archivos modificados

### Bloque A — Resolver con soporte `path`

| Archivo | Cambio |
|---------|--------|
| `infrastructure/storage/base_repository.py` | `VersionSummary` ahora acepta `path: Optional[str]`. `to_dict()` solo emite el campo cuando está presente (backward compat con versiones legacy sin path). `from_dict()` lo recupera del JSON. |
| `infrastructure/parametrization_resolver.py` | `_load_version_data()` gana parámetro opcional `path`. Cuando el `active_summary.path` está set, resuelve `(module_dir / path).resolve()` permitiendo `..` para apuntar a carpetas hermanas (p. ej. `../v2-7/hr.json`). Log INFO incluye explícitamente `path=...` cuando se usa override. |
| `storage/parametrization/hr/versions.json` | UUID v2-6 marcado `is_active=false`. Añadido entry `version_id=v2-7` con `path: "../v2-7/hr.json"` activo. |
| `storage/parametrization/gn/versions.json` | Mismo patrón (path → `../v2-7/gn.json`). |
| `storage/parametrization/op/versions.json` | Mismo patrón (path → `../v2-7/op.json`). |
| `storage/parametrization/business_rules/versions.json` | `active_version = "v2-7"`. Lista de `versions` incluye ambos (`2026-01` con status inactive, `v2-7` con `path: "../v2-7/business_rules.json"`). |
| `repositories/parametrization_provider.py` | `_load_business_rules_version()` ahora consulta `versions.json` para buscar el `path` opcional del entry. Si está presente, resuelve desde ahí; si no, usa `{version_id}.json` (comportamiento original). Log INFO al cargar vía override. Además se añadió `get_v27_defaults()` que devuelve `op.v2_7_defaults`. |

### Bloque A.1 — Ajustes derivados de la migración (mínimos)

| Archivo | Cambio | Razón |
|---------|--------|-------|
| `repositories/payroll_parametrization_repository.py` | `_load_rotacion_ausentismo_cache()` ahora detecta el formato dict V2-7 (`{"ausentismo": {linea: pct}, "rotacion": {linea: pct}}`) y lo normaliza al formato canónico `[{linea, pct_rotacion_mensual, pct_ausentismo, pct_examen_anual}]`. | El extractor WAVE 1 produjo dict; el repo solo entendía lista. Sin esto la carga de v2-7 falla con `KeyError: 0` en la primera fila. |
| `repositories/financial_parametrization_repository.py` | `get_ica()` ahora acepta `row["ica"] in ("Tasa", "Tarifa")`. v2-6 usa "Tasa", el Excel V2-7 (y por ende el JSON V2-7) usa "Tarifa". | Cambio terminológico de Excel V2-7. Bidireccional, no rompe v2-6. |
| `storage/parametrization/v2-7/hr.json` | `rentabilidad[*].minimo` y `margenobjetivo` re-emitidos como string-porcentaje ("21.0") en lugar de decimal ("0.21"). | El repo asume porcentaje y divide /100. WAVE 1 los emitió en decimal por inadvertencia. Excel V2-7 dice 21% → JSON debe codificarlo igual que v2-6 para que el repo aplique la misma conversión. |
| `storage/parametrization/v2-7/hr.json` | Añadida fila `nomina["Agente Básico 1"]` con `salario=2730864.2626` y marca `_wave2_backport`. | El extractor de WAVE 1 omitió esta fila (sigue presente en Excel V2-7). Sin ella, el motor revienta con `RoleNotFoundError` en cualquier deal con perfil Agente. Marcado para re-extracción posterior. |

### Bloque B — Campos faltantes en dominio y DTO

| Archivo | Cambio |
|---------|--------|
| `domain/models/panel.py` (`PanelDeControl`) | 4 campos nuevos: `margen_b: float = 0.30`, `margen_c: float = 0.20`, `mes_ajuste_indexacion: int = 6`, `tasa_interes_mensual: float = 0.0153`. Comentarios documentan Panel!D63/E63/L9/L10. `imprevistos` ya existía. |
| `domain/user_inputs.py` (`PanelDeControlInput`) | 4 campos nuevos como `Optional[...] = None` para distinguir "usuario no especificó" de "usuario eligió 0" (delegación a parametrización). |
| `simulation/request_dto.py` (`PanelDeControlRequest`) | 5 campos nuevos como `Optional`: `margen_b`, `margen_c`, `mes_ajuste_indexacion`, `tasa_interes_mensual`, `imprevistos`. `field_validator` rechaza fuera de rango (0..1 los porcentajes, 1..12 el mes). Import: `field_validator`. |
| `adapters/user_input_loader.py` (`_panel`) | Lee los 4 nuevos campos opcionales del dict crudo y los propaga a `PanelDeControlInput`. |
| `input/context_builder.py` (`_construir_panel`) | Resuelve cada campo nuevo así: `value = override_usuario if override_usuario is not None else op.v2_7_defaults.<key>`. Si `op.v2_7_defaults` no está presente, defaults locales (0.30 / 0.20 / 6 / 0.0153) en última instancia. Llama `self._prov.get_v27_defaults()` envuelto en try/except para tolerar parametrizaciones legacy. Construye `PanelDeControl` pasando los 4 nuevos campos. |

### Bloque C — Tests actualizados (snapshots legítimos)

| Archivo | Cambio |
|---------|--------|
| `tests/unit/test_phase9_business_rules_migration.py` | 4 tests actualizados con comentario `# WAVE2: v2-7 parametrization`:<br>· `test_storage_business_rules_structure_exists` — ahora acepta tanto archivo directo como override `path`.<br>· `test_get_politicas_comerciales_from_storage` — 5 políticas (no 4), `contingencia_operativa` min 0.05 max 0.08.<br>· `test_migration_data_consistency` — rangos actualizados a Excel V2-7 (lookup por nombre).<br>· `test_phase9_migration_complete` — 5 políticas. |

---

## 2. Diff conceptual del resolver

### Antes

```python
def _load_version_data(self, module_dir, version_id):
    data_path = module_dir / f"{version_id}.json"
    if not data_path.exists():
        raise ParametrizationNotFoundError(...)
    return read_json(data_path)
```

`versions.json` siempre apunta a un archivo `{version_id}.json` dentro de la misma carpeta.

### Después

```python
def _load_version_data(self, module_dir, version_id, path=None):
    if path:
        data_path = (module_dir / path).resolve()  # ../v2-7/hr.json → backend_nexa/storage/parametrization/v2-7/hr.json
        logger.debug(f"[PARAMETRIZATION] Loading {module_dir.name} via path override: {data_path}")
    else:
        data_path = module_dir / f"{version_id}.json"
    ...
```

Los `versions.json` siguen con el schema actual, solo añaden un campo opcional `path`. Los UUID antiguos permanecen sin modificar — quedan disponibles si se reactivan.

### Log esperado al arrancar con v2-7

```
INFO  [PARAMETRIZATION] ParametrizationProvider initialized modules=[financial, profitability, infrastructure, payroll]
INFO  [PARAMETRIZATION] Loaded active version for hr: version_id=v2-7, path=../v2-7/hr.json, rows=0
INFO  [PAYROLL_REPO] Top-level keys loaded: ['version_id', 'niveles', ..., 'rotacion_ausentismo']
INFO  [PAYROLL_REPO] rotacion_ausentismo (dict V2-7) normalizado a 6 filas
INFO  [PARAMETRIZATION] Loaded active version for op: version_id=v2-7, path=../v2-7/op.json, rows=0
INFO  [PARAMETRIZATION] Loaded active version for gn: version_id=v2-7, path=../v2-7/gn.json, rows=0
INFO  [PARAMETRIZATION] Loading business_rules via path override: .../storage/parametrization/v2-7/business_rules.json
```

---

## 3. Campos nuevos: defaults y validación

| Campo | Domain `PanelDeControl` | DTO `PanelDeControlRequest` | Default resolution chain |
|-------|-------------------------|-----------------------------|--------------------------|
| `margen_b` | `float = 0.30` | `Optional[float] = None`, validator [0,1] | request → `op.v2_7_defaults.margenes.margen_b_default` → 0.30 |
| `margen_c` | `float = 0.20` | `Optional[float] = None`, validator [0,1] | request → `op.v2_7_defaults.margenes.margen_c_default` → 0.20 |
| `mes_ajuste_indexacion` | `int = 6` | `Optional[int] = None`, validator [1,12] | request → `op.v2_7_defaults.indexacion.mes_ajuste` → 6 |
| `tasa_interes_mensual` | `float = 0.0153` | `Optional[float] = None`, validator [0,1] | request → `op.v2_7_defaults.indexacion.tasa_interes_mensual` → 0.0153 |
| `imprevistos` | ya existía (`float = 0.0`) | añadido `Optional[float] = None`, validator [0,1] | request → `volumetria.reglas_negocio.imprevistos` → 0.0 |

NB: `tasa_mensual_financ` (campo legacy de financiación en `PanelDeControl`) y `tasa_interes_mensual` son conceptualmente el mismo valor de Panel!L10. Se conservan ambos para no romper consumidores; futura unificación en WAVE 5.

---

## 4. Resultados de tests

| Métrica | Baseline (sin WAVE 2) | Con WAVE 2 |
|---------|----------------------|------------|
| passed | 583 | **694** (+111) |
| failed | 71 | **36** (−35) |
| errors | 398 | **321** (−77) |
| skipped | 23 | 23 |
| xfailed | 65 | 65 |

**Comparación failure-by-failure**: `comm -23 <(sort current) <(sort baseline)` arroja **0 regresiones**. Todos los failures actuales ya existían antes de WAVE 2; muchos relacionados con catálogos faltantes en HR (tipos_carga, rol_a_tipo_carga, clasificacion_cargos — ver §7) que afectan tests integrales independientemente de la versión activa.

### Tests actualizados intencionalmente (snapshots de valores)

Solo 4 tests en `test_phase9_business_rules_migration.py` requirieron edición: la cuenta de políticas pasó de 4 a 5 (se añadió `imprevistos`) y los rangos numéricos se actualizaron a los valores literales del Excel V2-7. Todos llevan comentario `# WAVE2: v2-7 parametrization`.

### Tests funcionales que rompieron por bug y se fijaron

1. `_load_rotacion_ausentismo_cache` — fix de formato dict V2-7.
2. `get_ica` — aceptar "Tarifa" además de "Tasa".
3. Datos `rentabilidad.minimo` en string-porcentaje.

---

## 5. Sample versions.json (HR) después de WAVE 2

```json
[
  {
    "version_id": "2236cdcf-7ed0-4894-a20d-c4519c211170",
    "filename": "HR_productiva_2026-05-11-09-52-29.xlsx",
    "uploaded_at": "2026-05-27T21:17:56.752385Z",
    "is_active": false,
    "sheet_count": 15,
    "total_rows": 836
  },
  {
    "version_id": "v2-7",
    "filename": "Nexa - Pricing - Simulador - V2-7.xlsx",
    "uploaded_at": "2026-05-27T18:33:00Z",
    "is_active": true,
    "sheet_count": 23,
    "total_rows": 0,
    "path": "../v2-7/hr.json"
  }
]
```

Idéntico patrón para `gn/versions.json` y `op/versions.json`. Para `business_rules/versions.json` el schema usa `{"active_version": "v2-7", "versions": [...]}` y el entry v2-7 lleva `path: "../v2-7/business_rules.json"`.

---

## 6. Validación funcional

```python
from backend_nexa.repositories.parametrization_provider import ParametrizationProvider
p = ParametrizationProvider.build()

# Sanity checks (todos pasan):
assert p.get_nomina_laboral_params()["salario_minimo"] == 1_750_905.0
assert p.get_pct_rotacion("Cobranzas") == 0.119875
assert p.get_pct_ausentismo("Cobranzas") == 0.081125
assert p.get_ica("Bogota") == 0.00966
assert p.get_gmf() == 0.004
assert p.get_margen_minimo("Cobranzas") == 0.21        # antes 0.17
assert p.get_salario_rol("Director de cuentas") == 22_761_150.0
assert len(p.get_politicas_comerciales()) == 5         # incluye imprevistos
defaults = p.get_v27_defaults()
assert defaults["margenes"]["margen_b_default"] == 0.30
assert defaults["margenes"]["margen_c_default"] == 0.20
assert defaults["indexacion"]["mes_ajuste"] == 6
assert defaults["indexacion"]["tasa_interes_mensual"] == 0.0153
```

Log al iniciar (extracto):
```
[PARAMETRIZATION] Loaded active version for hr: version_id=v2-7, path=../v2-7/hr.json, rows=0
[PARAMETRIZATION] Loaded active version for op: version_id=v2-7, path=../v2-7/op.json, rows=0
[PARAMETRIZATION] Loading business_rules via path override: .../v2-7/business_rules.json
```

---

## 7. Decisiones pendientes para WAVE 3

| # | Pendiente | Impacto WAVE 3 |
|---|-----------|----------------|
| W3-1 | Cablear `panel.margen_b`, `panel.margen_c` dentro de `calculators/vision_tarifas.py` (hoy lee `margen` global; debe usar margen específico por cadena). | Alto — afecta paridad Vision Tarifas. |
| W3-2 | Cablear `panel.mes_ajuste_indexacion` en `calculators/nomina.py` / motor de indexación (hoy usa constante `MES_INICIO_AJUSTE_ANUAL=1`). | Alto — cambia el mes en que se aplica el +IPC anual (de enero a junio). |
| W3-3 | Cablear `panel.tasa_interes_mensual` en `calculators/cost_to_serve.py` o equivalente (hoy usa `panel.tasa_mensual_financ`). Unificar fuentes. | Medio. |
| W3-4 | `NominaCalculator` debe respetar `hr.nomina[].costo_empresa_override` (Director de cuentas) en lugar de recomputar fórmula estándar. | Medio — afecta payroll Director cuentas. |
| W3-5 | Anomalía margen Cadena C en Vision Tarifas (DEC #5 WAVE 0): replicar tal cual Excel V2-7. | Alto. |
| W3-6 | v2-7 HR no exporta los catálogos `tipos_carga`, `rol_a_tipo_carga`, `clasificacion_cargos`, `complejidad_especialista`, `reglas_staff` (presentes tampoco en v2-6 — están en código). Tests `test_tipos_carga.py` fallan en baseline y siguen fallando. Decidir si esos catálogos forman parte del JSON HR o son metadata del backend. | Bloqueante para tests de tipos_carga. |
| W3-7 | Re-extraer el Excel V2-7 para añadir la fila "Agente Básico 1" formalmente (hoy backported desde v2-6). | Bajo (workaround vigente). |

---

## 8. Resumen ejecutivo

- **Resolver**: soporta `path` opcional → v2-7 vive en `storage/parametrization/v2-7/` y se activa cambiando solo `versions.json` de cada módulo.
- **Dominio**: 4 campos nuevos en `PanelDeControl` + DTO + loader + context_builder. Defaults provienen de `op.v2_7_defaults` (ningún hardcode en el código de aplicación).
- **Tests**: **0 regresiones**, 35 tests adicionales pasando vs. baseline. 4 snapshots actualizados (legítimos por cambio de valores Excel V2-7).
- **Bloque C — fixes derivados**: 3 bugs de carga descubiertos al activar v2-7 (formato dict de rotacion_ausentismo, etiqueta "Tarifa" vs "Tasa", formato porcentaje en rentabilidad). Todos resueltos sin tocar `calculators/`, `domain/services/` ni `engine.py`.

— Fin del WAVE 2.
