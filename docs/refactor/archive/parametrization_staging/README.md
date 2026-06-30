# Staging — Parametrizaciones no activadas

## Propósito
Almacenar versiones físicas cargadas vía API que no están activas y no deben contaminar el storage funcional.

## Versiones almacenadas

| Archivo | Módulo | Motivo |
|---------|--------|--------|
| `hr_40799552-3477-4a8a-b295-5c3208733ee2.json` | HR | Versión física no activa en versions.json (version_id no registrado como activo) |
| `op_8e651172-ba4a-44c4-9afe-38aec3281dd9.json` | OP | Versión física no activa — duplicado de 14da70ab (OP_productiva_2026-06-10.xlsx, misma fuente) |
| `gn_000e36a9-f6d4-42c7-89f1-af32450b80a9.json` | GN | Versión física no activa — duplicado de 60031c65 (GN_productiva_2026-06-10.xlsx, misma fuente) |

## Versiones activas (no movidas)

| Dominio | UUID activo | Archivo en storage |
|---------|-------------|-------------------|
| HR | 6506b1fa-b0d2-4bf9-9e87-d27f3f4fc73b | storage/parametrization/hr/6506b1fa-b0d2-4bf9-9e87-d27f3f4fc73b.json |
| OP | 14da70ab-b199-4587-8793-34b8a872ab66 | storage/parametrization/op/14da70ab-b199-4587-8793-34b8a872ab66.json |
| GN | 60031c65-c3db-45cf-ae4f-a24658322aa1 | storage/parametrization/gn/60031c65-c3db-45cf-ae4f-a24658322aa1.json |

## Regla
No activar individualmente. Cualquier activación requiere decisión explícita y validación coordinada de goldens/snapshots.

## Fecha
2026-06-10
