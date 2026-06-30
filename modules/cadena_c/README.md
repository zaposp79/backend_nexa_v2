# Cadena C

## Propósito

`modules/cadena_c` agrupa parámetros, reglas locales y servicios propios de
Cadena C.

## Responsabilidades

- Exponer parámetros de entrada de Cadena C.
- Mantener DTOs y modelos de la cadena.
- Concentrar reglas locales propias.
- Consultar parámetros mediante servicios del módulo.

## Qué no hace este módulo

- No implementa fórmulas del motor.
- No orquesta la simulación completa.
- No construye visiones de salida.
- No administra infraestructura de persistencia.

## Estructura interna

```text
cadena_c/
├── api/
│   └── chain_c_router.py
├── dto/
├── models/
├── services/
└── reglas.py
```

## Endpoints expuestos

| Método | Ruta | Propósito | Tag OpenAPI |
|---|---|---|---|
| GET | `/api/v1/simulation/input/chain-c/parametros` | Devuelve parámetros disponibles para Cadena C. | Simulations |

## Entradas y salidas principales

- Entrada: solicitud HTTP sin cuerpo.
- Salida: parámetros de entrada para Cadena C.

## Dependencias relevantes

- `services/parameters_query_service.py`.
- Reglas locales del módulo.

## Contratos públicos

La respuesta pública contiene datos de entrada. No debe incluir resultados
calculados ni estructuras de visión.

## Reglas de negocio y fuentes de cálculo

El cálculo principal vive en `calculator_motor`. Cadena C solo mantiene reglas
locales y datos propios de entrada.

## Pruebas relacionadas

- `tests/api/`

## Consideraciones de mantenimiento

- Evitar dependencias cruzadas con otras cadenas.
- Mantener la ruta bajo `simulation/input/chain-c`.
