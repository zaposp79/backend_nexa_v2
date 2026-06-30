# Visión Imprimible: contrato público V2-8

## Alcance

`GET /api/v1/simulation/{simulation_id}/results` y
`GET /api/v1/simulation/{simulation_id}/results/vision-imprimible` exponen el
mismo contrato público:

```json
{
  "success": true,
  "data": {
    "vision_imprimible": {
      "ficha_deal": {},
      "economics": {},
      "analisis_grafico": {},
      "comparativo_escenarios": {},
      "control_aprobacion": {},
      "contingencias_ajustes": []
    }
  }
}
```

El documento persistido conserva los cálculos completos para auditoría,
snapshots y endpoints especializados. La proyección HTTP elimina los bloques
técnicos que la hoja `Visión Imprimible` no consume.

## Deuda conocida

La parametrización canónica vigente expone el margen mínimo requerido, pero no
un máximo canónico del margen objetivo. Por eso
`contingencias_ajustes[margen_objetivo].maximo` se retorna como `null`. No se
debe completar con un valor supuesto ni derivado de otra regla sin actualizar
primero la fuente canónica y recertificar la paridad con Excel.

La sección visual de responsables pertenece al flujo del frontend y no forma
parte del resultado calculado ni del contrato público del backend.

## Estado de paridad

Este cambio certifica la forma del contrato, no la paridad numérica con Excel.
Las diferencias de valores existentes entre backend y `Visión Imprimible` deben
resolverse y probarse por separado antes de declarar certificación V2-8.
