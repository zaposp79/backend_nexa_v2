# Vision Tarifas

## Proposito

`modules/vision_tarifas` construye el contrato publico de pantalla para
`modelo-cobro` a partir del resultado persistido de simulacion. Tambien ofrece
un preview stateless para cambios de presentacion del modelo de cobro.

## Responsabilidades

- Exponer el contrato publico de `modelo-cobro`.
- Mapear `vision_tarifas.escenarios_detalle` a estructuras consumibles por frontend.
- Mantener `selected_view_id` como seleccion inicial, sin usarlo para esconder los demas escenarios cuando el contrato requiere la lista completa.
- Devolver `resumen_resultado_escenario` con escenarios 1 a 5 y `Total`.
- Devolver `modelo_cobro` con detalle de cadenas, tarifas, reglas y totales.
- Exponer `desglose_producto_opex`, donde `producto` si aplica como dimension.
- Usar `canal` para escenarios, no `producto`.
- Aplicar overrides de preview sin persistir.

## Que no hace este modulo

- No ejecuta formulas de negocio.
- No lee Excel en runtime.
- No lee `storage/parametrization` directamente.
- No invoca el motor para recalcular costos base desde el mapper.
- No hardcodea valores esperados del Excel.
- No usa defaults para ocultar fuentes monetarias faltantes.
- No expone payloads crudos de `vision_tarifas` en la API publica.

## Estructura interna

```text
vision_tarifas/
├── api/
│   ├── router.py
│   └── schemas.py
├── dto/
├── helpers/
│   └── modelo_cobro_mapper.py
├── models/
├── services/
│   └── modelo_cobro_recalculation_service.py
└── use_cases/
```

## Endpoints expuestos

| Metodo | Ruta | Proposito | Tag OpenAPI | Contrato |
|---|---|---|---|---|
| GET | `/api/v1/simulation/{simulation_id}/results/vision-tarifas/modelo-cobro` | Devuelve el contrato publico simplificado de modelo de cobro. | Vision Tarifas | `ApiResponse[ModeloCobroPublicData]` |
| POST | `/api/v1/simulation/{simulation_id}/results/vision-tarifas/modelo-cobro/recalculate` | Devuelve un preview stateless con overrides permitidos. | Vision Tarifas | `ApiResponse[ModeloCobroPublicData]` |

## Entradas y salidas principales

Entrada principal:

- Resultado persistido de simulacion obtenido con `ResultsRepository`.
- Bloque `vision_tarifas.escenarios_detalle`.
- Bloque `vision_tarifas.desglose_producto_opex`.

Salida principal:

- `success`
- `data.cliente`
- `data.servicio`
- `data.ciudad`
- `data.selected_view_id`
- `data.resumen_resultado_escenario`
- `data.modelo_cobro`
- `data.desglose_producto_opex`
- `error`
- `meta`

## Flujo de datos

```text
GET modelo-cobro
  -> carga resultado persistido de simulacion
  -> extrae vision_tarifas
  -> aplica modelo_cobro_mapper
  -> devuelve ApiResponse(success/data/error/meta)
```

```text
POST modelo-cobro/recalculate
  -> carga resultado persistido de simulacion
  -> construye contrato base con el mapper
  -> aplica overrides permitidos en memoria
  -> devuelve preview sin persistir
```

## Reglas de negocio y fuentes de calculo

- Los valores monetarios deben provenir de fuentes persistidas equivalentes a la hoja `Vision Tarifas_Modelo_Cobro`.
- `escenarios_detalle[].meta` es la fuente canonica para datos del escenario.
- `escenarios_detalle[].tarifas` es la fuente canonica para tarifas.
- `escenarios_detalle[].cadena_a/b/c` es la fuente canonica para cadenas.
- `escenarios_detalle[].reglas_business` es la fuente canonica para reglas.
- `canales[]` solo puede usarse como respaldo de etiquetas de display cuando falten en `meta`.

## Contratos publicos

- `selected_view_id` indica la seleccion por defecto.
- `selected_view_id` no filtra necesariamente `modelo_cobro`.
- `resumen_resultado_escenario` incluye escenarios y `Total`.
- `modelo_cobro` contiene el detalle de modelo de cobro.
- El POST no persiste overrides.
- El POST no recalcula el motor completo.
- Cambios de costos base deben ir a una recalculacion completa en otra fase.

## Pruebas relacionadas

- `tests/vision_tarifas/test_modelo_cobro_mapper.py`
- `tests/api/test_vision_tarifas_modelo_cobro_endpoint.py`
- `tests/api/test_vision_tarifas_modelo_cobro_recalculate_endpoint.py`
- `tests/api/test_openapi_public_contract.py`

## Consideraciones de mantenimiento

- No agregar rutas crudas o internas a Swagger.
- No mezclar `canales[]` con escenarios salvo como fallback de etiquetas.
- Si falta una fuente monetaria, no inventar el valor.
- Mantener el mapper como capa de lectura y transformacion.
