"""
FASE 3 — Tests de Single Source of Truth y DataProvenance

Verifica:
  1. DataProvenance — registro de origen de campos
  2. DataSource enum — categorías correctas
  3. horas_formacion_mensual mapeado desde datos_operativos.horas_formacion_mes
  4. indexacion_frecuencia mapeado desde volumetria.indexacion.frecuencia
  5. Integración DataProvenance con SimulationContextBuilder
  6. validate() — detección de hardcodes pendientes
"""

import pytest

from nexa_engine.modules.calculator_motor.models.data_provenance import DataProvenance, DataSource, ProvenanceEntry
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.dto.user_inputs import PanelDeControlInput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def json_oficial_bancamia():
    """JSON oficial mínimo estilo Bancamia con campos FASE 3."""
    return {
        "datos_operativos": {
            "servicio": "Cobranzas",
            "cliente": "Bancamia",
            "tipo_cliente": "No Grupo Aval",
            "fecha_inicio": "2026-01-01",
            "duracion_meses": 24,
            "ciudad": "Bogota",
            "sede": "Toberin",
            "horas_formacion_mes": 8,        # FASE 3: debe mapearse
            "tasa_ica": 0.0097,
            "tasa_gmf": 0.004,
            "cons_costo_de_financiacion": True,
            "pct_ausentismo": 0.065,
            "pct_rotacion": 0.085,
        },
        "reglas_negocio": {
            "margen_objetivo_cadena_a": 0.18,
            "contingencia_operativa": {"valor": 0.025},
            "contingencia_comercial": {"valor": 0.04},
            "markup": {"valor": 0.0},
            "imprevistos": 0,
        },
        "volumetria": {
            "indexacion": {
                "componente_humano": "IPC",
                "componente_tecnologico": "IPC",
                "frecuencia": "Anual",        # FASE 3: debe mapearse
                "mes_aplicacion": 1,           # FASE 3: debe mapearse
                "tasa_interes_mensual": 0.0153,
            },
            "inbound": {"cadenas_activas": {}, "canales": []},
            "outbound": {"cadenas_activas": {}, "canales": []},
        },
        "escenarios_comerciales": [],
        "condiciones_cadena_a": {
            "perfiles": [
                {
                    "nombre": "Inbound WhatsApp",
                    "modalidad": "Inbound",
                    "canal": "WhatsApp",
                    "fte": 10,
                    "pct_presencia": 1.0,
                    "salario_base": 1423000,
                    "comision_pct": 0.0,
                    "roles_operativos": [],
                    "capacitacion": {
                        "dias_capacitacion_perfil": 10,
                        "incluye_costo_examenes_ingreso": True,
                        "incluye_costo_examenes_rotacion": True,
                        "incluye_costo_capacitacion_anual": True,
                        "incluye_estudio_seguridad_ingreso": False,
                        "incluye_estudio_seguridad_rotacion": False,
                    },
                    "opex_fijo": {"items": [], "staffing": {}},
                    "inversiones": [],
                }
            ]
        },
        "condiciones_cadena_b": {
            "opex": {"items": []},
            "inversiones_capex": [],
            "equipo_soporte_mantenimiento": {"fte": 1, "roles": [], "dispositivos_requeridos": []},
            "costo_variable": {
                "tarifas_por_canal": {"inbound": [], "outbound": []},
                "tasa_escalamiento": {
                    "tarifa_de_escalamiento_indbound": {"tipo": "IC", "value": 0},
                    "tarifa_de_escalamiento_outbound": {"tipo": "IM", "value": 0},
                    "inbound": [], "outbound": [],
                },
            },
            "hitl": {"total_volumen_cadena_b": 0, "equipo": [], "dispositivos_requeridos": []},
        },
        "condiciones_cadena_c": {
            "tarifa_proveedor_canal": {"items": []},
            "inversiones_capex": [],
            "recurso_humano_transversal": {"fte": 0, "roles": [], "opex": []},
            "costo_variable": {
                "tarifas_por_canal": {"inbound": [], "outbound": []},
                "tasa_escalamiento": {
                    "tarifa_de_escalamiento_indbound": {"tipo": "IC", "value": 0},
                    "tarifa_de_escalamiento_outbound": {"tipo": "IM", "value": 0},
                    "inbound": [], "outbound": [],
                },
            },
            "hitl": {"total_volumen_cadena_c": 0, "equipo": [], "opex": []},
        },
    }


# ---------------------------------------------------------------------------
# 1. DataProvenance — unit tests
# ---------------------------------------------------------------------------

class TestDataProvenance:
    def test_record_and_get(self):
        prov = DataProvenance()
        prov.record("panel.ciudad", "Bogota", DataSource.USER_INPUT, "datos_operativos.ciudad")
        entry = prov.get("panel.ciudad")
        assert entry is not None
        assert entry.value == "Bogota"
        assert entry.source == DataSource.USER_INPUT
        assert "datos_operativos.ciudad" in entry.detail

    def test_record_user_input(self):
        prov = DataProvenance()
        prov.record_user_input("panel.margen", 0.18, "reglas_negocio.margen_objetivo_cadena_a")
        entry = prov.get("panel.margen")
        assert entry.source == DataSource.USER_INPUT

    def test_record_parametrization(self):
        prov = DataProvenance()
        prov.record_parametrization("panel.tasa_ica", 0.0097, "OP-ICA[ciudad=Bogota]")
        entry = prov.get("panel.tasa_ica")
        assert entry.source == DataSource.PARAMETRIZATION

    def test_record_default(self):
        prov = DataProvenance()
        prov.record_default("panel.periodo_pago_dias", 90, "Estándar BPO Colombia")
        entry = prov.get("panel.periodo_pago_dias")
        assert entry.source == DataSource.DEFAULT_EXPLICIT

    def test_record_calculated(self):
        prov = DataProvenance()
        prov.record_calculated("panel.tasa_ica_neta", 0.0097, "tasa_ica × (1 - margen)")
        entry = prov.get("panel.tasa_ica_neta")
        assert entry.source == DataSource.CALCULATED

    def test_record_hardcode_pending(self):
        prov = DataProvenance()
        prov.record_hardcode_pending("cadena_c.tarifa_proveedor", 0.0, "Siempre 0.0, debe venir de JSON")
        assert prov.problematic_entries()[0].field_path == "cadena_c.tarifa_proveedor"

    def test_validate_no_hardcodes_returns_empty(self):
        prov = DataProvenance()
        prov.record_user_input("panel.ciudad", "Bogota")
        issues = prov.validate()
        assert issues == []

    def test_validate_hardcodes_returns_list(self):
        prov = DataProvenance()
        prov.record_hardcode_pending("X.y", 0, "pending")
        issues = prov.validate(raise_on_hardcodes=False)
        assert "X.y" in issues

    def test_validate_raise_on_hardcodes(self):
        prov = DataProvenance()
        prov.record_hardcode_pending("X.y", 0, "pending")
        with pytest.raises(ValueError, match="hardcodes"):
            prov.validate(raise_on_hardcodes=True)

    def test_get_by_source(self):
        prov = DataProvenance()
        prov.record_user_input("a", 1)
        prov.record_parametrization("b", 2)
        prov.record_user_input("c", 3)
        user_entries = prov.get_by_source(DataSource.USER_INPUT)
        assert len(user_entries) == 2

    def test_contains(self):
        prov = DataProvenance()
        prov.record_user_input("x", 1)
        assert "x" in prov
        assert "y" not in prov

    def test_len(self):
        prov = DataProvenance()
        prov.record_user_input("a", 1)
        prov.record_user_input("b", 2)
        assert len(prov) == 2

    def test_as_dict_serializable(self):
        prov = DataProvenance()
        prov.record_user_input("panel.ciudad", "Bogota", "datos_operativos.ciudad")
        d = prov.as_dict()
        assert "panel.ciudad" in d
        assert d["panel.ciudad"]["value"] == "Bogota"
        assert d["panel.ciudad"]["source"] == "user_input"

    def test_summary_contains_counts(self):
        prov = DataProvenance()
        prov.record_user_input("a", 1)
        prov.record_parametrization("b", 2)
        summary = prov.summary()
        assert "user_input" in summary
        assert "parametrization" in summary

    def test_provenance_entry_is_problematic(self):
        entry_ok = ProvenanceEntry("x", 1, DataSource.USER_INPUT)
        entry_bad = ProvenanceEntry("y", 0, DataSource.HARDCODE_PENDING_FIX)
        assert not entry_ok.is_problematic()
        assert entry_bad.is_problematic()

    def test_record_user_override(self):
        prov = DataProvenance()
        prov.record_user_override("panel.tasa_ica", 0.0097, "OP-ICA[ciudad=Bogota]")
        entry = prov.get("panel.tasa_ica")
        assert entry.source == DataSource.USER_OVERRIDE_PARAMETRIZATION


# ---------------------------------------------------------------------------
# 2. DataSource enum
# ---------------------------------------------------------------------------

class TestDataSource:
    def test_all_values_exist(self):
        values = {s.value for s in DataSource}
        assert "user_input" in values
        assert "parametrization" in values
        assert "user_override_parametrization" in values
        assert "default_explicit" in values
        assert "calculated" in values
        assert "hardcode_pending_fix" in values


# ---------------------------------------------------------------------------
# 3. horas_formacion_mensual mapeado desde datos_operativos
# ---------------------------------------------------------------------------

class TestHorasFormacionMensual:
    def test_horas_formacion_mapeado_desde_json(self, json_oficial_bancamia):
        """datos_operativos.horas_formacion_mes se mapea a PanelDeControlInput.horas_formacion_mensual."""
        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)
        assert ui.panel.horas_formacion_mensual == 8

    def test_horas_formacion_default_cero_cuando_ausente(self, json_oficial_bancamia):
        """Si horas_formacion_mes no está en el JSON, el default es 0."""
        import copy
        data = copy.deepcopy(json_oficial_bancamia)
        data["datos_operativos"].pop("horas_formacion_mes", None)
        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(data)
        assert ui.panel.horas_formacion_mensual == 0

    def test_panel_de_control_input_tiene_campo(self):
        """PanelDeControlInput tiene el campo horas_formacion_mensual con default 0."""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(PanelDeControlInput)}
        assert "horas_formacion_mensual" in fields


# ---------------------------------------------------------------------------
# 4. indexacion_frecuencia mapeado desde volumetria
# ---------------------------------------------------------------------------

class TestIndexacionFrecuencia:
    def test_frecuencia_mapeada_desde_json(self, json_oficial_bancamia):
        """volumetria.indexacion.frecuencia se mapea a PanelDeControlInput.indexacion_frecuencia."""
        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)
        assert ui.panel.indexacion_frecuencia == "Anual"

    def test_mes_aplicacion_mapeado_desde_json(self, json_oficial_bancamia):
        """volumetria.indexacion.mes_aplicacion se mapea a mes_ajuste_indexacion (calendario)."""
        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)
        # NUEVO format: mes_aplicacion (calendar) → mes_ajuste_indexacion
        # (indexacion_mes_aplicacion is legacy contract-month, stays None for NUEVO)
        assert ui.panel.mes_ajuste_indexacion == 1

    def test_panel_de_control_input_tiene_campos_indexacion(self):
        """PanelDeControlInput tiene campos de indexacion agregados en FASE 3."""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(PanelDeControlInput)}
        assert "indexacion_frecuencia" in fields
        assert "indexacion_mes_aplicacion" in fields


# ---------------------------------------------------------------------------
# 5. DataProvenance integrado con SimulationContextBuilder
# ---------------------------------------------------------------------------

class TestProvenanceIntegracion:
    def test_context_builder_registra_provenance(self, json_oficial_bancamia):
        """SimulationContextBuilder.construir() registra DataProvenance."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)

        builder = SimulationContextBuilder()
        builder.construir(ui)

        prov = builder.last_provenance
        assert prov is not None
        assert len(prov) > 0

    def test_provenance_registra_ciudad(self, json_oficial_bancamia):
        """DataProvenance registra panel.ciudad con fuente USER_INPUT."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder

        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)
        builder = SimulationContextBuilder()
        builder.construir(ui)

        prov = builder.last_provenance
        entry = prov.get("panel.ciudad")
        assert entry is not None
        assert entry.source == DataSource.USER_INPUT
        assert entry.value == "Bogota"

    def test_provenance_registra_tasa_ica(self, json_oficial_bancamia):
        """DataProvenance registra panel.tasa_ica con fuente USER_OVERRIDE_PARAMETRIZATION."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder

        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)
        builder = SimulationContextBuilder()
        builder.construir(ui)

        prov = builder.last_provenance
        entry = prov.get("panel.tasa_ica")
        assert entry is not None
        # El usuario proveyó tasa_ica → USER_OVERRIDE_PARAMETRIZATION
        assert entry.source == DataSource.USER_OVERRIDE_PARAMETRIZATION

    def test_provenance_no_hardcodes_en_panel(self, json_oficial_bancamia):
        """Los campos del panel registrados en provenance no deben tener HARDCODE_PENDING_FIX."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder

        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)
        builder = SimulationContextBuilder()
        builder.construir(ui)

        prov = builder.last_provenance
        hardcodes = prov.problematic_entries()
        assert hardcodes == [], (
            f"Se encontraron hardcodes pendientes en DataProvenance: "
            f"{[h.field_path for h in hardcodes]}"
        )

    def test_provenance_serializable(self, json_oficial_bancamia):
        """DataProvenance.as_dict() retorna un dict serializable."""
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        import json as json_lib

        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial_bancamia)
        builder = SimulationContextBuilder()
        builder.construir(ui)

        prov_dict = builder.last_provenance.as_dict()
        # Debe ser serializable a JSON
        json_str = json_lib.dumps(prov_dict)
        assert len(json_str) > 10


# ---------------------------------------------------------------------------
# 6. float(x or 0) — documentación de instancias en entry_data_adapter
# ---------------------------------------------------------------------------

class TestFloatOrZeroDocumentacion:
    def test_entry_data_adapter_importable(self):
        """entry_data_adapter.py importa sin errores."""
        from nexa_engine.modules.calculator_motor.adapters.entry_data_adapter import NewEntryDataAdapter
        adapter = NewEntryDataAdapter()
        assert adapter is not None

    def test_valores_none_en_tarifas_se_tratan_como_cero(self):
        """float(x or 0) en entry_data_adapter convierte None a 0 (comportamiento documentado)."""
        from nexa_engine.modules.calculator_motor.adapters.entry_data_adapter import NewEntryDataAdapter
        adapter = NewEntryDataAdapter()
        # JSON con tarifa null — debe ser tratada como 0 (no error)
        cadena_b_con_null = {
            "opex": {"items": []},
            "inversiones_capex": [],
            "equipo_soporte_mantenimiento": {"fte": 1, "roles": [], "dispositivos_requeridos": []},
            "costo_variable": {
                "tarifas_por_canal": {
                    "inbound": [{"canal": "WhatsApp", "tarifa": None}],  # null explícito
                    "outbound": [],
                },
                "tasa_escalamiento": {
                    "tarifa_de_escalamiento_indbound": {"tipo": "IC", "value": None},
                    "tarifa_de_escalamiento_outbound": {"tipo": "IM", "value": 0},
                    "inbound": [], "outbound": [],
                },
            },
            "hitl": {"total_volumen_cadena_b": 0, "equipo": [], "dispositivos_requeridos": []},
        }
        result = adapter.adaptar({"condiciones_cadena_b": cadena_b_con_null})
        # El adaptador no debe fallar con valores None — los convierte a 0
        canales = result["condiciones_cadena_b"]["canales"]
        assert all(c["tarifa_unitaria"] == 0.0 for c in canales)
