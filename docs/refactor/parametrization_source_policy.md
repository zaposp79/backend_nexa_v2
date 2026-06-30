# Política de fuentes de parametrización

## Propósito

Este documento formaliza el estado actual de las fuentes de parametrización
para evitar que se mezcle parametrización runtime, snapshot certificado y datos
frozen. No resuelve el `HASH_MISMATCH`; lo deja visible hasta una decisión
explícita de revert controlado o recertificación versionada.

## Snapshot certificado

`storage/baselines/v2-7-certified/**` representa el baseline certificado WAVE 6.
Su `manifest.json`, checksums y casos congelados no deben mutarse sin una
recertificación versionada.

El manifest certificado compara hashes contra `storage/parametrization/v2-7/*`.
Actualmente hay drift conocido en `business_rules` y `hr`; actualizar el
manifest o los hashes para hacer pasar tests sin evidencia de recertificación
está prohibido.

## Parametrización runtime activa

El runtime activo no tiene una única forma homogénea para todos los dominios:

- HR/GN/OP usan actualmente `storage/parametrization/v2-7/{hr,gn,op}.json`
  porque sus `versions.json` apuntan a `v2-7` como versión activa.
- `business_rules` usa `storage/parametrization/business_rules/v2-7.json`
  mediante `BusinessRulesRepository` y `DocumentStore`.

Este estado describe el sistema actual; no debe leerse como política ideal
definitiva. En particular, no se debe mezclar automáticamente el runtime activo
con el snapshot certificado para resolver hashes.

## Frozen data

`storage/parametrization/frozen/{version}.json` es la fuente de datos frozen
real consumida por `FrozenParametrizationRepository`.

Los datos frozen son inmutables y semánticamente distintos del CRUD/versionado
runtime de parametrización. No deben migrarse ni reserializarse sin una fase
dedicada y validación de paridad.

## Estado mixto y deuda conocida

`storage/parametrization/v2-7/*` tiene semántica ambigua en el estado actual:

- WAVE 6 lo trata como fuente de hashes del snapshot certificado.
- HR/GN/OP runtime lo usan como parametrización activa.
- FROZEN-1 registró esos archivos como datos frozen con hashes ya drifted.

Esta ambigüedad es deuda explícita. No autoriza actualizar manifest, hashes,
snapshots ni tests para ocultar el `HASH_MISMATCH`.

## Prohibiciones

- No actualizar `storage/baselines/v2-7-certified/manifest.json` sin
  recertificación versionada.
- No actualizar hashes para hacer pasar tests.
- No ocultar el `HASH_MISMATCH`.
- No modificar `storage/parametrization/v2-7/*` sin decisión explícita.
- No mezclar runtime activo con snapshot certificado.

## Rutas permitidas para resolver la deuda

La decisión pendiente debe escoger una de estas rutas:

1. Revert controlado de `business_rules` y `hr` al estado del baseline WAVE 6.
2. Recertificación versionada del baseline si el drift es funcionalmente válido.

Hasta escoger una ruta, los tests de baseline/certified que fallan por
`HASH_MISMATCH` deben seguir actuando como señal bloqueante.
