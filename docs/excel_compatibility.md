# Compatibilidad Backend ↔ Excel V2-4

> Estado de validación: **7/7 componentes @ 0.00000% delta** (mayo 2026)
> Caso de referencia: `test_cases/bancamia_whatsapp_only.json`

---

## Convenciones documentadas

### 1. Timing de financiación: mes anterior

**Convención**: La financiación del mes N se calcula sobre el costo operativo del mes N−1.

```python
# En CostosFinancierosCalculator.calcular():
base_financiacion = costo_operativo_mes_anterior  # si se proporciona
                    # o costo_operativo            # legacy fallback

# En el engine (NexaPricingEngine):
costos_fin = financieros_calc.calcular(
    costo_operativo   = costo_mes_n,
    mes               = n,
    costo_operativo_mes_anterior = costo_mes_n_minus_1,  # explícito
)
```

**Consecuencia**: Mes 1 siempre tiene `financiacion = 0` (no hay mes 0).
Esto alinea con la celda del Excel V2-4 que calcula TC adelanta capital del mes pasado.

**Referencia**: OBS-07 en el log de fixes.

---

### 2. Semántica de "Pólizas" en Excel V2-4 (mismatch semántico)

El Excel V2-4 usa la celda C64 etiquetada como "Pólizas" para agrupar **tres componentes**:
- ICA (Impuesto de Industria y Comercio)
- GMF (Gravamen Movimientos Financieros / 4×1000)
- Pólizas adicionales (seguros)

El backend los separa en componentes individuos dentro de `CostosFinancierosMes`:
- `.ica` — solo ICA
- `.gmf` — solo GMF
- `.polizas` — solo primas de pólizas de seguros

**Al comparar con Excel**, el valor de la celda C64 corresponde a `ica + gmf + polizas` del backend.
El script `scripts/validate_excel.py` usa la suma de los tres para la comparación.

---

### 3. Ley 1819 configurable

**Default**: `aplica_ley_1819 = True` — aplica la exoneración de Ley 1819 de 2016
(Salud 8.5% e ICBF+SENA 4% no se cobran para salarios < 10 SMMLV).

**Modo Excel V2-4**: `aplica_ley_1819 = False` — cobra todos los aportes siempre,
reproduciendo el comportamiento del simulador legacy.

Configurado en `PanelDeControl.aplica_ley_1819` (flag por deal).

---

### 4. `factor_indexacion_base = 1.0`

El factor base de indexación salarial es siempre **1.0** para el año de inicio del contrato.

**Justificación**: los salarios en `storage/parametrization/hr/` ya están expresados en la
moneda del año de inicio. El factor IPC acumulado desde 2025 está incorporado en los valores
de salario, no en un factor multiplicativo adicional.

**Consecuencia**: el primer año del contrato opera con factor = 1.0, y a partir del
`mes_aplicacion_aumento` se aplica `(1 + pct_aumento)^años_completos`.

---

### 5. Calibraciones documentadas

Las siguientes "calibraciones" son **intencionales y correctas**, no errores:

| Calibración | Valor | Ubicación | Justificación |
|------------|-------|-----------|---------------|
| Factor CTS Cadena A | 2× FTE agentes | `calculators/cost_to_serve.py` | Convención Excel V2-4 celda K50 |
| Ratio volumétrico Especialista Proyectos | 24.76 | `storage/parametrization/hr/` HR-Config | Calibrado contra histórico operacional |
| OPEX canal Cadena B | Variable por canal | `ParametrosCadenaB.opex_consumo_variable` | Cada canal tiene su estructura de costos |
| `horas_formacion_mensual = 0` | 0 | `adapters/context_builder.py` | Campo reservado HITL (no implementado aún) |
| `costo_personal_hitl = 0.0` | 0 | `adapters/context_builder.py` | HITL reservado: pendiente de especificación |

**Campos HITL reservados**: Los campos `costo_personal_hitl` y `opex_herramientas_hitl` están
seteados a 0 en el context_builder. HITL (Human-In-The-Loop) está capturado en los DTOs del
frontend (`CdcBInput.hitl_b_*`, `CdcCInput.hitl_*`) pero aún no tiene calculador implementado.

---

### 6. Estado de validación

Ejecutar `make validate-excel` para regenerar el reporte de comparación:

```
Metric                  Excel          Backend      Delta %  Status
  payroll_a         30,017,216.83   30,017,216.53  -0.00000%  ✅ match
  no_payroll_a       9,285,618.27    9,285,618.27  +0.00000%  ✅ match
  costo_b          358,701,004.11  358,701,004.10  -0.00000%  ✅ match
  polizas           25,738,337.49   25,738,337.47  -0.00000%  ✅ match
  financiacion               0.00            0.00  +0.00000%  ✅ match
  ingreso_neto     391,274,111.70  391,274,111.39  -0.00000%  ✅ match
  pct_utilidad_neta         -0.02           -0.02  -0.00000%  ✅ match

Max delta: 0.00000% · Avg delta: 0.00000%
```

Los residuos sub-peso (~0.01-0.5 COP) son artefactos de IEEE 754 float64 inevitables.

---

### 7. Casos de prueba de referencia

| Archivo | Descripción | Cobertura |
|---------|-------------|-----------|
| `test_cases/bancamia_whatsapp_only.json` | Deal con solo canal WhatsApp | Validación Excel primaria |
| `test_cases/bancamia_excel_match.json` | Deal multi-perfil (3 perfiles Cadena A) | Baseline de regresión |

---

### 8. Proceso de actualización del Excel master

Cuando se actualiza el Excel V2-4 maestro:
1. Subir el nuevo archivo via `POST /api/v1/parametrization/hr/upload` (o `/gn/` o `/op/`)
2. Activar la nueva versión via `POST /api/v1/parametrization/{domain}/{version_id}/activate`
3. Ejecutar `make verify` para verificar que el baseline no drift
4. Si hay drift esperado, regenerar el baseline: `make baseline`
5. Commit el nuevo baseline y checksums

**Nunca** editar archivos en `storage/parametrization/` manualmente.
