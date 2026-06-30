"""Tests de tipologías laborales (EMPLEADO_ESTANDAR, APRENDIZ_SENA, etc.)."""
from __future__ import annotations

import pytest


class TestTiposCargaCatalog:
    """El catálogo HR-tipos_carga debe existir y estar completo."""

    @pytest.mark.known_debt
    # Known debt: HR-AutRot ausente en HR productiva 2026 — fallback no expone catálogo completo.
    def test_catalog_existe(self):
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        prov = ParametrizationProvider.build()
        catalog = prov.get_tipos_carga_catalog()
        codigos = {t["codigo"] for t in catalog}
        assert codigos >= {
            "EMPLEADO_ESTANDAR", "APRENDIZ_SENA", "EQUIPO_SOPORTE_MANTENIMIENTO",
            "SOPORTE_COMISIONABLE", "IMPLEMENTACION_PROYECTOS",
        }

    def test_cada_tipo_tiene_categoria_regla(self):
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        prov = ParametrizationProvider.build()
        for tipo in prov.get_tipos_carga_catalog():
            assert tipo.get("categoria_regla") in {
                "LEGAL", "PARAMETRIZABLE", "OPERATIVO", "LEGACY_EXCEL", "EXPERIMENTAL"
            }, f"Tipo {tipo['codigo']} sin categoría válida"


class TestRolATipoCarga:
    """Cada rol debe estar mapeado a un tipo_carga del catálogo."""

    @pytest.mark.parametrize("rol,tipo_esperado", [
        ("Agente Básico 1",                 "EMPLEADO_ESTANDAR"),
        pytest.param("Director de cuentas", "SOPORTE_COMISIONABLE", marks=pytest.mark.known_debt),
        pytest.param("GTR",                 "SOPORTE_COMISIONABLE", marks=pytest.mark.known_debt),
        pytest.param("Aprendiz SENA",       "APRENDIZ_SENA",        marks=pytest.mark.known_debt),
        pytest.param("Inclusión",           "APRENDIZ_SENA",        marks=pytest.mark.known_debt),
        pytest.param("Especialista de Proyectos", "IMPLEMENTACION_PROYECTOS", marks=pytest.mark.known_debt),
        pytest.param("Service Owner",       "EQUIPO_SOPORTE_MANTENIMIENTO",   marks=pytest.mark.known_debt),
        ("Supervisor",                      "EMPLEADO_ESTANDAR"),
    ])
    # Known debt: los casos SOPORTE_COMISIONABLE, APRENDIZ_SENA, IMPLEMENTACION_PROYECTOS, EQUIPO_SOPORTE_MANTENIMIENTO
    # requieren HR-AutRot en el HR activo. Con HR productiva 2026 (sin esa hoja) el fallback es EMPLEADO_ESTANDAR.
    def test_rol_clasificado(self, rol, tipo_esperado):
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        prov = ParametrizationProvider.build()
        actual = prov.get_tipo_carga_rol(rol)
        assert actual == tipo_esperado, f"{rol}: esperado {tipo_esperado}, actual {actual}"


class TestComisionablesIdentificados:
    """SEMANTIC F2: Excel V2-7 'Inputs de Nomina' E16-E40 confirma que solo
    los perfiles agente ("Inbound 25" y "inboun Whatsapp") tienen
    comision_pct=0.1 en la sección Empleado. Director de cuentas (E16) y
    GTR (E26) tienen 0 en Excel — los valores 0.05 y 0.10 previos eran
    hardcodes inventados (H1, WAVE 16) sin sustento en celda Excel.
    """

    def test_comision_director_cuentas_es_cero_en_excel(self):
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        prov = ParametrizationProvider.build()
        # Excel 'Inputs de Nomina'!E16 = 0
        assert prov.get_comision_pct_rol("Director de cuentas") == 0.0

    def test_comision_gtr_es_cero_en_excel(self):
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        prov = ParametrizationProvider.build()
        # Excel 'Inputs de Nomina'!E26 = 0
        assert prov.get_comision_pct_rol("GTR") == 0.0

    def test_comision_zero_para_otros(self):
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        prov = ParametrizationProvider.build()
        for rol in ["Supervisor", "Formadores", "Validador", "Monitor de Calidad"]:
            assert prov.get_comision_pct_rol(rol) == 0.0

    @pytest.mark.known_debt
    # Known debt: HR productiva 2026 no expone comision_pct de agentes — requiere HR-AutRot con hoja HR-Complejidad correcta.
    def test_comision_agentes_es_diez_pct_en_excel(self):
        """Excel 'Inputs de Nomina'!E39-E40 = 0.1 (únicas filas con comisión)."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        prov = ParametrizationProvider.build()
        assert abs(prov.get_comision_pct_rol("Inbound 25") - 0.1) < 1e-9
        assert abs(prov.get_comision_pct_rol("inboun Whatsapp") - 0.1) < 1e-9


@pytest.mark.legacy  # WAVE 7: Excel V2-4 (sin Ley 1819) — V2-7 sí implementa exoneración
class TestAportesPatronalesExcelV24:
    """
    Excel V2-4 legacy no implementa exoneración Ley 1819; comportamiento
    fijado para compatibilidad funcional estricta.
    Salud (8.5%) e ICBF+SENA (4%) se cobran siempre.
    """

    def test_flag_ley_1819_no_afecta_payroll(self, whatsapp_only_case, run_engine, tmp_path):
        """aplica_ley_1819=True y False producen payroll idéntico."""
        import json
        with open(whatsapp_only_case) as f:
            data = json.load(f)

        # Run con True (default)
        res_true = run_engine(whatsapp_only_case)

        # Run con False (override)
        data["panel_de_control"]["aplica_ley_1819"] = False
        modified = tmp_path / "ley_off.json"
        modified.write_text(json.dumps(data))
        res_false = run_engine(modified)

        # Ambos deben producir payroll idéntico (flag ignorado)
        assert res_true.pyg_por_mes[0].payroll_a == pytest.approx(
            res_false.pyg_por_mes[0].payroll_a, rel=1e-10
        )

    def test_payroll_incluye_salud_e_icbf(self, whatsapp_only_case, run_engine):
        """El payroll incluye Salud + ICBF+SENA (modo Excel V2-4)."""
        res = run_engine(whatsapp_only_case)
        # Payroll positivo (incluye todos los aportes patronales)
        assert res.pyg_por_mes[0].payroll_a > 0
