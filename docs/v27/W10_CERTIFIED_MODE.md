# W10 — Certified Mode (delivered by WAVE 15)

Status: **DELIVERED** (WAVE 15 / FASE 10).

A "certified" simulation is one where the engine pipeline ran against a
fully pinned configuration **and** produced output within the certified
parity envelope. WAVE 15 ships:

* `/calculate?mode=certified` — strict opt-in flag.
* `ExecutionCertificate` — immutable, deterministic record of the run.
* `/certification/*` — read + verify endpoints.

## What "certified" means

A run is `certified=True` iff **all** of the following hold:

1. The engine binary is at the active version recorded in
   `VersionRegistry.ENGINE_VERSION`.
2. The active parametrization JSONs (HR / GN / OP / business_rules) hash
   to the values pinned in
   `storage/baselines/v2-7-certified/manifest.json::parametrization_hashes`.
   Hashes are computed on the **canonical** (sort_keys, no-spaces) JSON
   re-serialisation — matches `scripts/baselines/generate_baselines.py`.
3. The request does **not** carry any field flagged experimental
   (`experimental*`, `*_experimental_*`).
4. The engine ran with `with_lineage=True` (so the run is replayable).
5. If a matching baseline case is found (servicio + ≥1 of
   modalidad/modelo/cadenas), the live KPIs differ by ≤0.01% relative
   tolerance from the baseline KPIs.

If any of (1)-(5) fails, the API returns `412 Precondition Failed` with
a structured `CertificationFailure` body.

## Activation surface

| Trigger                                            | Behaviour      |
|----------------------------------------------------|----------------|
| `POST /api/v1/simulation/calculate`                | normal mode    |
| `POST /api/v1/simulation/calculate?mode=certified` | certified      |
| Body field `metadata.mode = "certified"`           | certified (alt) |

## Failure codes

| code                    | when                                                |
|-------------------------|-----------------------------------------------------|
| `HASH_MISMATCH`         | active param hash ≠ baseline manifest or expected   |
| `EXPERIMENTAL_OVERRIDE` | request contains any `experimental*` field          |
| `PARITY_FAILURE`        | matched baseline KPIs differ > 0.01% rel-tol        |
| `BASELINE_NOT_FOUND`    | reserved (today best-effort matching skips parity)  |

Each failure includes `code`, `message`, `expected`, `actual`, and a
`details` dict (e.g. the failing module name, the failing KPI, the
absolute and relative drift).

## ExecutionCertificate

```jsonc
{
  "certificate_id": "<sha256 of body, deterministic>",
  "simulation_id": "<engine sim id, links to /audit/...>",
  "issued_at": "<UTC ISO-8601>",
  "version_metadata": {
    "engine_version": "engine-v2",
    "parametrization_version": "v2-7",
    "formula_set": "formula-set-v2-7",
    "api_version": "api-v1",
    "baseline_version": "v2-7-certified",
    "parametrization_hashes": { "hr": "...", "gn": "...", "op": "...", "business_rules": "..." }
  },
  "request_hash": "<sha256 of canonicalised raw user_input>",
  "result_hash":  "<sha256 of KPIs only — sim_id excluded>",
  "lineage_hash": "<sha256 of lineage graph>",
  "baseline_matched": "bancamia_sac_inbound_fte",
  "validation_results": {
    "parametrization_hashes": "matched",
    "experimental_overrides": "none",
    "lineage": "captured",
    "baseline_match": "bancamia_sac_inbound_fte",
    "parity": "passed"
  }
}
```

`certificate_id` is a SHA-256 over the certificate body **excluding
`issued_at` and `certificate_id` itself**. Two structurally identical
runs (same content) produce the same `certificate_id`.

## Storage layout

```
storage/
  certificates/
    <certificate_id>.json
    index.json                    # simulation_id → certificate_id
```

Files are JSON, written with `sort_keys=True` for deterministic bytes.

## Lineage stamp

When a certificate is issued, the corresponding lineage file is updated
in place with a `certificate_id` key, so audit consumers can cross-link
`/audit/simulation/{id}` ⇄ `/certification/certificate/{cert_id}`.

## Endpoints

| Method | Path                                              | Purpose                          |
|--------|---------------------------------------------------|----------------------------------|
| POST   | `/api/v1/simulation/calculate?mode=certified`     | Run certified + emit cert        |
| GET    | `/api/v1/certification/certificates?limit=N`      | List recent certs (desc)         |
| GET    | `/api/v1/certification/certificate/{cert_id}`     | Load one cert                    |
| POST   | `/api/v1/certification/verify/{cert_id}`          | Re-validate vs live param hashes |

## Test coverage

`tests/certification/mode_w15/` — 36 tests across:

* `test_certified_mode_basic.py` (6) — happy-path + cert structure.
* `test_certified_hash_validation.py` (4) — HASH_MISMATCH paths.
* `test_certified_experimental_overrides.py` (3) — EXPERIMENTAL_OVERRIDE.
* `test_certified_baseline_matching.py` (4) — dimension matcher + cert determinism.
* `test_certified_parity_failure.py` (3) — PARITY_FAILURE.
* `test_certificate_repository.py` (5) — CRUD + determinism.
* `test_certificate_verify_endpoint.py` (4) — HTTP /certification.
* `test_certificate_contract.py` (4) — Pydantic DTO frozen.
* `test_certified_lineage_includes_certificate.py` (3) — lineage stamp.

## Backward compatibility

* `POST /calculate` without `mode` parameter → **identical** to W14 behaviour.
* No existing endpoint changed signature or response shape.
* `VersionRegistry.compute_parametrization_hashes()` retained (raw-byte
  hashes for lineage/audit). Certified mode uses canonical-JSON hashes,
  matching the baseline-manifest convention from
  `scripts/baselines/generate_baselines.py`.
