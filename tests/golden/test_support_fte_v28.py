"""
tests/golden/test_support_fte_v28.py
====================================
SUPPORT FTE — cargos_adicionales contract field (V2-8).

EXCEL ANCHOR ('Condiciones Cadena A', V2-8):
  E26 = 12          ("FTEs cargos adicionales", escenario SAC Actual)
  F26 = None (= 0)  (escenario WhatsApp Actual)
  G26 = 7.384615... (escenario Crecimiento inhouse)
  Fórmula de FTE de soporte regular (F95/G95):
    FTE_rol = IF(activo, (col9 + col26 + col30 + col34) / col_ratio [× Panel!C20 si rotación], 0)
            = (fte_agentes + cargos_adicionales) / ratio
  Supervisor (ratio = 20):
    SAC          E95 = 9.5  ← LITERAL/override manual (la fórmula daría (130+12)/20 = 7.1)
    WhatsApp     F95 = 2.5  = 50/20
    Crecimiento  G95 = 4.3692 = (80+7.384615)/20

DECISIÓN APROBADA (docs/refactor/contract_design_cargos_adicionales_v28.md):
  - El contrato acepta el detalle `cargo/salario_base/ratio` y el escalar legacy.
  - Override manual per-rol (E95 = 9.5): IMPLEMENTADO vía `fte_soporte_overrides` (opt-in, default vacío).

Estos tests validan:
  1. Default vacío preserva la fórmula legacy (fte/ratio) — sin cargos ni override.
  2. El FTE de soporte regular usa (fte + cargos_adicionales)/ratio (sin override).
  3. Los valores V2-8 del request llegan al builder (PerfilCadenaAInput → PerfilCadenaA).
  4. cargos_adicionales NO se suma al payroll de agentes (perfil base fte intacto = sin doble conteo).
  5. CTS-001 mejora materialmente (E95 + CAPEX aplicados; residual honesto sin cancelación).
  6. E95 = 9.5 (override opt-in) lleva Supervisor SAC a 9.5; al retirarlo → 7.1 (fórmula).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT))

REQUEST_PATH = REPO_ROOT / "backend_nexa" / "request" / "request.json"

# Excel V2-8 anchors
EXCEL_CTS_CADENA_A = 6_224.575126115379
RATIO_SUPERVISOR = 20.0
# Excel cargos_adicionales por escenario (CCA!E26/F26/G26)
CARGOS_SAC = 12.0
CARGOS_WHATSAPP = 0.0
CARGOS_CRECIMIENTO = 7.384615384615385

# CTS-001 baseline ANTES del fix (post DIAS_CAPACITACION, commit e296c77): delta = -128.432769 COP/tx.
CTS_DELTA_PRE_FIX = -128.432769


def _build_context(payload_mutator=None):
    """Construye el contexto (solicitud) con el v28 deal provider y request.json."""
    import backend_nexa  # noqa: F401 — registers nexa_engine alias
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from backend_nexa.tests.refactor._v28_deal_provider import build_v28_deal_provider

    prov = build_v28_deal_provider()
    payload = json.loads(REQUEST_PATH.read_text())
    if payload_mutator is not None:
        payload_mutator(payload)
    user_input = UserInputLoader().cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder(provider=prov).construir(user_input)
    return user_input, solicitud, prov


def _supervisor_fte(solicitud) -> float:
    """Suma el FTE de los perfiles de soporte 'Supervisor' a través de los 3 bloques."""
    return sum(
        p.fte for p in solicitud.perfiles_cadena_a
        if "upervisor" in p.nombre and getattr(p, "es_soporte", False)
    )


@pytest.mark.golden
def test_cargos_adicionales_reaches_input_dto() -> None:
    """(3) El detalle de recurso humano se reduce al FTE usado por el motor."""
    user_input, _, _ = _build_context()
    by_name = {p.nombre: p for p in user_input.cadena_a.perfiles}
    assert by_name["Escenario SAC Actual"].cargos_adicionales == pytest.approx(CARGOS_SAC)
    assert by_name["Escenario WhatsApp Actual"].cargos_adicionales == pytest.approx(CARGOS_WHATSAPP)
    assert by_name["Crecimiento inhouse"].cargos_adicionales == pytest.approx(CARGOS_CRECIMIENTO)


@pytest.mark.golden
def test_cargos_adicionales_contract_accepts_list_and_legacy_scalar() -> None:
    """El contrato acepta la lista del frontend sin romper requests escalares anteriores."""
    from nexa_engine.modules.shared.contracts.api_v1.request.cadena_a import PerfilCadenaAV1

    detail = PerfilCadenaAV1.model_validate({
        "cargos_adicionales": [{
            "cargo": "Validador",
            "salario_base": 1_750_905,
            "ratio": 12,
        }]
    })
    legacy = PerfilCadenaAV1.model_validate({"cargos_adicionales": 7.384615384615385})

    assert detail.cargos_adicionales[0].ratio == pytest.approx(CARGOS_SAC)
    assert detail.cargos_adicionales[0].cargo == "Validador"
    assert legacy.cargos_adicionales == pytest.approx(CARGOS_CRECIMIENTO)


@pytest.mark.golden
def test_detalles_recursos_humanos_override_salary_and_commission() -> None:
    """Los valores editables reemplazan HR y los duplicados de roles_operativos."""
    def edit_detail(payload):
        detail = payload["condiciones_cadena_a"]["detalles_recursos_humanos"][0]
        detail["salario_base"] = 1_000_000
        detail["comisiones"] = 250_000

    _, solicitud, _ = _build_context(payload_mutator=edit_detail)
    directores = [
        p for p in solicitud.perfiles_cadena_a
        if p.nombre.lower() == "soporte — director de cuentas"
    ]

    assert len(directores) == 3
    assert all(p.salario_base == pytest.approx(1_000_000) for p in directores)
    assert all(p.comision_pct == pytest.approx(0.25) for p in directores)


@pytest.mark.golden
def test_detalles_recursos_humanos_matches_excel_catalog() -> None:
    """Agente Básico 1 es fila técnica y no se agrega al catálogo editable del Excel."""
    user_input, _, _ = _build_context()
    cargos = {item.cargo for item in user_input.cadena_a.detalles_recursos_humanos}

    assert "Director de cuentas" in cargos
    assert "Agente Básico 1" not in cargos


@pytest.mark.golden
def test_support_fte_uses_fte_plus_cargos_adicionales() -> None:
    """(2) FTE de soporte regular = (fte + cargos_adicionales)/ratio. Supervisor por bloque.

    Se retira el override E95 (fte_soporte_overrides) en el mutator para verificar el
    numerador puro (fte + cargos)/ratio en los 3 escenarios.
    """
    def drop_override(payload):
        for p in payload["condiciones_cadena_a"]["perfiles"]:
            p.pop("fte_soporte_overrides", None)
    _, solicitud, _ = _build_context(payload_mutator=drop_override)
    sup = sorted(
        (p.fte for p in solicitud.perfiles_cadena_a
         if "upervisor" in p.nombre and getattr(p, "es_soporte", False)),
        reverse=True,
    )
    # 3 bloques: SAC (130+12)/20=7.1, Crecimiento (80+7.3846)/20=4.3692, WhatsApp 50/20=2.5
    assert len(sup) == 3
    assert sup[0] == pytest.approx((130 + CARGOS_SAC) / RATIO_SUPERVISOR)          # 7.10
    assert sup[1] == pytest.approx((80 + CARGOS_CRECIMIENTO) / RATIO_SUPERVISOR)   # 4.3692
    assert sup[2] == pytest.approx((50 + CARGOS_WHATSAPP) / RATIO_SUPERVISOR)      # 2.50 (cargos=0)
    total = _supervisor_fte(solicitud)
    assert total == pytest.approx(13.96923076923077, abs=1e-6)


@pytest.mark.golden
def test_cargos_adicionales_default_preserves_legacy() -> None:
    """(1) Sin cargos_adicionales ni override (legacy), supervisor = fte/ratio puro (13.0)."""
    def zero_cargos(payload):
        for p in payload["condiciones_cadena_a"]["perfiles"]:
            p.pop("cargos_adicionales", None)
            p.pop("fte_soporte_overrides", None)
    _, solicitud, _ = _build_context(payload_mutator=zero_cargos)
    total = _supervisor_fte(solicitud)
    # 130/20 + 50/20 + 80/20 = 6.5 + 2.5 + 4.0 = 13.0 (comportamiento legacy exacto)
    assert total == pytest.approx(13.0, abs=1e-6)


@pytest.mark.golden
def test_cargos_adicionales_not_added_to_agent_payroll() -> None:
    """(4) cargos_adicionales NO infla el fte de agentes (sin doble conteo)."""
    _, solicitud, _ = _build_context()
    base = {
        p.nombre: p for p in solicitud.perfiles_cadena_a
        if not getattr(p, "es_soporte", False)
    }
    # Los perfiles base conservan su fte de agentes original (130/50/80), NO 142/50/87.4.
    assert base["Escenario SAC Actual"].fte == pytest.approx(130.0)
    assert base["Escenario WhatsApp Actual"].fte == pytest.approx(50.0)
    assert base["Crecimiento inhouse"].fte == pytest.approx(80.0)
    # El campo está disponible en el perfil base pero separado del fte de agentes.
    assert base["Escenario SAC Actual"].cargos_adicionales == pytest.approx(CARGOS_SAC)


@pytest.mark.golden
def test_cts_001_improves_materially_with_cargos_adicionales() -> None:
    """
    (5) CTS-001 mejora materialmente vs baseline pre-fix.

    Con E95 (override Supervisor SAC=9.5) y la corrección de amortización CAPEX (C47 EXACT),
    el residual queda en ~-27.5 COP/tx (0.44%), HONESTO (sin cancelación payroll⊕CAPEX). El
    residual restante = brecha aditiva salario_fijo/variable (Excel suma comisión cruda D62
    sobre el cargado) + costos_fijos menor. Ver doc de evidencia.
    """
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

    _, solicitud, prov = _build_context()
    resultado = NexaPricingEngine(parametrizacion=prov).calcular(solicitud)
    cts = resultado.cost_to_serve.cts_cadena_a
    delta = cts - EXCEL_CTS_CADENA_A

    # Mejora material: el delta debe acercarse al menos +40 COP/tx respecto al baseline pre-fix.
    assert delta > CTS_DELTA_PRE_FIX + 40.0, (
        f"CTS-001 no mejoró lo esperado: delta={delta:.4f} "
        f"(pre-fix {CTS_DELTA_PRE_FIX:.4f}, esperado > {CTS_DELTA_PRE_FIX + 40.0:.4f})"
    )
    # Y NO debe sobre-corregir (doble conteo) → delta no debe volverse positivo > +20.
    assert delta < 20.0, (
        f"CTS-001 sobre-corregido (posible doble conteo): delta={delta:.4f} COP/tx"
    )


@pytest.mark.golden
def test_per_channel_fte_override_whatsapp_director_de_performance() -> None:
    """
    Fix A: Director de Performance WhatsApp=1.0 override (Excel CCA!G78).

    fte_soporte_overrides accepts {role: {channel: fte}} per-channel format.
    WhatsApp perfil must use 1.0 for Director de Performance;
    other canales (Voz 1, Voz 2) must NOT be affected by this override.
    """
    _, solicitud, _ = _build_context()
    # Collect Director de Performance FTE per canal (support perfiles)
    director_perfs = [
        p for p in solicitud.perfiles_cadena_a
        if "director de performance" in p.nombre.lower() and getattr(p, "es_soporte", False)
    ]
    assert len(director_perfs) == 3, (
        f"Expected 3 Director de Performance soporte perfiles (one per canal), got {len(director_perfs)}"
    )
    by_canal = {p.canal.lower(): p for p in director_perfs}
    # WhatsApp canal: must use override=1.0 (Excel CCA!G78 literal)
    wa = by_canal.get("whatsapp")
    assert wa is not None, "Missing Director de Performance WhatsApp soporte perfil"
    assert wa.fte == pytest.approx(1.0, abs=1e-9), (
        f"Director de Performance WhatsApp FTE should be 1.0 (CCA!G78), got {wa.fte}"
    )
    # Other canales: must use formula fte_base_soporte/ratio (NOT the WhatsApp override)
    for canal, perfil in by_canal.items():
        if canal == "whatsapp":
            continue
        # Formula FTE: fte_base_soporte / ratio_director_performance (1200 Agentes)
        # The override MUST NOT apply to non-WhatsApp canales
        assert perfil.fte != pytest.approx(1.0, abs=1e-6), (
            f"Director de Performance override should NOT apply to canal={canal}, "
            f"but got fte={perfil.fte} (= 1.0, which would indicate wrong propagation)"
        )


@pytest.mark.golden
def test_roles_excluidos_deal_wired_from_roles_operativos() -> None:
    """
    Fix B: roles_operativos[].incluye_en_deal=False exclusions (Excel CCA!C79/C80/C87).

    JCR, AFAC, GTR have incluye_en_deal=False in request.json.
    They must NOT appear in soporte perfiles (excluded from support FTE calculation).
    """
    _, solicitud, _ = _build_context()
    soporte_nombres = {p.nombre.lower() for p in solicitud.perfiles_cadena_a if getattr(p, "es_soporte", False)}

    # Roles that must be excluded (incluye_en_deal=False in request.json)
    excluded_labels = [
        "jefe comercial regional",
        "analista profesional afac",
        "gtr",
    ]
    for label in excluded_labels:
        matching = [n for n in soporte_nombres if label in n]
        assert not matching, (
            f"Role '{label}' (incluye_en_deal=False) should be excluded from soporte but found: {matching}"
        )


@pytest.mark.golden
def test_roles_incluidos_deal_remain_in_soporte() -> None:
    """
    Fix B complement: roles with incluye_en_deal=True remain in support FTE.

    Director de cuentas, Supervisor, Jefe de Operación must still appear.
    """
    _, solicitud, _ = _build_context()
    soporte_nombres = {p.nombre.lower() for p in solicitud.perfiles_cadena_a if getattr(p, "es_soporte", False)}

    expected_present = [
        "director de cuentas",
        "supervisor",
        "jefe de operacion",  # normalized (accent stripped internally)
    ]
    for label in expected_present:
        matching = [n for n in soporte_nombres if label in n]
        assert matching, (
            f"Role '{label}' (incluye_en_deal=True) should remain in soporte but not found."
        )


@pytest.mark.golden
def test_e95_supervisor_override_applied() -> None:
    """
    (6) E95 = 9.5 (override manual SAC Supervisor) SE implementa vía `fte_soporte_overrides`.

    EXCEL V2-8 'Condiciones Cadena A'!E95 = 9.5 (literal manual; la fórmula daría (130+12)/20 = 7.1).
    El override es opt-in por rol/escenario: presente en request.json para SAC → Supervisor = 9.5;
    al retirarlo → 7.1 (fórmula con cargos_adicionales). Default vacío = legacy.
    """
    _, solicitud, _ = _build_context()
    sup_sac = max(
        p.fte for p in solicitud.perfiles_cadena_a
        if "upervisor" in p.nombre and getattr(p, "es_soporte", False)
    )
    # Backend SAC supervisor = 9.5 (override Excel CCA!E95 aplicado vía request).
    assert sup_sac == pytest.approx(9.5)

    # Opt-in: al retirar el override, la fórmula da 7.1 = (130+12)/20.
    def drop_override(payload):
        for p in payload["condiciones_cadena_a"]["perfiles"]:
            p.pop("fte_soporte_overrides", None)
    _, solicitud_sin, _ = _build_context(payload_mutator=drop_override)
    sup_sac_sin = max(
        p.fte for p in solicitud_sin.perfiles_cadena_a
        if "upervisor" in p.nombre and getattr(p, "es_soporte", False)
    )
    assert sup_sac_sin == pytest.approx((130 + CARGOS_SAC) / RATIO_SUPERVISOR)  # 7.10
