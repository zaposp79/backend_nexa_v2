"""
FASE 2 — Tests del InputNormalizer

Verifica:
  1. Modos STRICT / VALIDATION / AUDIT
  2. Validación de campos requeridos (H2/H6/H8/H9)
  3. Flatten de capacitacion{} → campos flat en perfiles
  4. Defaults explícitos y su registro en el log
  5. Preservación de estructuras ricas (no eliminación)
  6. Integración completa con UserInputLoader.cargar_desde_dict()
"""

import copy
import pytest

from nexa_engine.modules.calculator_motor.validation.input_normalizer import InputNormalizer
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.dto.normalized_input import NormalizationMode, NormalizedInput


# ---------------------------------------------------------------------------
# Fixture: JSON oficial mínimo válido
# ---------------------------------------------------------------------------

@pytest.fixture
def json_oficial_minimo():
    """JSON oficial mínimo con todos los campos requeridos."""
    return {
        "datos_operativos": {
            "servicio": "SAC",
            "cliente": "TestCo",
            "tipo_cliente": "No Grupo Aval",
            "fecha_inicio": "2026-01-01",
            "duracion_meses": 12,
            "ciudad": "Bogota",
            "tasa_ica": 0.0097,
            "tasa_gmf": 0.004,
            "cons_costo_de_financiacion": True,
            "pct_ausentismo": 0.065,
            "pct_rotacion": 0.085,
        },
        "reglas_negocio": {
            "margen_objetivo_cadena_a": 0.18,
            "contingencia_operativa": {"valor": 0.025, "minimo": 0.025, "maximo": 0.12},
            "contingencia_comercial": {"valor": 0.0, "minimo": 0.0, "maximo": 0.07},
            "markup": {"valor": 0.0, "minimo": 0.0, "maximo": 0.08},
            "imprevistos": 0,
        },
        "volumetria": {
            "indexacion": {
                "componente_humano": "IPC",
                "componente_tecnologico": "IPC",
                "frecuencia": "Anual",
                "mes_aplicacion": 1,
                "tasa_interes_mensual": 0.0153,
            },
            "inbound": {"cadenas_activas": {"cadena_a": True, "cadena_b": False, "cadena_c": False}, "canales": []},
            "outbound": {"cadenas_activas": {"cadena_a": False, "cadena_b": False, "cadena_c": False}, "canales": []},
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
                        "por_capacitacion_mes": 0.09,
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
            "costo_variable": {"tarifas_por_canal": {"inbound": [], "outbound": []},
                               "tasa_escalamiento": {"tarifa_de_escalamiento_indbound": {"tipo": "Input Calculado", "value": 0},
                                                     "tarifa_de_escalamiento_outbound": {"tipo": "Input Manual", "value": 0},
                                                     "inbound": [], "outbound": []}},
            "hitl": {"total_volumen_cadena_b": 0, "equipo": [], "dispositivos_requeridos": []},
        },
        "condiciones_cadena_c": {
            "tarifa_proveedor_canal": {"items": []},
            "inversiones_capex": [],
            "recurso_humano_transversal": {"fte": 0, "roles": [], "opex": []},
            "costo_variable": {"tarifas_por_canal": {"inbound": [], "outbound": []},
                               "tasa_escalamiento": {"tarifa_de_escalamiento_indbound": {"tipo": "Input Calculado", "value": 0},
                                                     "tarifa_de_escalamiento_outbound": {"tipo": "Input Manual", "value": 0},
                                                     "inbound": [], "outbound": []}},
            "hitl": {"total_volumen_cadena_c": 0, "equipo": [], "opex": []},
        },
    }


# ---------------------------------------------------------------------------
# 1. Modo STRICT — campos requeridos
# ---------------------------------------------------------------------------

class TestModoStrict:
    def test_json_valido_no_raise(self, json_oficial_minimo):
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        assert isinstance(result, NormalizedInput)
        assert result.is_valid

    @pytest.mark.parametrize("campo_faltante", [
        "ciudad", "fecha_inicio", "duracion_meses",
    ])
    def test_campo_requerido_datos_operativos_raise(self, json_oficial_minimo, campo_faltante):
        data = copy.deepcopy(json_oficial_minimo)
        del data["datos_operativos"][campo_faltante]
        normalizer = InputNormalizer()
        with pytest.raises(ValueError, match=campo_faltante):
            normalizer.normalize(data, NormalizationMode.STRICT)

    def test_margen_objetivo_faltante_raise(self, json_oficial_minimo):
        data = copy.deepcopy(json_oficial_minimo)
        del data["reglas_negocio"]["margen_objetivo_cadena_a"]
        normalizer = InputNormalizer()
        with pytest.raises(ValueError, match="margen_objetivo_cadena_a"):
            normalizer.normalize(data, NormalizationMode.STRICT)

    def test_ciudad_vacia_raise(self, json_oficial_minimo):
        data = copy.deepcopy(json_oficial_minimo)
        data["datos_operativos"]["ciudad"] = ""
        normalizer = InputNormalizer()
        with pytest.raises(ValueError, match="ciudad"):
            normalizer.normalize(data, NormalizationMode.STRICT)

    def test_fecha_anio_invalido_raise(self, json_oficial_minimo):
        data = copy.deepcopy(json_oficial_minimo)
        data["datos_operativos"]["fecha_inicio"] = "1999-01-01"
        normalizer = InputNormalizer()
        with pytest.raises(ValueError, match="1999"):
            normalizer.normalize(data, NormalizationMode.STRICT)


# ---------------------------------------------------------------------------
# 2. Modo VALIDATION — acumula todos los errores
# ---------------------------------------------------------------------------

class TestModoValidation:
    def test_multiples_errores_consolidados(self, json_oficial_minimo):
        data = copy.deepcopy(json_oficial_minimo)
        del data["datos_operativos"]["ciudad"]
        del data["datos_operativos"]["fecha_inicio"]
        del data["reglas_negocio"]["margen_objetivo_cadena_a"]

        normalizer = InputNormalizer()
        with pytest.raises(ValueError) as exc_info:
            normalizer.normalize(data, NormalizationMode.VALIDATION)

        msg = str(exc_info.value)
        assert "ciudad" in msg
        assert "fecha_inicio" in msg
        assert "margen_objetivo_cadena_a" in msg
        # Todos los errores en un solo ValueError
        assert "3 errores" in msg

    def test_json_valido_no_raise(self, json_oficial_minimo):
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.VALIDATION)
        assert result.is_valid


# ---------------------------------------------------------------------------
# 3. Modo AUDIT — loguea y continúa
# ---------------------------------------------------------------------------

class TestModoAudit:
    def test_campo_faltante_no_raise_genera_warning(self, json_oficial_minimo):
        data = copy.deepcopy(json_oficial_minimo)
        del data["datos_operativos"]["ciudad"]

        normalizer = InputNormalizer()
        result = normalizer.normalize(data, NormalizationMode.AUDIT)

        assert not result.log.has_errors  # no errors en AUDIT
        assert result.log.has_warnings
        warning_fields = [w.field_path for w in result.log.warnings]
        assert "datos_operativos.ciudad" in warning_fields


# ---------------------------------------------------------------------------
# 4. Flatten de capacitacion{} → campos flat
# ---------------------------------------------------------------------------

class TestFlattenCapacitacion:
    def test_dias_cap_inicial_extraido(self, json_oficial_minimo):
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert perfil["dias_cap_inicial"] == 10
        assert perfil["dias_cap_rotacion"] == 10

    def test_incluye_examenes_extraido(self, json_oficial_minimo):
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert perfil["incluye_examenes"] is True

    def test_incluye_seguridad_extraido(self, json_oficial_minimo):
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert perfil["incluye_seguridad"] is False

    def test_capacitacion_preservada_completa(self, json_oficial_minimo):
        """La sub-estructura capacitacion{} se preserva intacta para context_builder."""
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        # El dict capacitacion debe seguir existiendo con todos sus campos
        assert "capacitacion" in perfil
        cap = perfil["capacitacion"]
        assert cap["dias_capacitacion_perfil"] == 10
        assert cap["incluye_costo_examenes_ingreso"] is True

    def test_opex_fijo_preservado(self, json_oficial_minimo):
        """opex_fijo{} se preserva intacto — NO se elimina."""
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert "opex_fijo" in perfil

    def test_inversiones_preservadas(self, json_oficial_minimo):
        """inversiones[] se preserva intacto — NO se elimina."""
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert "inversiones" in perfil

    def test_roles_operativos_preservados(self, json_oficial_minimo):
        """roles_operativos[] se preserva intacto — NO se elimina."""
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert "roles_operativos" in perfil

    def test_capacitacion_con_valores_custom(self, json_oficial_minimo):
        """Valores custom en capacitacion{} se respetan sobre los defaults."""
        data = copy.deepcopy(json_oficial_minimo)
        data["condiciones_cadena_a"]["perfiles"][0]["capacitacion"]["dias_capacitacion_perfil"] = 15
        data["condiciones_cadena_a"]["perfiles"][0]["capacitacion"]["incluye_estudio_seguridad_ingreso"] = True

        normalizer = InputNormalizer()
        result = normalizer.normalize(data, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert perfil["dias_cap_inicial"] == 15
        assert perfil["incluye_seguridad"] is True

    def test_perfil_sin_capacitacion_usa_defaults(self, json_oficial_minimo):
        """Perfil sin capacitacion{} aplica todos los defaults documentados."""
        data = copy.deepcopy(json_oficial_minimo)
        del data["condiciones_cadena_a"]["perfiles"][0]["capacitacion"]

        normalizer = InputNormalizer()
        result = normalizer.normalize(data, NormalizationMode.STRICT)
        perfil = result.data["condiciones_cadena_a"]["perfiles"][0]
        assert perfil["dias_cap_inicial"] == 10
        assert perfil["incluye_examenes"] is True
        assert perfil["incluye_seguridad"] is False


# ---------------------------------------------------------------------------
# 5. Log de defaults
# ---------------------------------------------------------------------------

class TestLogDefaults:
    def test_defaults_registrados_cuando_se_aplican(self, json_oficial_minimo):
        """Cada default aplicado aparece en el log."""
        data = copy.deepcopy(json_oficial_minimo)
        del data["condiciones_cadena_a"]["perfiles"][0]["capacitacion"]

        normalizer = InputNormalizer()
        result = normalizer.normalize(data, NormalizationMode.STRICT)

        field_paths = [d.field_path for d in result.log.defaults_applied]
        assert "condiciones_cadena_a.perfiles[0].dias_cap_inicial" in field_paths
        assert "condiciones_cadena_a.perfiles[0].incluye_examenes" in field_paths

    def test_no_defaults_cuando_campos_provistos(self, json_oficial_minimo):
        """Si todos los campos están provistos, no se aplican defaults de capacitacion."""
        normalizer = InputNormalizer()
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        cap_defaults = [
            d for d in result.log.defaults_applied
            if "dias_cap_inicial" in d.field_path
        ]
        assert len(cap_defaults) == 0

    def test_raw_no_modificado(self, json_oficial_minimo):
        """El raw del NormalizedInput es idéntico al input original."""
        normalizer = InputNormalizer()
        original = copy.deepcopy(json_oficial_minimo)
        result = normalizer.normalize(json_oficial_minimo, NormalizationMode.STRICT)
        assert result.raw == original


# ---------------------------------------------------------------------------
# 6. Formato legacy — pasa sin transformación
# ---------------------------------------------------------------------------

class TestFormatoLegacy:
    def test_formato_panel_de_control_sin_transformacion(self):
        """El formato legacy (panel_de_control) pasa directo sin modificación."""
        data_legacy = {
            "panel_de_control": {
                "cliente": "TestCo",
                "linea_negocio": "SAC",
                "ciudad": "Bogota",
                "fecha_inicio": "2026-01-01",
                "meses_contrato": 12,
                "margen": 0.18,
                "op_cont": 0.025,
                "tasa_ica": 0.0097,
                "tasa_gmf": 0.004,
            },
            "condiciones_cadena_a": {"perfiles": []},
            "condiciones_cadena_b": {},
            "condiciones_cadena_c": {},
        }
        normalizer = InputNormalizer()
        result = normalizer.normalize(data_legacy, NormalizationMode.STRICT)
        # No debe haber transformaciones para formato legacy
        assert result.data == data_legacy
        assert len(result.log.defaults_applied) == 0
        assert not result.log.has_errors


# ---------------------------------------------------------------------------
# 7. Integración: UserInputLoader + InputNormalizer
# ---------------------------------------------------------------------------

class TestIntegracionUserInputLoader:
    def test_cargar_desde_dict_json_oficial_no_falla(self, json_oficial_minimo):
        """UserInputLoader.cargar_desde_dict() acepta el JSON oficial completo."""
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(json_oficial_minimo)
        assert user_input is not None
        assert user_input.panel.ciudad == "Bogota"
        assert user_input.panel.meses_contrato == 12
        assert user_input.panel.margen == pytest.approx(0.18)

    def test_perfiles_normalizados_correctamente(self, json_oficial_minimo):
        """Los perfiles del JSON oficial se cargan con los campos correctos."""
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(json_oficial_minimo)
        assert len(user_input.cadena_a.perfiles) == 1
        perfil = user_input.cadena_a.perfiles[0]
        assert perfil.nombre == "Inbound WhatsApp"
        assert perfil.fte == 10
        assert perfil.dias_cap_inicial == 10
        assert perfil.incluye_examenes is True
        assert perfil.incluye_seguridad is False

    def test_polizas_cargadas(self, json_oficial_minimo):
        """Polizas del JSON oficial se cargan correctamente."""
        data = copy.deepcopy(json_oficial_minimo)
        data["polizas"] = [
            {
                "nombre": "Póliza Test",
                "activa": True,
                "pct_poliza": 0.005,
                "pct_atribuible": 0.1,
                "aplica_extension": False,
                "meses_extension": None,
                "cadenas": {"cadena_a": True, "cadena_b": False, "cadena_c": False},
            }
        ]
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(data)
        assert len(user_input.polizas) == 1
        assert user_input.polizas[0].nombre == "Póliza Test"

    def test_json_bancamia_completo(self):
        """Smoke test con el JSON oficial de Bancamia (estructura completa)."""
        import json, pathlib
        json_path = pathlib.Path(__file__).parent.parent / "golden" / "bancamia_sac_v25_input.json"
        if not json_path.exists():
            pytest.skip("bancamia_sac_v25_input.json no disponible")
        with open(json_path) as f:
            data = json.load(f)
        if "datos_operativos" not in data:
            pytest.skip("Fixture es formato legacy, no oficial")
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(data)
        assert user_input is not None

    def test_doble_anidamiento_condiciones_cadena_a_se_desenvuelve(self, json_oficial_minimo):
        """Double-nesting de condiciones_cadena_a es detectado y desanidado."""
        data = copy.deepcopy(json_oficial_minimo)
        # Simulate the client bug: wrapping condiciones_cadena_a in itself
        data["condiciones_cadena_a"] = {
            "condiciones_cadena_a": data["condiciones_cadena_a"]
        }
        normalizer = InputNormalizer()
        result = normalizer.normalize(data, NormalizationMode.STRICT)
        # Perfiles should still be accessible after unwrapping
        cadena_a = result.data.get("condiciones_cadena_a", {})
        assert "perfiles" in cadena_a, "perfiles should be at top level after unwrapping"
        assert len(cadena_a["perfiles"]) == 1
        # Warning should be logged
        warning_msgs = [w.message for w in result.log.warnings]
        assert any("doble-anidado" in m for m in warning_msgs)
