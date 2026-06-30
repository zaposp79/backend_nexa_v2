"""
tests/db/contract/test_api_router_modularization.py

Guardrail test para API_ROUTER_MODULARIZATION_PHASE1.

Valida que:
  1. app.py importa router desde modules.api_v1
  2. modules/api_v1/router.py es el router agregador
  3. No hay referencias a antigua ubicación api/v1/
  4. OpenAPI expone rutas esperadas sin cambios
  5. Rutas v1 están disponibles bajo /api/v1
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend_nexa  # noqa: F401
from nexa_engine.app import create_app
from nexa_engine.modules.shared.config.app_settings import AppSettings


class TestApiRouterModularizationPhase1:
    """Validaciones de estructura y estabilidad del router."""

    @pytest.fixture
    def app_settings(self):
        """Settings con docs habilitados para validar OpenAPI."""
        return AppSettings(
            app_env="test",
            docs_enabled=True,
            cors_allowed_origins=("localhost:3000", "localhost:5173"),
            host="127.0.0.1",
            port=8000,
            reload=False,
        )

    @pytest.fixture
    def app(self, app_settings):
        """Crea la app para testing."""
        return create_app(settings=app_settings)

    @pytest.fixture
    def client(self, app):
        """Cliente HTTP para testing."""
        return TestClient(app)

    # ========================================================================
    # Test 1: Router module exists and is importable
    # ========================================================================

    def test_modules_api_v1_router_exists(self):
        """modules/api_v1/router.py debe existir."""
        router_path = Path(__file__).resolve().parents[3] / "modules" / "api_v1" / "router.py"
        assert router_path.exists(), f"Router not found at {router_path}"

    def test_modules_api_v1_router_importable(self):
        """modules.api_v1.router debe ser importable."""
        try:
            from nexa_engine.modules.api_v1.router import router as v1_router
            assert v1_router is not None
        except ImportError as e:
            pytest.fail(f"Cannot import router from modules.api_v1: {e}")

    # ========================================================================
    # Test 2: app.py imports from correct location
    # ========================================================================

    def test_app_imports_router_from_modules_api_v1(self):
        """app.py debe importar router desde modules.api_v1."""
        app_path = Path(__file__).resolve().parents[3] / "app.py"
        app_source = app_path.read_text(encoding="utf-8")

        # Debe contener import desde modules.api_v1
        assert (
            "from .modules.api_v1.router import router as v1_router"
            in app_source
            or "from .modules.api_v1.router import"
            in app_source
        ), "app.py must import router from modules.api_v1"

    # ========================================================================
    # Test 3: Old api/ folder does not exist
    # ========================================================================

    def test_old_api_folder_removed(self):
        """Carpeta api/ en raíz debe no existir."""
        api_path = Path(__file__).resolve().parents[3] / "api"
        assert not api_path.exists(), f"Old api/ folder still exists at {api_path}"

    # ========================================================================
    # Test 4: No references to old api.v1.router remain
    # ========================================================================

    def test_no_old_api_imports_in_codebase(self):
        """No debe haber imports desde antigua ubicación api/."""
        backend_path = Path(__file__).resolve().parents[3]
        this_test_file = Path(__file__).resolve()

        # Search for old import patterns
        old_patterns = [
            "from api.v1",
            "from api import",
            "import api.v1",
            "import api ",
        ]

        found_old_imports = []
        for py_file in backend_path.rglob("*.py"):
            # Exclude this test file (it contains the patterns in its docstring/comments)
            if py_file == this_test_file:
                continue
            if "__pycache__" in py_file.parts or ".pytest_cache" in py_file.parts:
                continue
            source = py_file.read_text(encoding="utf-8")
            for pattern in old_patterns:
                if pattern in source:
                    found_old_imports.append(f"{py_file}: {pattern}")

        assert not found_old_imports, (
            f"Found old api imports: {found_old_imports}"
        )

    # ========================================================================
    # Test 5: Router is properly included in FastAPI app
    # ========================================================================

    def test_v1_router_included_in_app(self, app):
        """Router v1 debe estar incluído en la app."""
        # Check que hay rutas bajo /api/v1
        routes = [route.path for route in app.routes]
        api_v1_routes = [r for r in routes if r.startswith("/api/v1")]
        assert len(api_v1_routes) > 0, "No routes found under /api/v1"

    # ========================================================================
    # Test 6: OpenAPI schema is valid and includes expected endpoints
    # ========================================================================

    def test_openapi_schema_valid(self, client):
        """OpenAPI schema debe ser válido y accesible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200, "OpenAPI schema not accessible"

        schema = response.json()
        assert "paths" in schema, "OpenAPI schema missing paths"
        assert len(schema["paths"]) > 0, "No paths in OpenAPI schema"

    def test_openapi_includes_v1_endpoints(self, client):
        """OpenAPI debe incluir endpoints v1 conocidos."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})

        # Endpoints esperados (sampling of key endpoints)
        expected_paths = [
            "/api/v1/simulation/calculate",
            "/api/v1/simulation/{simulation_id}/results/vision-imprimible",
        ]

        missing_paths = [p for p in expected_paths if p not in paths]
        assert not missing_paths, f"Missing expected paths in OpenAPI: {missing_paths}"

    # ========================================================================
    # Test 7: Health endpoint available
    # ========================================================================

    def test_health_endpoint_available(self, client):
        """Health endpoint debe estar disponible."""
        response = client.get("/health")
        assert response.status_code == 200, "Health endpoint failed"
        data = response.json()
        assert data.get("status") == "ok", "Health check status not ok"

    # ========================================================================
    # Test 8: Multiple module routers are included
    # ========================================================================

    def test_router_includes_multiple_modules(self, client):
        """Router debe incluir sub-routers de múltiples módulos."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})

        # Verificar que hay rutas de diferentes módulos
        module_indicators = {
            "parametrization": "/api/v1/parametrization",
            "simulation": "/api/v1/simulation",
            "audit": "/api/v1/audit",
        }

        for module_name, path_prefix in module_indicators.items():
            module_paths = [p for p in paths if p.startswith(path_prefix)]
            assert (
                len(module_paths) > 0
            ), f"No routes found for {module_name} (expected {path_prefix})"

    # ========================================================================
    # Test 9: No breaking changes to endpoint paths
    # ========================================================================

    def test_calculate_endpoint_exists(self, client):
        """POST /api/v1/simulation/calculate debe existir."""
        response = client.options("/api/v1/simulation/calculate")
        # OPTIONS puede no estar soportado, pero GET/POST deben estar en schema
        schema_response = client.get("/openapi.json")
        schema = schema_response.json()
        paths = schema.get("paths", {})
        assert "/api/v1/simulation/calculate" in paths, "Calculate endpoint not in schema"

    # ========================================================================
    # Test 10: Modular import structure in router.py
    # ========================================================================

    def test_router_aggregator_uses_nexa_engine_imports(self):
        """router.py debe usar imports desde nexa_engine (alias)."""
        router_path = Path(__file__).resolve().parents[3] / "modules" / "api_v1" / "router.py"
        router_source = router_path.read_text(encoding="utf-8")

        # Debe usar nexa_engine alias para imports
        assert (
            "from nexa_engine." in router_source
        ), "router.py should import from nexa_engine (alias)"

        # No debe hacer importes locales relativos (violaba principio)
        assert "from ..modules" not in router_source, (
            "router.py should not use relative imports from ..modules"
        )


__all__ = [
    "TestApiRouterModularizationPhase1",
]
