# Visión Imprimible

## Propósito

`modules/vision_imprimible` construye la versión pública imprimible del
resultado de simulación. Su responsabilidad es presentar datos ya calculados en
un contrato estable para frontend y documentos.

## Responsabilidades

- Exponer la visión imprimible screen-ready.
- Construir secciones de ficha, configuración comercial, análisis, gráficos,
  comparativos, aprobaciones y contingencias cuando existan datos.
- Normalizar la salida pública con modelos de respuesta.
- Omitir campos vacíos sin perder ceros o booleanos reales.

## Qué no hace este módulo

- No ejecuta fórmulas de negocio.
- No lee Excel en runtime.
- No administra storage ni parametrización.
- No expone payloads internos del motor como contrato público.

## Estructura interna

```text
vision_imprimible/
├── api/
│   ├── public_mapper.py
│   ├── response_models.py
│   └── router.py
├── builders/
├── helpers/
└── models/
```

## Endpoints expuestos

| Método | Ruta | Propósito | Tag OpenAPI | Contrato |
|---|---|---|---|---|
| GET | `/api/v1/simulation/{simulation_id}/results/vision-imprimible` | Devuelve la visión imprimible pública. | Vision Imprimible | `ApiResponse[VisionImprimibleDataV1]` |

## Entradas y salidas principales

Entrada principal:

- Resultado persistido de simulación.

Salida principal:

- Datos generales de la simulación.
- Secciones imprimibles disponibles.
- Metadatos de fuente y campos omitidos.

## Dependencias relevantes

- `ResultsRepository` para cargar el resultado persistido.
- `api/public_mapper.py` para el contrato público.
- `builders/` y `helpers/` para composición de secciones.
- `modules/shared/responses.py` para el envelope público.

## Contratos públicos

La visión imprimible debe ser una proyección de lectura. Los nombres de campos
públicos deben mantenerse estables porque los consume frontend y la generación
de documentos.

## Reglas de negocio y fuentes de cálculo

Las reglas y valores calculados se producen antes de llegar a este módulo. La
visión imprimible solo alinea, etiqueta y limpia los datos persistidos.

## Pruebas relacionadas

- `tests/api/test_vision_imprimible_endpoint.py`
- `tests/api/test_openapi_public_contract.py`

## Consideraciones de mantenimiento

- No duplicar lógica que ya vive en otras visiones.
- No agregar dependencias directas a Excel ni provider activo.
- Mantener las secciones opcionales con pruning de vacíos.
