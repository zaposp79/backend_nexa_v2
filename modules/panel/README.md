# Panel

## Propósito

`modules/panel` expone los parámetros de entrada usados por el panel de
simulación. Es una superficie de consulta para que frontend pueda armar el
formulario inicial.

## Responsabilidades

- Publicar parámetros del panel.
- Mantener DTOs y modelos propios del panel.
- Delegar la obtención de datos a servicios del módulo.
- Entregar datos de entrada, no resultados calculados.

## Qué no hace este módulo

- No ejecuta fórmulas.
- No persiste resultados.
- No construye visiones de salida.
- No administra parametrización activa.

## Estructura interna

```text
panel/
├── api/
│   └── panel_router.py
├── dto/
├── models/
└── services/
```

## Endpoints expuestos

| Método | Ruta | Propósito | Tag OpenAPI |
|---|---|---|---|
| GET | `/api/v1/simulation/input/panel/parametros` | Devuelve parámetros disponibles para el panel. | Simulations |

## Entradas y salidas principales

- Entrada: solicitud HTTP sin cuerpo.
- Salida: catálogo de parámetros de panel.

## Dependencias relevantes

- Servicios internos del módulo.
- Contratos compartidos de respuesta cuando aplica.

## Contratos públicos

El contrato público representa datos de entrada para simulación. No debe
contener métricas de resultado ni estructuras de visión.

## Reglas de negocio y fuentes de cálculo

Este módulo no calcula. Si un valor requiere cálculo, debe provenir de la capa
propietaria correspondiente.

## Pruebas relacionadas

- `tests/api/`

## Consideraciones de mantenimiento

- Mantener el endpoint como catálogo de entrada.
- Evitar mezclar parámetros del panel con cadenas o visiones.
