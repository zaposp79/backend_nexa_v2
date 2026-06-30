# FASE 1 — Mapa de Origen de Datos y Auditoría de Hardcodes

**Fecha:** 2026-05-26
**Objetivo:** Mapear el origen de cada dato en el pipeline. Identificar hardcodes, defaults silenciosos, valores mágicos.

---

## 1. Hardcodes Críticos (MUST FIX)

| # | Archivo | Línea | Hardcode | Valor | Riesgo | Acción |
|---|---------|-------|----------|-------|--------|--------|
| H1 | `adapters/context_builder.py` | 751 | Año fallback en `_anio_inicio()` | `2026` | ALTO — afecta indexación de todo el contrato | Raise `ValueError` en lugar de fallback silencioso |
| H2 | `adapters/user_input_loader.py` | 208 | Ciudad default en `_normalizar_entry_data_format()` | `"Bogota"` | ALTO — afecta ICA, costos infraestructura | Raise si falta `ciudad` (campo requerido) |
| H3 | `adapters/user_input_loader.py` | 316 | Ciudad default en `_panel()` | `"Bogota"` | ALTO — duplicado de H2 | Raise si falta `ciudad` |
| H4 | `adapters/user_input_loader.py` | 245,258 | Salario fallback | `1423000` | MEDIO — solo cuando `salario_base_default` no existe en entry_data | Documentar como fallback explícito del SMMLV |
| H5 | `adapters/user_input_loader.py` | 276 | precio_unitario para canales B derivados | `50.0` | BAJO — solo path de derivación automática | Documentar como default de entry_data |
| H6 | `adapters/user_input_loader.py` | 210,318 | Fecha inicio fallback | `"2026-01-01"` | MEDIO — afecta indexación | Raise si falta `fecha_inicio` |
| H7 | `adapters/user_input_loader.py` | 220,325 | periodo_pago_dias | `90` | BAJO — valor por defecto documentado en contrato | Mantener como default explícito |
| H8 | `adapters/user_input_loader.py` | 211 | meses_contrato fallback | `24` | MEDIO — solo en path entry_data | Raise si falta |
| H9 | `adapters/user_input_loader.py` | 212 | margen fallback | `0.18` | MEDIO — solo en path entry_data | Raise si falta |

---

## 2. Silent Defaults (`float(x or 0)` y similares)

### adapters/entry_data_adapter.py (~18 instancias)
Todas las instancias de `float(x or 0)` donde un valor null/missing se convierte silenciosamente a 0:

| Campo | Impacto |
|-------|---------|
| opex_fijo, tarifa_unitaria, pct_escalamiento, costo_escalamiento | Costos B/C silenciosamente 0 si no se proveen |
| volumen_mensual, cantidad, valor_unitario | Cero volumen silencioso |
| pct_dedicacion, costo_unitario, meses_amortizacion | Staff/dispositivos silenciosamente ignorados |

**Acción FASE 2:** Reemplazar con validación explícita en InputNormalizer. `None` debe ser el valor para "no provisto", y el normalizer decide si es 0.0 (permitido) o error (requerido).

### adapters/user_input_loader.py
| Línea | Campo | Default | Impacto |
|-------|-------|---------|---------|
| 200-201 | `contingencia_comercial.valor` | `0.0` | Legítimo default (no hay contingencia comercial por defecto) |
| 196-197 | `componente_humano/tecnologico` | `"IPC"` | Legítimo default documentado en Excel |
| 322 | `com_cont` | `0.0` | Legítimo default |
| 323 | `markup` | `0.0` | Legítimo default |
| 324 | `descuento` | `0.0` | Legítimo default |

---

## 3. Defaults Legítimos (documentados, mantener)

Estos defaults son intencionales y documentados en el contrato de dominio:

| Campo | Default | Justificación |
|-------|---------|---------------|
| `com_cont` | 0.0 | No hay contingencia comercial por defecto |
| `markup` | 0.0 | Sin markup por defecto |
| `descuento` | 0.0 | Sin descuento por defecto |
| `periodo_pago_dias` | 90 | Estándar BPO Colombia |
| `activa_financiacion` | True | Por defecto se financia |
| `componente_indexacion_*` | "IPC" | Excel V2-5 default |
| `comision_pct` | 0.0 | Sin comisión por defecto |
| `pct_fijo` | 1.0 | 100% fijo por defecto |
| `modelo_cobro` | "Fijo FTE" | Modelo más común |
| `incluye_examenes` | True | Por defecto incluye |
| `incluye_crucero` | True | Por defecto incluye |
| `dias_cap_inicial` | 10 | Estándar operativo |
| `dias_cap_rotacion` | 10 | Estándar operativo |

---

## 4. Calculators — Constants from Parametrization vs Hardcoded

### calculators/riesgo.py (15 hardcodes)
| Constante | Valor | Fuente actual | Debería ser |
|-----------|-------|---------------|-------------|
| `smmlv` | 1,423,500 | Hardcode L88 | `parametrization.get_riesgo_config()` (**ya migrado a storage en Fase 9**) |
| `umbral_aprobacion_smmlv` | 1000 | Hardcode L89 | `riesgo_config` storage |
| `pesos_categorias` | 0.4/0.6 | Hardcode L92 | `riesgo_config` storage |
| `clasificacion_score` | 2.5/1.5 | Hardcode L92 | `riesgo_config` storage |
| Todos los umbrales (L94-101) | Varios | Hardcode | **YA MIGRADOS** a `storage/parametrization/business_rules/2026-01.json` |

**Estado:** El RiesgoCalculator ya recibe `riesgo_config` como parámetro en `__init__()`. Los hardcodes solo aparecen como `_DEFAULT_RIESGO_CONFIG` fallback cuando no se pasa config. Este fallback se usa solo en tests legacy.

### config/business_rules/operaciones.yaml
Constantes operativas correctamente externalizadas:
- `horas_semanales: 42`, `semanas_al_mes: 4.33`, `breaks_diarios_min: 30`
- `formacion_min: 20`, `deslogueos_min: 5`, `coaching_min: 5`, `pausa_activa_min: 5`
- `dias_habiles_semana: 5`, `margen_minimo: 0.15`

**Estado:** OK. Correctamente externalizado vía `BusinessRulesConfig` singleton.

---

## 5. Pipeline: Origen de Cada Campo en PricingRequest

### PanelDeControl
| Campo | Origen | Ruta |
|-------|--------|------|
| cliente | entry_data | `datos_operativos.cliente` o `panel_de_control.cliente` |
| tipo_cliente | entry_data | `datos_operativos.tipo_cliente` o `panel_de_control.tipo_cliente` |
| linea_negocio | entry_data | `datos_operativos.servicio` o `panel_de_control.linea_negocio` |
| ciudad | entry_data **o HARDCODE "Bogota"** | **H2/H3 — FIX NEEDED** |
| fecha_inicio | entry_data **o HARDCODE "2026-01-01"** | **H6 — FIX NEEDED** |
| meses_contrato | entry_data **o HARDCODE 24** | **H8 — FIX NEEDED** |
| margen | entry_data **o HARDCODE 0.18** | **H9 — FIX NEEDED** |
| tasa_ica | entry_data override → parametrización `OP-ICA(ciudad)` | OK (patrón correcto) |
| tasa_gmf | entry_data override → parametrización `OP-Config` | OK |
| tasa_mensual_financ | entry_data override → parametrización `OP-Poliza` | OK |
| pct_rotacion | entry_data override → parametrización `HR-rotacion(linea)` | OK |
| pct_ausentismo | entry_data override → parametrización `HR-ausentismo(linea)` | OK |

### PerfilCadenaA
| Campo | Origen | Notas |
|-------|--------|-------|
| salario_base | entry_data override → parametrización `HR-Nomina(rol)` | OK |
| salario_cargado | Calculado por `NominaCargadaService.calcular()` | OK |
| rol | entry_data | Requerido |
| fte | entry_data | Requerido |
| Support staff | Auto-generado en `context_builder._construir_soporte()` desde `HR-reglas_staff` + `HR-ratios` | OK |

---

## 6. Resumen de Acciones FASE 1

### Hardcodes a ELIMINAR (convertir en raises):
1. **H1** — `_anio_inicio()` fallback 2026 → `raise ValueError("fecha_inicio inválida")`
2. **H2/H3** — ciudad "Bogota" → campo requerido, raise si falta
3. **H6** — fecha "2026-01-01" → campo requerido, raise si falta
4. **H8** — meses_contrato 24 → campo requerido en path entry_data
5. **H9** — margen 0.18 → campo requerido en path entry_data

### Hardcodes a DOCUMENTAR (mantener como defaults explícitos):
1. **H4** — salario_base 1423000 → default del SMMLV en derivación automática
2. **H5** — precio_unitario 50.0 → default para canales B auto-derivados
3. **H7** — periodo_pago_dias 90 → estándar BPO Colombia documentado

### Silent defaults a MIGRAR (FASE 2):
1. 18+ instancias de `float(x or 0)` en entry_data_adapter.py → InputNormalizer
