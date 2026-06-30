# Lineage

## Propósito

`modules/lineage` modela la procedencia de valores y eventos: de dónde salió
un dato, qué proceso lo produjo y qué evidencia lo respalda.

## Responsabilidades

- Mantener el dominio de lineage.
- Armar trazas usadas por auditoría.
- Proveer infraestructura de consulta y ensamblaje de procedencia.
- Separar evidencia de cálculo.

## Qué no hace este módulo

- No ejecuta fórmulas.
- No construye contratos de pantalla.
- No administra parametrización activa.
- No persiste resultados de simulación como owner principal.

## Estructura interna

```text
lineage/
├── application/
├── domain/
└── infrastructure/
```

## Endpoints expuestos

Este módulo no publica una superficie HTTP principal propia en OpenAPI. Sus
componentes se consumen desde auditoría y flujos internos.

## Entradas y salidas principales

- Entrada: nodos, eventos o identificadores de ejecución.
- Salida: trazas de procedencia y evidencia estructurada.

## Dependencias relevantes

- Dominio interno de lineage.
- Infraestructura de lectura de eventos.
- `modules/audit` como consumidor principal.

## Contratos públicos

Lineage es una capa de evidencia. No debe modificar ni recalcular valores.

## Reglas de negocio y fuentes de cálculo

No contiene reglas de cálculo. Describe relaciones entre datos ya producidos.

## Pruebas relacionadas

- Pruebas de auditoría y lineage cuando existan.

## Consideraciones de mantenimiento

- Mantener separación entre evidencia y cálculo.
- Evitar dependencias hacia visiones de pantalla.
