# FASE DB — Report (Infrastructure batch)

Branch: `refactor/modular-pure`. This batch delivers the transversal `db/`
persistence infrastructure **only**. No domain consumer was migrated, so the
gate is byte-identical to baseline.

## Validation

```
Gate:                     56 failed / 1263 passed / 46 skipped   (failing node ids IDENTICAL to baseline)
Oracle (parity):          406 passed / Δ = 0
Collection errors:        0
JSON flow:                unchanged (no consumer touched)
New db tests:             23 passed (+12 Cosmos cases skipped — no credentials)
Imports of concrete providers from modules/api:  0
Direct storage/ references introduced:            0
```

Baseline was re-established at the start of this work (a prior
`cost_to_serve → vision_cost_to_serve` rename had left 4 stale test imports →
4 collection errors; fixed in commit `fix(tests): update stale cost_to_serve imports`).

## Infrastructure created

```
db/
├── __init__.py
├── config.py
├── exceptions.py
├── factory.py
├── README.md
├── constants/provider_constants.py
├── models/collection_config.py
├── ports/document_store.py
├── providers/json_document_store.py
├── providers/cosmos_document_store.py
└── helpers/atomic_json_writer.py
tests/db/
├── conftest.py
├── contract/test_document_store_contract.py   # shared JSON+Cosmos suite
└── unit/test_config_and_factory.py
```

## Persistence inventory (FASE 1)

| Path under `storage/` | Data type | Current consumer | Backend target | Action |
| --- | --- | --- | --- | --- |
| `parametrization/{domain}/*.json` + `versions.json` | parametrización versionada | `JsonParametrizationRepository` (+ existing Cosmos repo, FASE P.8) | json (cosmos prepared) | migrate later — already has its own port |
| `parametrization/frozen/v*.json` | snapshots inmutables | `FrozenParametrizationRepository` | json | migrate later |
| `simulation_results/{id}.json` | resultados de simulación | `modules/calculator/persistence/results_repository.py` | json → DocumentStore | **batch 1 candidate** |
| `snapshots/{id}/snapshot.json,summary.json` | snapshots | `modules/shared/persistence/snapshots_repository.py` | json → DocumentStore | **batch 2 candidate** |
| `certificates/{id}.json` + `index.json` | certificación | `modules/shared/certification/certificate_repository.py` | json → DocumentStore | batch 4 |
| `lineage/{id}/lineage.json` | auditoría/linaje | `modules/shared/infrastructure/lineage/snapshot_repository.py` | json → DocumentStore | batch 3 |
| `baselines/v2-7-certified/**` | baselines certificados | `certified_calculation.py` (read-only) | **NOT migrated** | keep — fixtures/certified artifacts |
| `simulation_inputs/**` | fixtures de entrada | inputs | **NOT migrated** | keep |

## Cosmos topology (FASE 7) — POSTPONE until per-collection evidence exists

| Capability | Logical collection | `id` | Partition key | Container | State |
| --- | --- | --- | --- | --- | --- |
| Parametrization | `parametrization_versions` | version_id | `/domain` | `parametrization` | READY (already implemented in FASE P.8 repo) |
| Simulation results | `simulation_results` | simulation_id | `simulation_id` | TBD | POSTPONE_WITH_REASON — container/throughput not defined |
| Snapshots | `audit_snapshots` | simulation_id | `simulation_id` | TBD | POSTPONE_WITH_REASON |
| Certificates | `certificates` | certificate_id | TBD | TBD | POSTPONE_WITH_REASON — index.json semantics need a query design |
| Lineage | `lineage` | simulation_id | `simulation_id` | TBD | POSTPONE_WITH_REASON |

No containers, partition keys or throughput were invented. The JSON backend is
unaffected by these POSTPONE states.

## Consumer migration plan (FASE 11 — NOT executed in this batch)

Batches, each followed by full gate + Oracle + node-id diff before proceeding:

1. `simulation_results` → `SimulationResultsRepository(store: DocumentStore)`
2. `snapshots`
3. `lineage`
4. `certificates`
5. parametrización (already has a port; adapt to the shared `DocumentStore` or
   keep its dedicated port — decide during that batch)

Rule honoured: never migrate all modules in a single batch; revert the batch on
any real regression.

## Postponed

| Item | Reason |
| --- | --- |
| Consumer migration (FASE 11) | Risk-isolated; must be validated batch-by-batch against the gate |
| Data migration script (FASE 12) | No consumer migrated yet → nothing to move |
| `storage/README.md` DEPRECATED markers | No path migrated yet; marking now would be inaccurate |
| Cosmos activation (FASE 7) | Per-collection container/partition topology undocumented |

## Technical debt / notes

| Item | Risk | Recommendation |
| --- | --- | --- |
| Two persistence abstractions coexist (existing `ParametrizationRepositoryPort` + new `DocumentStore`) | Low | During parametrization batch, decide whether to converge onto `DocumentStore` |
| `env.example` still carries unrelated Flask placeholders | Cosmetic | Clean up in a docs pass |
| JSON `query` loads the whole collection before filtering | Low (small collections) | Acceptable for JSON; Cosmos pushes filters server-side |
