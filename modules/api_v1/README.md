# API v1

## Proposito

`modules/api_v1` compone los routers publicos de la version `/api/v1`.
Es la capa que decide que modulos quedan publicados en la API versionada,
pero no implementa logica de negocio.

## Responsabilidades

- Registrar los routers publicos de parametrizacion, simulacion y visiones.
- Mantener una superficie v1 limpia para Swagger/OpenAPI.
- Evitar rutas duplicadas, crudas, internas o temporales en la documentacion publica.
- Delegar cada endpoint a su modulo propietario.

## Que no hace este modulo

- No calcula precios.
- No formatea contratos de pantalla.
- No lee ni escribe resultados.
- No valida reglas de negocio.
- No mantiene rutas de compatibilidad heredada.

## Estructura interna

```text
api_v1/
├── __init__.py
└── router.py
```

## Endpoints expuestos

Este modulo no declara endpoints propios. Incluye routers que luego se montan
en `app.py` bajo `/api/v1`.

## Routers incluidos

| Router | Modulo propietario | Proposito |
|---|---|---|
| `parametrizacion_router` | `modules/parametrizacion` | Upload, versiones y activacion de parametrizacion HR/GN/OP. |
| `panel_router` | `modules/panel` | Parametros de Panel. |
| `chain_a_router` | `modules/cadena_a` | Parametros de Cadena A. |
| `chain_b_router` | `modules/cadena_b` | Parametros de Cadena B. |
| `chain_c_router` | `modules/cadena_c` | Parametros de Cadena C. |
| `calculate_router` | `modules/calculator` | Ejecucion de simulacion. |
| `results_router` | `modules/calculator` | Resultado imprimible y trazabilidad. |
| `vision_imprimible_router` | `modules/vision_imprimible` | Vision imprimible screen-ready. |
| `pyg_router` | `modules/vision_pyg` | Vision PYG screen-ready. |
| `vision_tarifas_router` | `modules/vision_tarifas` | Modelo de cobro y preview de tarifas. |
| `cost_to_serve_router` | `modules/vision_cost_to_serve` | Vision Cost To Serve screen-ready. |
| `audit_router` | `modules/audit` | Auditoria y lineage. |
| `certification_router` | `modules/certification` | Certificados y verificacion. |

## Contratos publicos

La documentacion publica v1 se organiza alrededor de estos grupos:

- Health
- Simulations
- Parametrization
- Vision Imprimible
- Vision PYG
- Vision Cost To Serve
- Vision Tarifas

## Consideraciones de mantenimiento

- No registrar aliases antiguos para la primera version publica.
- No publicar rutas con `/internal`, `/raw` o `/debug`.
- Si un endpoint pertenece a una vision, su router debe vivir en el modulo de esa vision.
- Si una ruta nueva aparece en Swagger, debe tener `summary`, `operation_id`,
  contrato claro y modulo propietario.
