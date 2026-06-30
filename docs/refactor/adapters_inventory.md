# Adapters Inventory — Excel V2-8 Parity

Inventario de adapters temporales creados al mover código a su ubicación canónica
durante la paridad V2-8.

| Path viejo | Path nuevo | TICKET_ID | Marca (MOTOR_TO_VIEW / VIEW_TO_MOTOR) | Estado |
|------------|------------|-----------|----------------------------------------|--------|
| _(ninguno)_ | — | — | — | — |

**Stage 1:** sin adapters. No se movió código (decisión "parity only, defer structural";
Stage 1 es harness + análisis de delta, no edita `modules/**`).

Los adapters se agregarán en Stage 2 únicamente si una corrección de paridad toca código
mal ubicado (política "tocás → mové con adapter; no tocás → diferí").
