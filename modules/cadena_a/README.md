# Cadena A

## Propósito

`modules/cadena_a` agrupa la superficie de entrada y composición propia de
Cadena A, especialmente estructuras de personal, nómina y parámetros asociados.

## Responsabilidades

- Exponer parámetros de entrada de Cadena A.
- Mantener DTOs, modelos y servicios propios de la cadena.
- Componer información de staffing y nómina cuando el flujo lo requiere.
- Mantener el límite funcional de Cadena A separado de las demás cadenas.

## Qué no hace este módulo

- No orquesta la simulación completa.
- No implementa fórmulas globales del motor.
- No construye contratos de visión.
- No administra infraestructura de persistencia.

## Estructura interna

```text
cadena_a/
├── api/
│   └── chain_a_router.py
├── dto/
├── models/
├── services/
└── use_cases/
```

## Endpoints expuestos

| Método | Ruta | Propósito | Tag OpenAPI |
|---|---|---|---|
| GET | `/api/v1/simulation/input/chain-a/parametros` | Devuelve parámetros disponibles para Cadena A. | Simulations |

## Entradas y salidas principales

- Entrada: solicitud HTTP sin cuerpo.
- Salida: parámetros de entrada para Cadena A.

## Dependencias relevantes

- Servicios internos de Cadena A.
- Casos de uso de staffing y nómina.

## Contratos públicos

La respuesta pública contiene datos de entrada para configurar la simulación.
No debe contener resultados, fórmulas ni contratos de pantalla.

## Reglas de negocio y fuentes de cálculo

Las fórmulas de cálculo pertenecen al motor. Cadena A mantiene composición y
datos propios de su dominio.

## Pruebas relacionadas

- `tests/api/`
- Pruebas de servicios y casos de uso de Cadena A cuando existan.

## Consideraciones de mantenimiento

- No mezclar lógica de Cadena A con Cadena B o Cadena C.
- Mantener las rutas bajo `simulation/input/chain-a`.
