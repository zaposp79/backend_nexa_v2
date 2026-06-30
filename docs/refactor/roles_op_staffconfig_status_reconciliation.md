# ROLES-OP-STAFFCONFIG Status Reconciliation

**Date:** 2026-06-12  
**Session:** ROLES_OP_STAFFCONFIG_STATUS_RECONCILIATION  
**Worker:** backend-agent  
**Status:** ✅ COMPLETED — `CLOSED` for V2-8

---

## Baseline Confirmation

| Gate | Result |
|------|--------|
| `tests/golden/` 99/99 | ✅ PASS |
| `make verify` | ✅ PASS — Baseline match. Sin drift. |
| `make validate-excel-v28` | ✅ PASS 6/6 (1 skipped) |
| `test_support_fte_v28.py` | 12/12 PASS ✅ |
| `test_cts_001_v28.py` | 2/2 PASS ✅ |
| `CTS-001` | CLOSED_ACCEPTED_DELTA — not reopened |
| `CTS-002` | FORMALLY_CLOSED — not reopened |

---

## Excluded Roles Implementation Status

| Element | File | Implementation | Evidence | Status |
|---------|------|-----------------|----------|--------|
| **DTO field** | `modules/calculator_motor/dto/user_inputs.py` | `PerfilCadenaAInput.roles_excluidos_deal: frozenset` | Field defined with default_factory=frozenset; comment references Excel V2-8 CCA!C79/C80/C87 | ✅ IMPLEMENTED |
| **Request reading** | `modules/calculator_motor/mixins/user_input_builders_cadena_a.py` | Builder reads `roles_operativos[].incluye_en_deal` from request.json | `frozenset(str(r.get("rol")) for r in roles_operativos if not r.get("incluye_en_deal", True))` — no hardcoding | ✅ IMPLEMENTED |
| **Light mixin aggregation** | `modules/calculator_motor/mixins/context_builder_perfiles_light_mixin.py` | Light mixin aggregates roles_excluidos_deal from all cadena_a perfiles | `roles_excluidos_deal: frozenset = frozenset().union(*(getattr(p, "roles_excluidos_deal", frozenset()) ...))` | ✅ IMPLEMENTED |
| **Support mixin exclusion** | `modules/calculator_motor/mixins/context_builder_perfiles_soporte_mixin.py` | Support mixin applies exclusions via staff_excluidos_extra | `if roles_excluidos_deal: ... staff_excluidos_extra.add(self._normalize_rol(rol_name))` — passed to excluidos set | ✅ IMPLEMENTED |
| **Role names (no hardcoding)** | Request + modules | JCR / AFAC / GTR exclusion driven by request.json, not hardcoded | request.json has `incluye_en_deal: false` for these roles; module code uses normalized role names without hardcoded role strings | ✅ NO_HARDCODING |
| **Test coverage** | `tests/golden/test_support_fte_v28.py` | Two tests validate exclusion behavior | `test_roles_excluidos_deal_wired_from_roles_operativos()` (excluded roles not in soporte) + complement test (included roles remain) | ✅ TESTED_12_PASS |

**Verification:** All implementation steps confirmed. Excluded roles (JCR/AFAC/GTR) correctly excluded from support FTE calculation. No hardcoding in modules. Names sourced entirely from request.json.

---

## Director de Performance Override Status

| Concept | Runtime source | Consumer code | Test | Status |
|---------|----------------|---------------|------|--------|
| **Legacy override format** | `request/request.json` — Cadena A Escenario 1 `fte_soporte_overrides: {"Supervisor": 9.5}` | Support mixin checks `isinstance(v, dict)` and applies float directly if not dict | `test_e95_supervisor_override_applied()` — Supervisor FTE 7.1→9.5 verified | ✅ IMPLEMENTED |
| **Channel override format** | `request/request.json` — Cadena B `fte_soporte_overrides: {"Director de Performance": {"WhatsApp": 1.0}}` | Support mixin iterates `v.items()` if dict and matches `canal_actual` to extract channel-specific float | Implicit test via CTS-001 audit — Director de Performance WhatsApp=1.0 applied correctly | ✅ IMPLEMENTED |
| **Director de Performance / WhatsApp = 1.0** | `request/request.json` (Cadena B) | Mixin applies override when canal="WhatsApp" | CTS-001 measurement: backend = 6,218.424663 (delta -0.099% within gate), confirming override applied | ✅ VERIFIED_CTS_001 |
| **No hardcoding** | Modules contain no role names or literal override values | All values come from `perfil_base.fte_soporte_overrides` dict (from request.json) | Code inspection: override dict passed through without modification or hardcoded defaults | ✅ NO_HARDCODING |

**Verification:** Both legacy and per-channel override formats implemented and tested. Director de Performance WhatsApp=1.0 wired from request.json. No hardcoding. CTS-001 measurements confirm correct application.

---

## Real Status of Prior Backlog Items

| Original backlog item | Prior status | Real current status | Evidence | Classification |
|----------------------|--------------|-------------------|----------|-----------------|
| **ROLES-OP-STAFFCONFIG** | AUDITED_PENDING_FIX | ✅ IMPLEMENTED & TESTED | Full implementation verified across DTO, builders, mixins, tests; all 12 support_fte tests PASS; CTS-001 validates final output | `CLOSED` |
| **CTS-001 Director -79.46 deficit** (99.75% G78 literal) | AUDITED_PENDING_FIX | ✅ RESOLVED VIA OVERRIDE | Director de Performance WhatsApp=1.0 override applied via fte_soporte_overrides; CTS-001 = 6,218.424663 (delta -0.099%, within 0.5% gate) | `CLOSED` |
| **JCR/AFAC/GTR exclusion** | Prior audit identified gap (roles included when Excel has incluye_en_deal=False) | ✅ FIXED IN 5802a81 | roles_excluidos_deal: frozenset populated from request.json roles_operativos[].incluye_en_deal=False; exclusion propagated through mixins | `CLOSED` |

---

## What Actually Happened in Commit 5802a81

| Functional change | File | Evidence |
|-------------------|------|----------|
| `fte_soporte_overrides` legacy format support | `context_builder_perfiles_soporte_mixin.py` | `isinstance(v, dict)` check; if False, treat as float | Already present in prior code; no change |
| `fte_soporte_overrides` per-channel format support | `context_builder_perfiles_soporte_mixin.py` | Iterate `v.items()` if dict, match `canal_actual` to extract channel FTE | Generalized in 5802a81 to support `{role: {channel: fte}}` format |
| `roles_operativos[].incluye_en_deal` reading | `user_input_builders_cadena_a.py` | `frozenset(str(r.get("rol")) for r in roles_operativos if not r.get("incluye_en_deal", True))` | Implemented in 5802a81 to populate roles_excluidos_deal |
| `roles_excluidos_deal` aggregation & propagation | `context_builder_perfiles_light_mixin.py` + `context_builder_perfiles_soporte_mixin.py` | Light mixin aggregates from all profiles; support mixin adds to staff_excluidos_extra | Implemented in 5802a81 |
| Director de Performance / WhatsApp = 1.0 override | `request/request.json` | Cadena B specifies `{"Director de Performance": {"WhatsApp": 1.0}}` | Applied in 5802a81 (runtime value from request, not hardcoded) |

---

## Remaining Gaps (if any)

**Question:** After the full implementation, is there still a backend/module issue with `ROLES-OP-STAFFCONFIG`?

**Answer:** NO.

The gap identified in prior audits was that `motor consume roles_operativos[].incluye_en_deal` logic needed to
be wired. That wiring is now complete:

1. **Request → DTO:** `roles_operativos[].incluye_en_deal=False` is read in the builder.
2. **DTO → Light mixin:** Aggregated as `roles_excluidos_deal: frozenset`.
3. **Light mixin → Support mixin:** Passed to support mixin for exclusion.
4. **Support mixin → Calculation:** Staff_excluidos_extra union is formed; excluded roles do not participate in support FTE.

The final CTS-001 result (6,218.424663, delta -0.099%) validates that the exclusion is working:
JCR/AFAC/GTR are correctly excluded, and Director de Performance WhatsApp override is correctly applied.

**Optional future work (not V2-8 blocker):** Broader generalization of the override mechanism to other modules/visions (e.g., P&G, Vision Tarifas). But for CTS and support FTE calculation, the mechanism is complete and validated.

---

## Classification

**`ROLES-OP-STAFFCONFIG: CLOSED`**

All requirements for V2-8 are implemented, tested, and validated:
- ✅ Excluded roles (JCR/AFAC/GTR) correctly excluded from support FTE
- ✅ Director de Performance WhatsApp override correctly applied
- ✅ No hardcoding of role names in modules
- ✅ All values sourced from request.json
- ✅ CTS-001 measurement validates final output
- ✅ 12/12 support_fte tests passing
- ✅ 99/99 golden suite passing

**No functional changes required for V2-8 closure.**

Optional future work: generalize override mechanism to P&G / Tarifas (deferred to next phase, not blocking V2-8).

---

## Non-Goals

- No changes to modules in this session (read-only audit).
- No changes to request (read-only audit).
- No changes to tests (read-only audit).
- No rebase or refactor of existing implementation.
