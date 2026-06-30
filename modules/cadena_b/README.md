# Cadena B

## Propósito

`modules/cadena_b` agrupa los parámetros, reglas locales y servicios propios
de Cadena B.

## Responsabilidades

- Exponer parámetros de entrada de Cadena B.
- Mantener DTOs y modelos de la cadena.
- Concentrar reglas locales de Cadena B cuando no pertenecen al motor.
- Mantener una frontera clara frente a Cadena A y Cadena C.

## Qué no hace este módulo

- No implementa fórmulas del motor.
- No orquesta la simulación completa.
- No construye visiones de salida.
- No administra infraestructura de persistencia.

## Estructura interna

```text
cadena_b/
├── api/
│   └── chain_b_router.py
├── dto/
├── models/
├── services/
└── reglas.py
```

## Endpoints expuestos

| Método | Ruta | Propósito | Tag OpenAPI |
|---|---|---|---|
| GET | `/api/v1/simulation/input/chain-b/parametros` | Devuelve parámetros disponibles para Cadena B. | Simulations |

## Entradas y salidas principales

- Entrada: solicitud HTTP sin cuerpo.
- Salida: parámetros de entrada para Cadena B.

## Dependencias relevantes

- Servicios internos de Cadena B.
- Reglas locales declaradas en el módulo.

## Contratos públicos

La respuesta pública contiene datos de entrada. No debe incluir resultados
calculados ni estructuras de visión.

## Reglas de negocio y fuentes de cálculo

El cálculo principal vive en `calculator_motor`. Cadena B solo mantiene reglas
locales y datos propios de entrada.

## Pruebas relacionadas

- `tests/api/`

## Consideraciones de mantenimiento

- Evitar dependencias cruzadas con otras cadenas.
- Mantener la ruta bajo `simulation/input/chain-b`.
