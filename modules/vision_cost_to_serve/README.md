# Visión Cost To Serve

## Propósito

`modules/vision_cost_to_serve` construye el contrato público de pantalla para
Cost To Serve a partir de datos ya calculados y persistidos.

## Responsabilidades

- Exponer la visión CTS screen-ready.
- Convertir fuentes técnicas persistidas en `summary_cards`, `sections` y
  `charts`.
- Incluir una sección de riesgo cuando `evaluacion_riesgo` esté persistida.
- Reportar campos faltantes en `metadata.missing_fields`.
- Omitir campos vacíos sin perder valores reales como `0`, `0.0` o `false`.

## Qué no hace este módulo

- No ejecuta fórmulas de Cost To Serve.
- No lee Excel en runtime.
- No accede directamente a parametrización almacenada.
- No expone buckets técnicos como raíz de la respuesta pública.

## Estructura interna

```text
vision_cost_to_serve/
├── api/
│   ├── response_models.py
│   └── router.py
├── dto/
├── helpers/
│   ├── charts_mapper.py
│   └── screen_mapper.py
├── models/
└── services/
```

## Endpoints expuestos

| Método | Ruta | Propósito | Tag OpenAPI | Contrato |
|---|---|---|---|---|
| GET | `/api/v1/simulation/{simulation_id}/results/cost-to-serve` | Devuelve el contrato público CTS. | Vision Cost To Serve | `ApiResponse[CostToServeScreenDataV1]` |

## Entradas y salidas principales

Entrada principal:

- Resultado persistido de simulación.
- Bloques de CTS calculados previamente.

Salida principal:

- `version`
- `simulation_id`
- `header`
- `summary_cards`
- `sections`
- `charts`
- `metadata`

## Dependencias relevantes

- `ResultsRepository` para cargar el resultado persistido.
- `helpers/screen_mapper.py` para armar el contrato de pantalla.
- `helpers/charts_mapper.py` para gráficos existentes.
- `modules/shared/responses.py` para el envelope público.

## Contratos públicos

La respuesta pública no debe exponer como raíz:

- `cost_to_serve`
- `vision_por_servicio`
- `vision_por_canal`
- `detalle_por_canal`
- `estructura_equipo`

Esas fuentes se convierten en secciones de pantalla.

## Reglas de negocio y fuentes de cálculo

Los cálculos vienen del resultado persistido. Este módulo solo transforma datos
para frontend.

## Pruebas relacionadas

- `tests/vision_cost_to_serve/`
- `tests/api/test_cost_to_serve_endpoint.py`
- `tests/api/test_openapi_public_contract.py`

## Consideraciones de mantenimiento

- Mantener las fuentes técnicas dentro del mapper, no en la respuesta raíz.
- Si aparece una fuente nueva, agregarla como sección o metadata explícita.
- No introducir dependencias a Excel, provider activo o motor de cálculo en la
  superficie pública.
