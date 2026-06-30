# Remove Legacy Vision PyG Route

## Scope

Removed the public route `/api/v1/simulation/{simulation_id}/vision/pyg`.

`vision_pyg` remains part of the persisted `PricingResult` and is still available through `/api/v1/simulation/{simulation_id}/results/vision-pyg`. No PyG formulas, calculations, persistence, Vision Imprimible, Cost To Serve, or Vision Tarifas behavior changed.

## Client Usage Found

- `postman/NEXA_Simulator.postman_collection.json` contained `GET /api/v1/simulation/{simulation_id}/vision/pyg`

No frontend `ts/js/tsx` consumer was found in this repository.

## Guardrails

- Runtime router must not register `/api/v1/simulation/{simulation_id}/vision/pyg`
- OpenAPI must not publish `/api/v1/simulation/{simulation_id}/vision/pyg`
- `modules/vision_pyg/` remains absent

## Validation

- `tests/refactor/` passed after route removal
- `tests/golden/` passed with no drift
- Baseline snapshot tests `v1` and `cadena_c_v1` passed
