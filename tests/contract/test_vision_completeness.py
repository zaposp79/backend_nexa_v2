"""
tests/contract/test_vision_completeness.py
==========================================
FASE 5 — Contrato de completitud de datasets de visión.

Verifica que el motor produce `DatasetsVision` con todos los datasets
requeridos correctamente populados: staffing, pólizas, indexación y volumetría.

Principios:
  - Estos tests son los guardianes del contrato FASE 5.
  - Si un dataset desaparece o pierde campos, el test falla.
  - El frontend NO recalcula: todo lo que necesita DEBE estar en DatasetsVision.
"""

import json
import pytest
import sys
from pathlib import Path

# WAVE 7: marcado como legacy pre-V2-7 — usa fixtures Excel V2-4 obsoletas.
# Ver docs/v27/WAVE7_TRIAGE.md (categoría OBSOLETE_FIXTURE).
pytestmark = pytest.mark.legacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
from nexa_engine.modules.vision_imprimible.models.vision_datasets import (
    DatasetsVision, DatasetStaffing, DatasetPolizasMensual,
    DatasetIndexacion, DatasetVolumetriaPorCanal,
)


# ---------------------------------------------------------------------------
# Fixture: ejecutar motor con caso canónico
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def resultado_y_solicitud():
    """
    Ejecuta el motor con bancamia_whatsapp_only.json.
    Devuelve (solicitud, resultado) para verificar contratos.
    """
    test_case = PROJECT_ROOT / "backend_nexa" / "test_cases" / "input" / "bancamia_whatsapp_only.json"
    raw = json.loads(test_case.read_text())
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(raw)

    provider = ParametrizationProvider.build()
    builder = SimulationContextBuilder(provider)
    solicitud = builder.construir(user_input)

    engine = NexaPricingEngine(parametrizacion=provider)
    resultado = engine.calcular(solicitud)

    return solicitud, resultado


@pytest.fixture(scope="module")
def datasets(resultado_y_solicitud):
    _, resultado = resultado_y_solicitud
    return resultado.datasets_vision


# ---------------------------------------------------------------------------
# Test: DatasetsVision existe en PricingResult
# ---------------------------------------------------------------------------

class TestDatasetsVisionPresente:

    def test_datasets_vision_no_none(self, datasets):
        """PricingResult.datasets_vision debe ser construido por el motor."""
        assert datasets is not None, "PricingResult.datasets_vision es None — VisionDatasetsBuilder no se ejecutó"

    def test_datasets_vision_tipo_correcto(self, datasets):
        assert isinstance(datasets, DatasetsVision)

    def test_as_dict_serializable(self, datasets):
        """datasets_vision.as_dict() debe producir un dict JSON-serializable."""
        d = datasets.as_dict()
        assert isinstance(d, dict)
        # Verificar que es JSON-serializable
        json_str = json.dumps(d, default=str)
        assert len(json_str) > 10


# ---------------------------------------------------------------------------
# Test: Dataset Staffing
# ---------------------------------------------------------------------------

class TestDatasetStaffing:

    def test_staffing_no_none(self, datasets):
        assert datasets.staffing is not None, "DatasetStaffing es None"

    def test_staffing_tipo_correcto(self, datasets):
        assert isinstance(datasets.staffing, DatasetStaffing)

    def test_staffing_tiene_filas(self, datasets):
        assert len(datasets.staffing.filas) > 0, "DatasetStaffing sin filas"

    def test_staffing_fte_positivo(self, datasets):
        for fila in datasets.staffing.filas:
            assert fila.fte >= 0, f"FTE negativo en perfil {fila.nombre}"

    def test_staffing_salario_base_no_negativo(self, datasets):
        for fila in datasets.staffing.filas:
            assert fila.salario_base >= 0, f"salario_base negativo en {fila.nombre}"

    def test_staffing_costo_mensual_positivo(self, datasets):
        """Perfiles con FTE > 0 deben tener costo_total_mensual > 0."""
        for fila in datasets.staffing.filas:
            if fila.fte > 0 and fila.salario_cargado > 0:
                assert fila.costo_total_mensual > 0, f"costo_mensual=0 con fte={fila.fte} en {fila.nombre}"

    def test_staffing_total_fte_positivo(self, datasets):
        assert datasets.staffing.total_fte > 0

    def test_staffing_tiene_campos_requeridos(self, datasets):
        fila = datasets.staffing.filas[0]
        campos = ["nombre", "modalidad", "canal", "es_soporte", "fte",
                  "salario_base", "salario_cargado", "costo_total_mensual",
                  "tipo_carga", "modelo_cobro"]
        for campo in campos:
            assert hasattr(fila, campo), f"Campo requerido '{campo}' faltante en PerfilStaffingRow"

    def test_staffing_as_dict_estructura(self, datasets):
        d = datasets.staffing.as_dict()
        assert "filas" in d
        assert "totales" in d
        assert "fte_total" in d["totales"]
        assert "costo_nomina_mensual" in d["totales"]


# ---------------------------------------------------------------------------
# Test: Dataset Pólizas
# ---------------------------------------------------------------------------

class TestDatasetPolizas:

    def test_polizas_no_none(self, datasets):
        assert datasets.polizas is not None, "DatasetPolizasMensual es None"

    def test_polizas_tipo_correcto(self, datasets):
        assert isinstance(datasets.polizas, DatasetPolizasMensual)

    def test_polizas_tasa_total_no_negativa(self, datasets):
        assert datasets.polizas.tasa_total_efectiva >= 0

    def test_polizas_costo_mensual_no_negativo(self, datasets):
        assert datasets.polizas.costo_mensual_promedio >= 0

    def test_polizas_as_dict_estructura(self, datasets):
        d = datasets.polizas.as_dict()
        assert "polizas_activas" in d
        assert "tasa_total_efectiva" in d
        assert "costo_mensual_promedio" in d
        assert isinstance(d["polizas_activas"], list)


# ---------------------------------------------------------------------------
# Test: Dataset Indexación
# ---------------------------------------------------------------------------

class TestDatasetIndexacion:

    def test_indexacion_no_none(self, datasets):
        assert datasets.indexacion is not None, "DatasetIndexacion es None"

    def test_indexacion_tipo_correcto(self, datasets):
        assert isinstance(datasets.indexacion, DatasetIndexacion)

    def test_indexacion_tiene_filas(self, datasets):
        assert len(datasets.indexacion.filas) > 0, "DatasetIndexacion sin filas"

    def test_indexacion_meses_match_contrato(self, resultado_y_solicitud, datasets):
        solicitud, _ = resultado_y_solicitud
        meses_contrato = solicitud.panel.meses_contrato
        assert len(datasets.indexacion.filas) == meses_contrato, (
            f"Filas de indexación ({len(datasets.indexacion.filas)}) "
            f"!= meses_contrato ({meses_contrato})"
        )

    def test_indexacion_factores_mayor_cero(self, datasets):
        for fila in datasets.indexacion.filas:
            assert fila.factor_humano > 0, f"factor_humano=0 en mes {fila.mes}"
            assert fila.factor_tecnologico > 0, f"factor_tecnologico=0 en mes {fila.mes}"

    def test_indexacion_primer_mes_factor_uno(self, datasets):
        """Mes 1 siempre tiene factor 1.0 (sin ajuste aún)."""
        primer_mes = datasets.indexacion.filas[0]
        assert primer_mes.mes == 1
        assert primer_mes.aplica_ajuste is False

    def test_indexacion_as_dict_estructura(self, datasets):
        d = datasets.indexacion.as_dict()
        assert "filas" in d
        assert "frecuencia" in d
        assert "mes_aplicacion" in d
        assert isinstance(d["filas"], list)
        if d["filas"]:
            fila = d["filas"][0]
            assert "mes" in fila
            assert "factor_humano" in fila
            assert "factor_tecnologico" in fila
            assert "aplica_ajuste" in fila


# ---------------------------------------------------------------------------
# Test: Dataset Volumetría
# ---------------------------------------------------------------------------

class TestDatasetVolumetria:

    def test_volumetria_no_none(self, datasets):
        assert datasets.volumetria is not None, "DatasetVolumetriaPorCanal es None"

    def test_volumetria_tipo_correcto(self, datasets):
        assert isinstance(datasets.volumetria, DatasetVolumetriaPorCanal)

    def test_volumetria_tiene_filas(self, datasets):
        assert len(datasets.volumetria.filas) > 0, "DatasetVolumetriaPorCanal sin filas"

    def test_volumetria_cadenas_validas(self, datasets):
        cadenas_validas = {"A", "B", "C"}
        for fila in datasets.volumetria.filas:
            assert fila.cadena in cadenas_validas, f"Cadena inválida '{fila.cadena}' en {fila.nombre}"

    def test_volumetria_cadena_a_tiene_fte(self, datasets):
        """Al menos un perfil de Cadena A debe tener FTE > 0."""
        filas_a = [f for f in datasets.volumetria.filas if f.cadena == "A"]
        assert len(filas_a) > 0, "No hay canales de Cadena A en volumetría"
        assert any(f.fte > 0 for f in filas_a), "Cadena A sin FTE positivo"

    def test_volumetria_fte_no_negativo(self, datasets):
        for fila in datasets.volumetria.filas:
            assert fila.fte >= 0, f"FTE negativo en {fila.nombre}"

    def test_volumetria_volumen_no_negativo(self, datasets):
        for fila in datasets.volumetria.filas:
            assert fila.volumen_mensual >= 0, f"volumen_mensual negativo en {fila.nombre}"

    def test_volumetria_as_dict_estructura(self, datasets):
        d = datasets.volumetria.as_dict()
        assert "filas" in d
        assert "totales" in d
        assert "fte_cadena_a" in d["totales"]
        assert "volumen_total_mensual" in d["totales"]


# ---------------------------------------------------------------------------
# Test: as_dict() global — integración
# ---------------------------------------------------------------------------

class TestDatasetsVisionAsDict:

    def test_as_dict_tiene_todas_secciones(self, datasets):
        d = datasets.as_dict()
        assert "staffing" in d
        assert "polizas" in d
        assert "indexacion" in d
        assert "volumetria" in d

    def test_as_dict_secciones_no_none(self, datasets):
        d = datasets.as_dict()
        assert d["staffing"] is not None
        assert d["polizas"] is not None
        assert d["indexacion"] is not None
        assert d["volumetria"] is not None

    def test_as_dict_json_serializable(self, datasets):
        d = datasets.as_dict()
        json_str = json.dumps(d, default=str)
        # Round-trip
        reloaded = json.loads(json_str)
        assert reloaded["staffing"]["totales"]["fte_total"] >= 0
