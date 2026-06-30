# Skill: nexa-excel-migration

## When to use

Comparar versiones del Excel de referencia (ej. V2-7 → V2-8), analizar cambios en fórmulas, estructuras de entrada, hojas de visión, parámetros HR/GN/OP, o generar reportes técnicos de impacto para el backend.

**Riesgo esperado: medio** — solo análisis; la implementación posterior (via `nexa-backend-context` o `business-rules-agent`) es donde aumenta el riesgo.

## When not to use

- Cambios de código sin análisis previo del Excel (usa `nexa-backend-context`).
- Validación de golden tests sin cambios en el Excel fuente (usa `nexa-golden-validation`).
- Tareas de infraestructura o seguridad.

## Context to read first

1. `CLAUDE.md` — sección "Política de migración Excel V2-7 → V2-8".
2. `docs/refactor/excel_v28/findings.csv` — estado inter-sesión de gaps documentados.
3. `docs/refactor/excel_v28/parity_report.md` — resumen ejecutivo de la migración en curso.
4. Hoja específica del Excel afectada (solo la hoja relevante, no todo el archivo).
5. Calculador o módulo del backend correspondiente a la hoja analizada.

**No leer por defecto:** todo el Excel, todas las hojas, toda la suite de tests, VALIDATION.md histórico.

## Operating rules

1. **Clasificar hojas antes de analizar:**
   - **Hojas de entrada** (`Panel General`, `Cadenas A/B/C`): representan datos enviados desde el frontend. Cambios aquí pueden afectar contratos Pydantic (`PanelDeControl`, `CondicionesCadena*`).
   - **Hojas intermedias**: cálculos internos que mapean a calculadores del pipeline (capas 2–10).
   - **Hojas de visión** (`Vision Imprimible`, `Vision CTS`, `Vision Tarifas`, `P&G`): muestran resultados calculados. Cambios aquí afectan DTOs de salida o render.
2. Un cambio de fórmula **no implica automáticamente** un cambio de contrato de entrada/salida. Analizar impacto antes de proponer cambios.
3. Citar hoja + celda/rango para cada fórmula analizada:
   ```python
   # Excel V2-8 · 'Nomina'!K167 · fórmula: =B45*factor_billing*(1+tasa_mensual_financ)
   ```
4. Para cada gap identificado, clasificar:
   - `DELTA_NUMÉRICO`: diferencia de valor numérico entre versiones.
   - `NUEVA_FÓRMULA`: lógica que no existía en V2-7.
   - `CAMBIO_CONTRATO`: input/output con nueva estructura.
   - `PARÁMETRO_HR_GN_OP`: cambio en parametrización de negocio.
5. Documentar gaps en `findings.csv` antes de implementar cambios.
6. Separar análisis (esta skill) de implementación (`nexa-backend-context` o `business-rules-agent`).

## Forbidden actions

- Asumir que un cambio de fórmula Excel implica romper contratos existentes sin análisis.
- Modificar fixtures V2-7 existentes — crear fixtures V2-8 nuevos.
- Regenerar baselines durante el análisis.
- Implementar cambios de negocio sin evidencia citada del Excel (hoja + celda).
- Ignorar `findings.csv` — es la fuente inter-sesión del estado de la migración.

## Validation

```bash
# Comparar backend actual vs Excel V2-8
cd backend_nexa && make validate-excel

# Ejecutar tests parity V2-8 específicos
PYTHONPATH=$(pwd) pytest backend_nexa/tests/parity/v28/ -v --tb=short

# Verificar que no hay regresiones en V2-7
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m parity -v
```

## Final response format

```md
## Resultado
## Evidencia
## Riesgo
## Validación
## Siguiente paso
```

Incluir siempre tabla de gaps con columnas: `Hoja | Celda | Tipo | Impacto backend | Estado`.

---

**Ejemplo de invocación:**

```
Usando la skill nexa-excel-migration:
Analizar cambios entre V2-7 y V2-8 en la hoja 'Nomina'.
Identificar fórmulas modificadas, nuevos parámetros y posibles cambios de contrato.
Leer findings.csv antes de clasificar.
No implementar cambios — solo generar reporte de impacto.
Citar hoja + celda para cada hallazgo.
```
