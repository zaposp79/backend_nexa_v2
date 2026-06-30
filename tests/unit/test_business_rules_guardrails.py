"""
BUSINESS_RULES_FINAL_GUARDRAILS
================================
Tests permanentes que protegen los invariantes establecidos en FIX_1/FIX_2B/FIX_3/FIX_4A.

Propósito: actuar como ratchet estructural. Si cualquier invariante se rompe
(p.ej. alguien reintroduce smmlv en el canonical YAML, agrega una política
huérfana, o elimina un umbral Excel), estos tests fallan inmediatamente y
con mensaje claro.

NO duplican la lógica de cálculo — solo verifican *estructura* y *contratos*.

Invariantes protegidos:
  G-01  riesgo.yaml no contiene smmlv en constantes_regulatorias.
  G-02  riesgo.yaml no contiene aprobaciones_umbrales.
  G-03  politicas_comerciales.yaml no contiene porcentaje_acumulado.
  G-04  politicas_comerciales.yaml no contiene descuento_volumen.
  G-05  politicas_comerciales.yaml contiene exactamente las 5 políticas activas canónicas.
  G-06  Cada política en politicas_comerciales mapea a un campo real de PanelDeControl.
  G-07  RiesgoCalculator no puede instanciarse sin smmlv — TypeError.
  G-08  RiesgoCalculator lanza ValueError si smmlv <= 0.
  G-09  engine._calcular_pipeline llama get_smmlv() e inyecta smmlv= a RiesgoCalculator.
  G-10  _aprobaciones_requeridas no referencia business_rules ni smmlv.
  G-11  Umbrales Excel VI 100M/200M/1B son constantes de módulo (no leen YAML).
  G-12  _aprobaciones_requeridas no acepta parámetros de firmantes ni aprobaciones_umbrales.
  G-13  panel_dto.ReglasNegocio no contiene descuento_volumen ni porcentaje_acumulado.
  G-14  engine_helpers._calcular_reglas_negocio lanza ValueError para política sin Panel.
  G-15  Ningún módulo runtime referencia storage/parametrization/v2-7/business_rules.json.

Canonical sources:
  - riesgo.yaml (via load_business_rules)
  - politicas_comerciales.yaml (via load_business_rules)

Fuente documental: docs/refactor/business_rules_source_of_truth_audit.md
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from nexa_engine.modules.shared.config.business_rules.loader import (
    load_business_rules,
)

# ---------------------------------------------------------------------------
# Rutas de referencia
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Conjunto canónico de políticas activas post-FIX_3
_POLITICAS_ACTIVAS = frozenset({
    "contingencia_operativa",
    "contingencia_comercial",
    "markup",
    "descuento",
    "imprevistos",
})

# Mapping canónico: política → atributo de PanelDeControl
_PANEL_FIELD_MAP = {
    "contingencia_operativa": "op_cont",
    "contingencia_comercial": "com_cont",
    "markup":                 "markup",
    "descuento":              "descuento",
    "imprevistos":            "imprevistos",
}


# ===========================================================================
# TAREA 1 — G-01 … G-04: canonical YAML no contiene campos prohibidos
# ===========================================================================

class TestCanonicalYamlCamposProhibidos:

    # G-01
    def test_g01_no_smmlv_en_constantes_regulatorias(self):
        """G-01: riesgo.yaml constantes_regulatorias NO tiene 'smmlv'."""
        reg = load_business_rules("riesgo").get("constantes_regulatorias", {})
        assert "smmlv" not in reg, (
            "REGRESIÓN G-01: 'smmlv' fue reintroducido en riesgo.yaml. "
            "FIX_2B lo eliminó definitivamente. La única fuente canónica es "
            "IParametrizationProvider.get_smmlv() (HR-Salarios). "
            "Eliminar el campo y NO reintroducirlo."
        )

    # G-02
    def test_g02_no_aprobaciones_umbrales_en_riesgo_config(self):
        """G-02: riesgo.yaml NO tiene 'aprobaciones_umbrales'."""
        riesgo = load_business_rules("riesgo")
        assert "aprobaciones_umbrales" not in riesgo, (
            "REGRESIÓN G-02: 'aprobaciones_umbrales' fue reintroducido en riesgo.yaml. "
            "FIX_1 lo eliminó: los umbrales viven como constantes en serializer_helpers.py "
            "(_UMBRAL_GERENCIA_FINANCIERA_COP, etc.), no en business_rules."
        )

    # G-03
    def test_g03_no_porcentaje_acumulado_en_politicas(self):
        """G-03: politicas_comerciales.yaml NO tiene 'porcentaje_acumulado'."""
        politicas = load_business_rules("politicas_comerciales").get("politicas_comerciales", [])
        nombres = {p["nombre"] for p in politicas}
        assert "porcentaje_acumulado" not in nombres, (
            "REGRESIÓN G-03: 'porcentaje_acumulado' fue reintroducido en politicas_comerciales. "
            "FIX_3 lo eliminó: era DEAD_FIELD_LEGACY sin campo en PanelDeControl. "
            "No tiene fuente real — no reintroducir."
        )

    # G-04
    def test_g04_no_descuento_volumen_en_politicas(self):
        """G-04: politicas_comerciales.yaml NO tiene 'descuento_volumen' (renombrado a 'descuento')."""
        politicas = load_business_rules("politicas_comerciales").get("politicas_comerciales", [])
        nombres = {p["nombre"] for p in politicas}
        assert "descuento_volumen" not in nombres, (
            "REGRESIÓN G-04: 'descuento_volumen' fue reintroducido en politicas_comerciales. "
            "FIX_1 lo renombró a 'descuento'. Usar 'descuento' siempre."
        )


# ===========================================================================
# TAREA 2 — G-05 … G-06: políticas comerciales canónicas
# ===========================================================================

class TestPoliticasComerciales:
    """Ratchet: politicas_comerciales contiene exactamente las 5 políticas activas."""

    @pytest.fixture(scope="class")
    def politicas(self):
        return load_business_rules("politicas_comerciales")["politicas_comerciales"]

    # G-05
    def test_g05_exactamente_5_politicas_activas(self, politicas):
        """G-05: politicas_comerciales tiene exactamente las 5 políticas canónicas."""
        nombres = {p["nombre"] for p in politicas}
        assert nombres == _POLITICAS_ACTIVAS, (
            f"REGRESIÓN G-05: politicas_comerciales difiere del conjunto canónico.\n"
            f"  Esperado: {sorted(_POLITICAS_ACTIVAS)}\n"
            f"  Actual:   {sorted(nombres)}\n"
            f"  Añadidas: {sorted(nombres - _POLITICAS_ACTIVAS)}\n"
            f"  Faltantes:{sorted(_POLITICAS_ACTIVAS - nombres)}"
        )

    # G-06
    def test_g06_cada_politica_tiene_campo_panel_mapeado(self, politicas):
        """G-06: cada política en politicas_comerciales.yaml tiene campo real en PanelDeControl."""
        from nexa_engine.modules.panel.models.panel import PanelDeControl
        panel_fields = {f.name for f in PanelDeControl.__dataclass_fields__.values()} \
            if hasattr(PanelDeControl, "__dataclass_fields__") \
            else set(PanelDeControl.__annotations__)

        for pol in politicas:
            nombre = pol["nombre"]
            campo_panel = _PANEL_FIELD_MAP.get(nombre)
            assert campo_panel is not None, (
                f"G-06: política '{nombre}' no tiene entrada en _PANEL_FIELD_MAP "
                f"(el mapa de referencia en este test). "
                f"Agregar el mapeo o eliminar la política del YAML."
            )
            assert campo_panel in panel_fields, (
                f"G-06: política '{nombre}' mapea a PanelDeControl.{campo_panel} "
                f"pero ese campo no existe en PanelDeControl. "
                f"Campos disponibles: {sorted(panel_fields)}"
            )

    def test_g06b_engine_helpers_tiene_todas_las_politicas_en_panel_fields(self):
        """G-06b: _PANEL_FIELDS en engine_helpers cubre todas las políticas canónicas."""
        from nexa_engine.modules.calculator_motor.helpers.engine_helpers import _calcular_reglas_negocio
        source = inspect.getsource(_calcular_reglas_negocio)
        for politica in _POLITICAS_ACTIVAS:
            assert f'"{politica}"' in source or f"'{politica}'" in source, (
                f"G-06b: política canónica '{politica}' no aparece en _calcular_reglas_negocio. "
                f"Verificar que _PANEL_FIELDS cubre todas las políticas activas."
            )


# ===========================================================================
# TAREA 3 — G-07 … G-09: SMMLV
# ===========================================================================

class TestSmmlvGuardrails:
    """Ratchet: SMMLV obligatorio en RiesgoCalculator, inyectado desde HR en engine."""

    # G-07
    def test_g07_riesgo_calculator_sin_smmlv_lanza_typeerror(self):
        """G-07: RiesgoCalculator() sin smmlv lanza TypeError (argumento obligatorio)."""
        from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator
        with pytest.raises(TypeError):
            RiesgoCalculator()  # type: ignore[call-arg]

    def test_g07b_riesgo_calculator_con_config_sin_smmlv_lanza_typeerror(self):
        """G-07b: RiesgoCalculator(riesgo_config) sin smmlv también lanza TypeError."""
        from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator
        with pytest.raises(TypeError):
            RiesgoCalculator({})  # type: ignore[call-arg]

    # G-08
    def test_g08_riesgo_calculator_smmlv_cero_lanza_valueerror(self):
        """G-08: smmlv=0 → ValueError (valor inválido)."""
        from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator
        with pytest.raises(ValueError, match="smmlv > 0"):
            RiesgoCalculator(smmlv=0.0)

    def test_g08b_riesgo_calculator_smmlv_negativo_lanza_valueerror(self):
        """G-08b: smmlv<0 → ValueError."""
        from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator
        with pytest.raises(ValueError, match="smmlv > 0"):
            RiesgoCalculator(smmlv=-1.0)

    # G-09
    def test_g09_engine_inyecta_get_smmlv_en_pipeline(self):
        """G-09: engine._calcular_pipeline llama get_smmlv() e inyecta smmlv= kwarg."""
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        source = inspect.getsource(NexaPricingEngine._calcular_pipeline)
        assert "get_smmlv()" in source, (
            "REGRESIÓN G-09: engine._calcular_pipeline ya no llama get_smmlv(). "
            "FIX_2 estableció que SMMLV debe inyectarse desde HR vía provider. "
            "Restaurar: smmlv=self._parametrizacion.get_smmlv()"
        )
        assert "smmlv=" in source, (
            "REGRESIÓN G-09: engine._calcular_pipeline ya no pasa smmlv= a RiesgoCalculator. "
            "FIX_2B exige kwarg obligatorio. Restaurar la inyección."
        )

    def test_g09b_fallback_riesgo_yaml_no_tiene_smmlv(self):
        """G-09b: config/business_rules/riesgo.yaml no contiene 'smmlv'."""
        from nexa_engine.modules.shared.config.business_rules.loader import (
            load_business_rules,
        )
        reg = load_business_rules("riesgo").get("constantes_regulatorias", {})
        assert "smmlv" not in reg, (
            "REGRESIÓN G-09b: smmlv fue reintroducido en el fallback YAML. "
            "FIX_2B lo eliminó. No reintroducir."
        )


# ===========================================================================
# TAREA 4 — G-10 … G-12: aprobaciones_requeridas removido del backend
# ===========================================================================

class TestVisionImprimibleAprobacionesRemoved:
    """Ratchet: aprobaciones_requeridas helper y UMBRAL_* constantes fueron removidos (BLOCK_25)."""

    # G-10
    def test_g10_aprobaciones_helper_eliminado(self):
        """G-10: modules/vision_imprimible/helpers/aprobaciones.py ya no existe."""
        import importlib.util
        spec = importlib.util.find_spec("nexa_engine.modules.vision_imprimible.helpers.aprobaciones")
        assert spec is None, (
            "REGRESIÓN G-10: aprobaciones.py fue reintroducido. "
            "BLOCK_25 lo eliminó — el Excel 'aprobaciones' es solo un área de firmas manual."
        )

    # G-11
    def test_g11_serializer_helpers_sin_aprobaciones(self):
        """G-11: serializer_helpers no contiene _aprobaciones_requeridas ni UMBRAL_* constantes."""
        import inspect
        from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
        source = inspect.getsource(serializer_helpers)
        assert "_aprobaciones_requeridas" not in source, (
            "REGRESIÓN G-11: _aprobaciones_requeridas fue reintroducido en serializer_helpers."
        )
        assert "UMBRAL_GERENCIA" not in source, (
            "REGRESIÓN G-11: UMBRAL_GERENCIA_* constantes fueron reintroducidas en serializer_helpers."
        )
        assert "_aprobaciones_requeridas" not in serializer_helpers.__all__, (
            "REGRESIÓN G-11: _aprobaciones_requeridas está en __all__ de serializer_helpers."
        )

    # G-12
    def test_g12_vision_imprimible_helpers_sin_aprobaciones_export(self):
        """G-12: vision_imprimible.helpers.__init__ no exporta aprobaciones ni UMBRAL_*."""
        from nexa_engine.modules.vision_imprimible.helpers import __all__ as helpers_all
        assert "aprobaciones_requeridas" not in helpers_all, (
            "REGRESIÓN G-12: aprobaciones_requeridas exportado en helpers.__init__."
        )
        assert "UMBRAL_GERENCIA_FINANCIERA_COP" not in helpers_all
        assert "UMBRAL_GERENCIA_GENERAL_COP" not in helpers_all
        assert "UMBRAL_ALTA_DIRECCION_COP" not in helpers_all


# ===========================================================================
# TAREA 5 (extra) — G-13 … G-14: DTO y engine limpios
# ===========================================================================

class TestDtoYEngineGuardrails:
    """Ratchet: el DTO del panel y el engine no tienen campos o patrones prohibidos."""

    # G-13
    def test_g13_panel_dto_no_tiene_campos_prohibidos(self):
        """G-13: ReglasNegocio DTO no tiene descuento_volumen ni porcentaje_acumulado."""
        from nexa_engine.modules.panel.dto.panel_dto import ReglasNegocio
        fields = set(ReglasNegocio.model_fields)
        prohibited = {"descuento_volumen", "porcentaje_acumulado"}
        reintroduced = fields & prohibited
        assert not reintroduced, (
            f"REGRESIÓN G-13: ReglasNegocio tiene campos prohibidos: {reintroduced}. "
            f"descuento_volumen → renombrado a descuento (FIX_1). "
            f"porcentaje_acumulado → eliminado (FIX_3 DEAD_FIELD_LEGACY)."
        )

    def test_g13b_panel_dto_tiene_campo_descuento(self):
        """G-13b: ReglasNegocio DTO tiene 'descuento' (no la versión stale)."""
        from nexa_engine.modules.panel.dto.panel_dto import ReglasNegocio
        assert "descuento" in ReglasNegocio.model_fields, (
            "REGRESIÓN G-13b: ReglasNegocio perdió el campo 'descuento'. "
            "Fue renombrado de descuento_volumen en FIX_1/FIX_3."
        )

    # G-14
    def test_g14_engine_helpers_guard_activo(self):
        """G-14: _calcular_reglas_negocio tiene guard ValueError para política sin Panel."""
        from nexa_engine.modules.calculator_motor.helpers.engine_helpers import _calcular_reglas_negocio
        source = inspect.getsource(_calcular_reglas_negocio)
        assert "ValueError" in source, (
            "REGRESIÓN G-14: el guard ValueError fue eliminado de _calcular_reglas_negocio. "
            "FIX_3 lo introdujo para detectar políticas sin campo Panel. Restaurar."
        )
        assert "_PANEL_FIELDS[nombre]" in source or "_PANEL_FIELDS[" in source, (
            "REGRESIÓN G-14: _calcular_reglas_negocio usa .get() en lugar de lookup explícito. "
            "FIX_3 reemplazó .get(nombre, 0.0) por lookup directo con guard. Restaurar."
        )

    def test_g14b_guard_dispara_para_politica_huerfana(self):
        """G-14b: verificación runtime del guard — política huérfana → ValueError."""
        from nexa_engine.modules.calculator_motor.helpers.engine_helpers import _calcular_reglas_negocio
        from nexa_engine.modules.shared.models import (
            Indexacion, PanelDeControl,
        )

        panel = PanelDeControl(
            cliente="T", tipo_cliente="GA", linea_negocio="C",
            fecha_inicio="2026-01-01", meses_contrato=12, margen=0.10,
            op_cont=0.05, com_cont=0.05, markup=0.02, descuento=0.0,
            tasa_ica=0.02, tasa_gmf=0.004, activa_financiacion=False,
            periodo_pago_dias=30, tasa_mensual_financ=0.0153,
            indexacion=Indexacion(componente_humano="IPC", frecuencia="Anual"),
        )

        class _OrphanProvider:
            def get_politicas_comerciales(self):
                return [{"nombre": "campo_muerto_xyz", "label": "X", "min": 0.0, "max": 1.0}]

        with pytest.raises(ValueError, match="campo_muerto_xyz"):
            _calcular_reglas_negocio(panel, parametrizacion=_OrphanProvider())


# ===========================================================================
# FIX_4A — G-15: Snapshot WAVE1 isolation
# ===========================================================================

class TestSnapshotWave1Isolation:
    """Ratchet: el snapshot histórico WAVE1 no es referenciado por el runtime.

    storage/parametrization/v2-7/ es un snapshot FROZEN-1 (2026-06-04).
    El runtime usa canonical YAML loader, no JSON repository.

    G-16 removido porque business_rules/versions.json y JSON repository
    fueron eliminados por BUSINESS_RULES_CANONICAL_MIGRATION.
    G-15 solo protege que ningún módulo runtime referencie el snapshot stale.
    """

    _SNAPSHOT_PATH_FRAGMENT = "v2-7/business_rules.json"
    _MODULES_ROOT = _REPO_ROOT / "modules"

    # G-15
    def test_g15_ningun_modulo_runtime_referencia_snapshot(self):
        """G-15: ningún archivo .py en modules/ contiene la ruta del snapshot stale.

        La ruta 'v2-7/business_rules.json' solo debe aparecer en:
          - tests/unit/test_frozen_parametrization_integrity.py (hash check)
          - tests/versioning/conftest.py (fixture sintético)
          - scripts/ (one-off scripts)
          - docs/ (documentación histórica)

        Si aparece en modules/, significa que el runtime podría leer el snapshot
        stale con smmlv/descuento_volumen obsoletos.
        """
        violations = []
        for py_file in self._MODULES_ROOT.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if self._SNAPSHOT_PATH_FRAGMENT in content:
                violations.append(str(py_file.relative_to(_REPO_ROOT)))

        assert not violations, (
            f"REGRESIÓN G-15 (FIX_4A): los siguientes módulos runtime referencian el "
            f"snapshot WAVE1 stale 'v2-7/business_rules.json':\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nEl runtime usa canonical YAML loader, no JSON repository."
        )
