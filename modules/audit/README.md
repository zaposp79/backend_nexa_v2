# Audit

## Propósito

`modules/audit` expone evidencia, trazabilidad y envelopes de auditoría para
simulaciones y procesos relacionados.

## Responsabilidades

- Registrar rutas de auditoría.
- Construir envelopes de evidencia.
- Coordinar helpers de lineage usados por auditoría.
- Describir cómo se produjo un resultado sin recalcularlo.

## Qué no hace este módulo

- No ejecuta fórmulas.
- No orquesta pricing.
- No construye contratos de pantalla.
- No administra providers de persistencia.

## Estructura interna

```text
audit/
├── api/
├── registry.py
├── trace.py
└── writer.py
```

## Endpoints expuestos

Las rutas de auditoría se registran en `api/audit_router.py`. Actualmente se
montan fuera del esquema público de OpenAPI cuando corresponde.

## Entradas y salidas principales

- Entrada: identificadores de simulación, nodos o contexto auditable.
- Salida: evidencia, trazas y envelopes de auditoría.

## Dependencias relevantes

- `modules/lineage` para información de procedencia.
- `modules/shared/responses.py` para formatos de respuesta.

## Contratos públicos

Auditoría debe describir evidencia y trazas. No debe modificar resultados ni
recalcular valores de negocio.

## Reglas de negocio y fuentes de cálculo

No contiene reglas de cálculo. Se apoya en datos ya generados por módulos
propietarios.

## Pruebas relacionadas

- `tests/api/`
- Pruebas de auditoría y lineage cuando existan.

## Consideraciones de mantenimiento

- Mantener audit como capa descriptiva.
- Evitar dependencias desde audit hacia fórmulas o routers de visión.
