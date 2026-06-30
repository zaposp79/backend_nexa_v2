# W10 — Versioning Strategy

**Status**: FROZEN (WAVE 14 — 2026-05-28)
**Owner**: NEXA engine core
**Scope**: every version stamp emitted by the pricing engine.

---

## 1. Why a separate registry

The engine emits several independent version stamps in every
simulation:

| Stamp                     | Lifetime              | Source of truth                                       |
|---------------------------|-----------------------|-------------------------------------------------------|
| `engine_version`          | code semver           | constant in `VersionRegistry` (literal `engine-v2`)   |
| `api_version`             | api contract          | constant `api-v1`                                     |
| `parametrization_version` | active parametrization| `storage/parametrization/<module>/versions.json`      |
| `excel_version`           | excel workbook        | `storage/parametrization/<param_v>/manifest.json`     |
| `formula_set`             | formula collection    | derived from `parametrization_version`                |
| `baseline_version`        | certified outputs     | `storage/baselines/<v>/manifest.json` (optional)      |
| `parametrization_hashes`  | content fingerprint   | SHA-256 of each active json (hr/gn/op/business_rules) |

Pre-W14 every stamp was a literal scattered across emitters, DTOs, and
the audit use case. WAVE 14 consolidates them in a single immutable
container (`VersionMetadata`) produced by a single reader
(`VersionRegistry`).

---

## 2. `VersionRegistry`

Module: `application/versioning/version_registry.py`.

```python
class VersionRegistry:
    ENGINE_VERSION = "engine-v2"
    API_VERSION    = "api-v1"

    def get_current(baseline_version=None) -> VersionMetadata
    def get_active_parametrization_version() -> str
    def compute_parametrization_hashes() -> dict[str, str]
    def invalidate_cache() -> None
```

* `get_current` is cached after the first call; cheap enough to call
  inside an endpoint handler (<5 ms).
* `compute_parametrization_hashes` is idempotent: same bytes → same
  hash, deterministic and reusable as a content fingerprint.
* `invalidate_cache` is called when a parametrization upload swaps the
  active version.

Construction takes an optional `storage_root` so unit tests can isolate
the registry from production storage.

---

## 3. `VersionMetadata`

```python
@dataclass(frozen=True)
class VersionMetadata:
    excel_version: str
    parametrization_version: str
    engine_version: str
    api_version: str
    formula_set: str
    baseline_version: Optional[str]
    parametrization_hashes: dict[str, str]
```

Frozen — passed by value into emitters and serialized into the lineage
JSON, audit response, and `SimulationResultV1` envelope.

---

## 4. Lineage integration

* `JsonLineageEmitter(simulation_id, version_metadata=...)` stamps each
  `LineageNode` with `engine_version` / `formula_set` from the metadata
  and includes the full snapshot in `LineageGraph.version_metadata`.
* `LineageGraph.parametrization_hashes` is populated from the metadata
  (was an empty dict pre-W14).
* `LineageNode` fields renamed: `engine_version_placeholder` →
  `engine_version`, `formula_set_placeholder` → `formula_set`.
  Backwards-compat aliases preserve read access for old code, and
  `LineageNode.from_dict` accepts both legacy and new keys.

---

## 5. Audit integration

`AuditSimulationUseCase._resolve_versions` resolves the three fields
returned in `AuditResponseV1` (engine_version, formula_set,
parametrization_hashes) by precedence:

1. **Best**: graph's persisted `version_metadata` (post-W14 snapshots).
2. **Good**: first node's `engine_version` / `formula_set` plus the
   graph's `parametrization_hashes`.
3. **Fallback**: `VersionRegistry.get_current()` (legacy snapshot —
   logged as a warning).

---

## 6. simulation_id mapping

`NexaPricingEngine._generate_simulation_id` produces the canonical id:

1. `solicitud.metadata.simulation_id` (caller-provided).
2. `solicitud.panel.simulation_id` (compat alias).
3. UUID4 hex.

The same id is:

* used by the lineage emitter,
* stored as `storage/lineage/<sim_id>/lineage.json`,
* attached to `PricingResult.simulation_id`, and
* returned by `/calculate` so `/audit/simulation/<id>` resolves.

---

## 7. SimulationResult contract

`SimulationResultV1` (api-v1) was extended additively with:

* `formula_set` (string)
* `parametrization_hashes` (dict[str,str])

OpenAPI + JSONSchema regenerated; existing consumers ignore the new
fields (additive, `extra="forbid"` enforced on top-level only).

---

## 8. Test surface

26 tests under `tests/versioning/`:

| File                                              | Tests | Coverage                                    |
|---------------------------------------------------|-------|---------------------------------------------|
| `test_version_registry.py`                        |     8 | registry semantics, hash idempotence        |
| `test_simulation_id_mapping.py`                   |     6 | id propagation across calculate / audit     |
| `test_lineage_includes_real_versions.py`          |     5 | emitter stamps real versions, new keys      |
| `test_audit_response_includes_versions.py`        |     4 | audit response real hashes + version stamps |
| `test_backward_compat_legacy_lineage.py`          |     3 | legacy snapshots still loadable             |

Critical paridad suite remained at 141 / 141.
