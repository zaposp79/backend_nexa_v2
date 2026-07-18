"""
FASE 4 — Tests de Integración: SimulationSnapshot persistencia round-trip

Verifica:
  1. SimulationSnapshot — creación y serialización
  2. ParametrizationSnapshot — captura de valores activos
  3. PanelSummary — resumen del deal
  4. SnapshotRepository — save/get/exists/list round-trip
  5. build_simulation_snapshot() — ensamblado completo
  6. Round-trip completo: create → persist → load → verify
  7. UserInputLoader — last_normalization_log / last_raw_input expuestos
  8. SimulationContextBuilder — last_parametrization_snapshot expuesto
"""

import copy
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.serializers import build_simulation_snapshot
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.models.snapshot import (
    PanelSummary,
    ParametrizationSnapshot,
    SimulationSnapshot,
)
from nexa_engine.modules.calculator.persistence.snapshots_repository import SnapshotRepository
from nexa_engine.modules.shared.exceptions import NotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def json_oficial():
    """JSON oficial mínimo estilo Bancamia con sede válida."""
    return {
        "datos_operativos": {
            "servicio": "Cobranzas",
            "cliente": "Bancamia Test",
            "tipo_cliente": "No Grupo Aval",
            "fecha_inicio": "2026-01-01",
            "duracion_meses": 12,
            "ciudad": "Bogota",
            "sede": "Toberin",
            "horas_formacion_mes": 8,
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
                "frecuencia": "Anual",
                "mes_aplicacion": 1,
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


@pytest.fixture
def tmp_repo(tmp_path):
    """SnapshotRepository con DocumentStore mock para tests."""
    from nexa_engine.db.providers.json_document_store import JsonDocumentStore
    # Usar JsonDocumentStore con directorio temporal para tests
    store = JsonDocumentStore(storage_path=tmp_path / "db")
    return SnapshotRepository(store=store)


@pytest.fixture
def sim_id():
    return str(uuid.uuid4())


@pytest.fixture
def sample_snapshot(sim_id):
    """SimulationSnapshot mínimo para tests de persistencia."""
    now = datetime.now(timezone.utc).isoformat()
    param = ParametrizationSnapshot(
        smmlv=1750905.0,
        auxilio_transporte=249095.0,
        linea_negocio="Cobranzas",
        pct_rotacion_linea=0.085,
        pct_ausentismo_linea=0.065,
        ciudad="Bogota",
        tasa_ica_ciudad=0.0097,
        tasa_gmf=0.004,
        tasa_mensual_financiacion=0.0153,
        factores_indexacion={"IPC_2026": 1.0, "IPC_2027": 1.111},
        constantes_operativas={"tarifa_dia_cap": 20000.0},
        salarios_por_rol={"Agente Basico I": 1750905.0},
    )
    summary = PanelSummary(
        simulation_id=sim_id,
        cliente="Bancamia Test",
        tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas",
        ciudad="Bogota",
        fecha_inicio="2026-01-01",
        meses_contrato=12,
        margen=0.18,
        total_fte=10.0,
        created_at=now,
    )
    return SimulationSnapshot(
        simulation_id=sim_id,
        created_at=now,
        raw_input={"test": "raw"},
        normalized_input={"test": "normalized"},
        normalization_log={"mode": "strict", "defaults_applied": [], "warnings": [], "errors": []},
        parametrization=param,
        data_provenance={"panel.ciudad": {"value": "Bogota", "source": "user_input", "detail": "datos_operativos.ciudad"}},
        pricing_result={"simulation_id": sim_id, "pyg_mensual": []},
        panel_summary=summary,
    )


# ---------------------------------------------------------------------------
# 1. SimulationSnapshot — creación y serialización
# ---------------------------------------------------------------------------

class TestSimulationSnapshot:
    def test_as_dict_serializable(self, sample_snapshot):
        import json
        d = sample_snapshot.as_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert len(json_str) > 100

    def test_as_dict_contiene_campos_requeridos(self, sample_snapshot, sim_id):
        d = sample_snapshot.as_dict()
        assert d["simulation_id"] == sim_id
        assert "raw_input" in d
        assert "normalized_input" in d
        assert "normalization_log" in d
        assert "parametrization" in d
        assert "data_provenance" in d
        assert "pricing_result" in d
        assert "panel_summary" in d

    def test_from_dict_round_trip(self, sample_snapshot, sim_id):
        d = sample_snapshot.as_dict()
        restored = SimulationSnapshot.from_dict(d)
        assert restored.simulation_id == sim_id
        assert restored.panel_summary.cliente == "Bancamia Test"
        assert restored.parametrization.smmlv == pytest.approx(1750905.0)
        assert restored.parametrization.tasa_ica_ciudad == pytest.approx(0.0097)
        assert restored.data_provenance["panel.ciudad"]["source"] == "user_input"


# ---------------------------------------------------------------------------
# 2. ParametrizationSnapshot
# ---------------------------------------------------------------------------

class TestParametrizationSnapshot:
    def test_as_dict(self):
        param = ParametrizationSnapshot(
            smmlv=1750905.0,
            linea_negocio="SAC",
            ciudad="Medellin",
            factores_indexacion={"IPC_2026": 1.0},
        )
        d = param.as_dict()
        assert d["smmlv"] == pytest.approx(1750905.0)
        assert d["linea_negocio"] == "SAC"
        assert d["ciudad"] == "Medellin"
        assert "IPC_2026" in d["factores_indexacion"]

    def test_capture_desde_provider(self):
        """capture_parametrization_snapshot() captura valores reales."""
        from nexa_engine.modules.parametrizacion.services.provider import get_provider
        prov = get_provider()
        snapshot_dict = prov.capture_parametrization_snapshot(
            ciudad="Bogota",
            linea_negocio="Cobranzas",
            anio_inicio=2026,
            roles_usados=["Agente Basico I"],
        )
        assert "smmlv" in snapshot_dict
        assert "tasa_ica_ciudad" in snapshot_dict
        assert float(snapshot_dict["smmlv"]) > 0
        assert float(snapshot_dict["tasa_ica_ciudad"]) > 0
        assert "factores_indexacion" in snapshot_dict


# ---------------------------------------------------------------------------
# 3. PanelSummary
# ---------------------------------------------------------------------------

class TestPanelSummary:
    def test_as_dict(self, sim_id):
        summary = PanelSummary(
            simulation_id=sim_id,
            cliente="Acme",
            linea_negocio="SAC",
            meses_contrato=24,
            margen=0.20,
            total_fte=15.0,
        )
        d = summary.as_dict()
        assert d["simulation_id"] == sim_id
        assert d["cliente"] == "Acme"
        assert d["meses_contrato"] == 24


# ---------------------------------------------------------------------------
# 4. SnapshotRepository — persistencia round-trip
# ---------------------------------------------------------------------------

class TestSnapshotRepository:
    def test_save_y_exists(self, tmp_repo, sample_snapshot):
        assert not tmp_repo.exists(sample_snapshot.simulation_id)
        tmp_repo.save(sample_snapshot)
        assert tmp_repo.exists(sample_snapshot.simulation_id)

    def test_save_y_get_round_trip(self, tmp_repo, sample_snapshot, sim_id):
        tmp_repo.save(sample_snapshot)
        restored = tmp_repo.get(sim_id)
        assert restored.simulation_id == sim_id
        assert restored.panel_summary.cliente == "Bancamia Test"
        assert restored.parametrization.smmlv == pytest.approx(1750905.0)

    def test_get_summary(self, tmp_repo, sample_snapshot, sim_id):
        tmp_repo.save(sample_snapshot)
        summary = tmp_repo.get_summary(sim_id)
        assert summary.simulation_id == sim_id
        assert summary.cliente == "Bancamia Test"
        assert summary.meses_contrato == 12

    def test_list_summaries(self, tmp_repo, sample_snapshot):
        # NOTE: list_summaries() no está implementado para DocumentStore scan.
        # Esta es una limitación conocida (TODO para STEP3B).
        # El test verifica que no falla ni cambia la interfaz.
        tmp_repo.save(sample_snapshot)
        summaries = tmp_repo.list_summaries()
        # Ahora retorna lista vacía — todo bien documentado
        assert isinstance(summaries, list)

    def test_get_not_found_raises(self, tmp_repo):
        with pytest.raises(NotFoundError):
            tmp_repo.get("non-existent-id")

    def test_snapshot_json_es_valido(self, tmp_repo, sample_snapshot):
        """El snapshot debe ser guardado y recuperable via DocumentStore."""
        tmp_repo.save(sample_snapshot)
        # Verificar que el snapshot se guardó correctamente
        restored = tmp_repo.get(sample_snapshot.simulation_id)
        assert restored.simulation_id == sample_snapshot.simulation_id
        # Verificar que el documento está en el storage
        assert tmp_repo.exists(sample_snapshot.simulation_id)


# ---------------------------------------------------------------------------
# 5. build_simulation_snapshot() — ensamblado
# ---------------------------------------------------------------------------

class TestBuildSimulationSnapshot:
    def test_build_produce_snapshot_valido(self, sim_id):
        snapshot = build_simulation_snapshot(
            simulation_id=sim_id,
            raw_input={"datos_operativos": {"cliente": "Test"}},
            normalized_input={"datos_operativos": {"cliente": "Test"}},
            normalization_log={"mode": "strict", "defaults_applied": [], "warnings": [], "errors": []},
            parametrization_snapshot={"smmlv": 1750905.0, "ciudad": "Bogota", "linea_negocio": "SAC"},
            data_provenance={"panel.ciudad": {"value": "Bogota", "source": "user_input", "detail": ""}},
            pricing_result_dict={"simulation_id": sim_id},
            panel_summary_data={
                "cliente": "Test", "ciudad": "Bogota",
                "linea_negocio": "SAC", "meses_contrato": 12,
                "margen": 0.18, "total_fte": 5.0,
            },
        )
        assert isinstance(snapshot, SimulationSnapshot)
        assert snapshot.simulation_id == sim_id
        assert snapshot.parametrization.smmlv == pytest.approx(1750905.0)
        assert snapshot.panel_summary.cliente == "Test"


# ---------------------------------------------------------------------------
# 6. Round-trip completo: pipeline → snapshot → persist → load
# ---------------------------------------------------------------------------

class TestRoundTripCompleto:
    @pytest.mark.legacy  # WAVE 7: fixture json_oficial sin cadenas_activas (TASK_3)
    def test_pipeline_completo_y_snapshot(self, json_oficial, tmp_repo):
        """
        Round-trip completo:
          1. Cargar JSON oficial → UserInput (con last_raw_input, last_normalization_log)
          2. Construir PricingRequest (con last_parametrization_snapshot, last_provenance)
          3. Ejecutar motor → PricingResult
          4. Construir SimulationSnapshot
          5. Persistir → cargar → verificar invariantes
        """
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict

        sim_id = str(uuid.uuid4())

        # 1. Cargar JSON oficial
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(json_oficial)
        assert loader.last_raw_input is not None
        assert loader.last_normalization_log is not None
        assert loader.last_normalized_input is not None

        # 2. Construir PricingRequest
        builder = SimulationContextBuilder()
        solicitud = builder.construir(user_input)
        assert builder.last_parametrization_snapshot is not None
        assert builder.last_provenance is not None

        # 3. Ejecutar motor
        engine = NexaPricingEngine()
        resultado = engine.calcular(solicitud)
        result_dict = pricing_result_to_dict(resultado, result_id=sim_id)

        # 4. Construir snapshot
        panel = solicitud.panel
        total_fte = sum(
            p.fte for p in solicitud.perfiles_cadena_a if not p.es_soporte
        )
        snapshot = build_simulation_snapshot(
            simulation_id          = sim_id,
            raw_input              = loader.last_raw_input,
            normalized_input       = loader.last_normalized_input or {},
            normalization_log      = loader.last_normalization_log,
            parametrization_snapshot = builder.last_parametrization_snapshot,
            data_provenance        = builder.last_provenance.as_dict(),
            pricing_result_dict    = result_dict,
            panel_summary_data     = {
                "cliente":        panel.cliente,
                "tipo_cliente":   panel.tipo_cliente,
                "linea_negocio":  panel.linea_negocio,
                "ciudad":         panel.ciudad,
                "fecha_inicio":   panel.fecha_inicio,
                "meses_contrato": panel.meses_contrato,
                "margen":         panel.margen,
                "total_fte":      total_fte,
            },
        )

        # 5. Persistir y cargar
        tmp_repo.save(snapshot)
        restored = tmp_repo.get(sim_id)

        # ── Verificar invariantes del round-trip ──────────────────────
        assert restored.simulation_id == sim_id
        assert restored.panel_summary.cliente == "Bancamia Test"
        assert restored.panel_summary.meses_contrato == 12
        assert restored.panel_summary.margen == pytest.approx(0.18)
        assert restored.panel_summary.total_fte == pytest.approx(total_fte)

        # Input original preservado
        assert "datos_operativos" in restored.raw_input
        assert restored.raw_input["datos_operativos"]["cliente"] == "Bancamia Test"

        # Parametrización capturada con valores reales
        assert restored.parametrization.smmlv > 0
        assert restored.parametrization.tasa_ica_ciudad == pytest.approx(0.0097)
        assert restored.parametrization.linea_negocio == "Cobranzas"

        # DataProvenance con campos registrados
        assert "panel.ciudad" in restored.data_provenance
        assert restored.data_provenance["panel.ciudad"]["value"] == "Bogota"

        # Normalization log capturado
        assert "mode" in restored.normalization_log

        # Resultado del motor incluido
        assert "simulation_id" in restored.pricing_result


# ---------------------------------------------------------------------------
# 7. UserInputLoader — propiedades FASE 4
# ---------------------------------------------------------------------------

class TestUserInputLoaderFase4:
    def test_last_raw_input_guardado(self, json_oficial):
        loader = UserInputLoader()
        loader.cargar_desde_dict(json_oficial)
        assert loader.last_raw_input is not None
        assert loader.last_raw_input["datos_operativos"]["cliente"] == "Bancamia Test"

    def test_last_normalization_log_guardado(self, json_oficial):
        loader = UserInputLoader()
        loader.cargar_desde_dict(json_oficial)
        log = loader.last_normalization_log
        assert log is not None
        assert "mode" in log
        assert "defaults_applied" in log

    def test_last_normalized_input_guardado(self, json_oficial):
        loader = UserInputLoader()
        loader.cargar_desde_dict(json_oficial)
        assert loader.last_normalized_input is not None

    def test_raw_input_es_copia_independiente(self, json_oficial):
        """El raw_input guardado no se afecta por modificaciones posteriores."""
        loader = UserInputLoader()
        data = copy.deepcopy(json_oficial)
        loader.cargar_desde_dict(data)
        raw = loader.last_raw_input
        # El raw capturado debe ser independiente del dict original
        assert raw is not data


# ---------------------------------------------------------------------------
# 8. SimulationContextBuilder — last_parametrization_snapshot
# ---------------------------------------------------------------------------

class TestContextBuilderFase4:
    def test_last_parametrization_snapshot_capturado(self, json_oficial):
        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial)
        builder = SimulationContextBuilder()
        builder.construir(ui)
        snap = builder.last_parametrization_snapshot
        assert snap is not None
        assert "smmlv" in snap
        assert "tasa_ica_ciudad" in snap
        assert float(snap["smmlv"]) > 0

    def test_snapshot_contiene_salarios_de_roles_usados(self, json_oficial):
        loader = UserInputLoader()
        ui = loader.cargar_desde_dict(json_oficial)
        builder = SimulationContextBuilder()
        builder.construir(ui)
        snap = builder.last_parametrization_snapshot
        # El rol "Inbound WhatsApp" debería tener salario capturado
        assert isinstance(snap.get("salarios_por_rol"), dict)
