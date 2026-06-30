# Vision PYG

## Proposito

`modules/vision_pyg` construye el contrato publico de pantalla para PYG a
partir de `vision_pyg` persistido. El contrato actual es period-centric:
organiza la informacion por periodo y agrega totales.

## Responsabilidades

- Exponer la Vision PYG screen-ready.
- Convertir filas internas de PYG en `periods[]`.
- Construir `totales`.
- Ocultar campos tecnicos como `formula`, `excel_row`, `seccion`, `tipo`,
  `signo` y `detalle`.
- Preservar ceros reales.
- Omitir valores nulos o vacios en la salida publica.

## Que no hace este modulo

- No ejecuta formulas de negocio.
- No lee Excel en runtime.
- No lee `storage/parametrization` directamente.
- No expone el payload interno de `vision_pyg` en OpenAPI publico.

## Estructura interna

```text
vision_pyg/
├── api/
│   ├── response_models.py
│   └── vision_router.py
├── builders/
├── helpers/
│   └── screen_mapper.py
├── models/
└── services/
```

## Endpoints expuestos

| Metodo | Ruta | Proposito | Tag OpenAPI | Contrato |
|---|---|---|---|---|
| GET | `/api/v1/simulation/{simulation_id}/results/vision-pyg` | Devuelve el contrato period-centric de PYG. | Vision PYG | `ApiResponse[VisionPygDataV1]` |

## Entradas y salidas principales

Entrada principal:

- Resultado persistido de simulacion.
- Bloque `vision_pyg`.

Salida principal:

- `version`
- `simulation_id`
- `header`
- `periods[]`
- `totales`
- `metadata`

## Flujo de datos

```text
GET vision-pyg
  -> carga resultado persistido de simulacion
  -> extrae vision_pyg
  -> aplica helpers/screen_mapper.py
  -> devuelve ApiResponse con contrato period-centric
```

## Contratos publicos

- `periods[]` contiene los valores por periodo.
- `totales` contiene acumulados.
- `metadata.source` debe indicar `persisted_pricing_result`.
- La respuesta publica no debe exponer formulas ni filas de Excel.

## Relacion con calculator_motor

`calculator_motor` produce los valores ya calculados. `vision_pyg` solo los
transforma para pantalla.

## Pruebas relacionadas

- `tests/vision_pyg/`
- `tests/api/test_vision_pyg_endpoint.py`
- `tests/api/test_openapi_public_contract.py`

## Consideraciones de mantenimiento

- No recrear endpoints `internal`, `screen` o aliases duplicados.
- Mantener el tag publico como `Vision PYG`.
- El mapper debe seguir siendo una proyeccion de datos persistidos.
