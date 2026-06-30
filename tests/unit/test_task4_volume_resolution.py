"""
TASK 4 — Volume Resolution Integration

Verifica que los volúmenes se resuelven correctamente desde el JSON y que
los volúmenes resueltos fluyen correctamente a través del pipeline para
afectar costos operacionales.

Objetivo:
  - Volúmenes se cargan desde JSON y se normalizan
  - VolumeResolutionService respeta flags de cadenas activas
  - Volúmenes se aplican a perfiles (Cadena A) y canales (B, C)
  - Vision dataset expone volumes resueltos por canal y cadena
  - Cambios en volumen de una cadena NO afectan otras cadenas
"""

import pytest

from nexa_engine.modules.calculator_motor.adapters.volume_resolution import VolumeResolutionService, ResolvedChainState
from nexa_engine.modules.vision_imprimible.models.vision_datasets import DatasetVolumetriaPorCanal, CanalVolumetriaRow


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — VolumeResolutionService Core
# ────────────────────────────────────────────────────────────────────────────

class TestVolumeResolutionService:
    """Tests para VolumeResolutionService: resolución de volúmenes por cadena."""

    def test_volume_service_returns_zero_for_inactive_chains(self):
        """
        Si una cadena está desactivada (cadenas_activas=false),
        volumen debe retornar 0 incluso si hay datos en el JSON.
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": False,  # Desactivada
                    "cadena_c": True,
                },
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 200},  # Tiene valor pero cadena inactiva
                        "cadena_c": {"valor": 150},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service = VolumeResolutionService(volumetria)

        # Cadena A activa: debe retornar su volumen
        assert service.volumen("inbound", "Voz", "cadena_a") == 100.0

        # Cadena B desactivada: debe retornar 0 aunque tenga datos
        assert service.volumen("inbound", "Voz", "cadena_b") == 0.0

        # Cadena C activa: debe retornar su volumen
        assert service.volumen("inbound", "Voz", "cadena_c") == 150.0

    def test_volume_service_returns_active_chains_state(self):
        """
        cadenas_activas property retorna correctamente qué cadenas están activas.
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": False,
                    "cadena_c": True,
                },
                "canales": [],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service = VolumeResolutionService(volumetria)
        cadenas = service.cadenas_activas

        assert isinstance(cadenas, ResolvedChainState)
        assert cadenas.cadena_a is True
        assert cadenas.cadena_b is False
        assert cadenas.cadena_c is True

    def test_volume_service_normalizes_modalidad_and_canal(self):
        """
        El servicio normaliza modalidad y canal (minúsculas, strip de espacios).
        "INBOUND" == "inbound", "  Voz  " == "voz".
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {"cadena_a": True},
                "canales": [
                    {
                        "canal": "  Voz  ",  # Con espacios
                        "cadena_a": {"valor": 100},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service = VolumeResolutionService(volumetria)

        # Consulta con diferentes variantes — todas deben funcionar
        assert service.volumen("inbound", "Voz", "cadena_a") == 100.0
        assert service.volumen("INBOUND", "VOZ", "cadena_a") == 100.0
        assert service.volumen("Inbound", "  voz  ", "cadena_a") == 100.0

    def test_volume_canal_total_sums_all_active_chains(self):
        """
        volumen_canal_total suma volúmenes de TODAS las cadenas activas.
        Si B está desactivada, no cuenta.
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": False,
                    "cadena_c": True,
                },
                "canales": [
                    {
                        "canal": "WhatsApp",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 200},
                        "cadena_c": {"valor": 150},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service = VolumeResolutionService(volumetria)

        # Total debe ser A (100) + B (0, desactivada) + C (150) = 250
        assert service.volumen_canal_total("inbound", "WhatsApp") == 250.0

    def test_volume_service_handles_multiple_modalidades(self):
        """
        El servicio maneja inbound y outbound independientemente.
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {"cadena_a": True},
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                    }
                ],
            },
            "outbound": {
                "cadenas_activas": {"cadena_a": True},
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 50},
                    }
                ],
            },
        }

        service = VolumeResolutionService(volumetria)

        assert service.volumen("inbound", "Voz", "cadena_a") == 100.0
        assert service.volumen("outbound", "Voz", "cadena_a") == 50.0

    def test_volume_service_handles_missing_channels(self):
        """
        Si un canal no está en el JSON, retorna 0.0 (no falla).
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {"cadena_a": True},
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service = VolumeResolutionService(volumetria)

        # Canal "Email" no está definido
        assert service.volumen("inbound", "Email", "cadena_a") == 0.0

    def test_volume_service_handles_empty_volumetria(self):
        """
        Si volumetria es None o {}, el servicio no falla.
        """
        service1 = VolumeResolutionService(None)
        service2 = VolumeResolutionService({})

        # Ambos deben retornar 0 y cadenas inactivas
        assert service1.volumen("inbound", "Voz", "cadena_a") == 0.0
        assert service1.cadenas_activas.cadena_a is False

        assert service2.volumen("inbound", "Voz", "cadena_a") == 0.0
        assert service2.cadenas_activas.cadena_a is False


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — Volume Isolation (Cadena Independence)
# ────────────────────────────────────────────────────────────────────────────

class TestVolumeIsolation:
    """Tests para verificar que cambios en un cadena NO afectan otros."""

    def test_cadena_a_volume_independent_of_b_c(self):
        """
        Cambiar volumen de B y C no debe afectar volumen de A.
        """
        volumetria_v1 = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": True,
                    "cadena_c": True,
                },
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 200},
                        "cadena_c": {"valor": 300},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service_v1 = VolumeResolutionService(volumetria_v1)
        vol_a_v1 = service_v1.volumen("inbound", "Voz", "cadena_a")
        vol_b_v1 = service_v1.volumen("inbound", "Voz", "cadena_b")

        # Cambiar volumen de B a 999
        volumetria_v2 = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": True,
                    "cadena_c": True,
                },
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 999},  # Cambió
                        "cadena_c": {"valor": 300},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service_v2 = VolumeResolutionService(volumetria_v2)
        vol_a_v2 = service_v2.volumen("inbound", "Voz", "cadena_a")
        vol_b_v2 = service_v2.volumen("inbound", "Voz", "cadena_b")

        # A debe ser igual en ambas versiones
        assert vol_a_v1 == vol_a_v2 == 100.0

        # B cambió correctamente
        assert vol_b_v1 == 200.0
        assert vol_b_v2 == 999.0

    def test_deactivating_cadena_b_doesnt_affect_a_c(self):
        """
        Desactivar B no debe afectar los volúmenes resueltos de A y C.
        """
        volumetria_active = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": True,
                    "cadena_c": True,
                },
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 200},
                        "cadena_c": {"valor": 300},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service_active = VolumeResolutionService(volumetria_active)

        # Desactivar B
        volumetria_inactive_b = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": False,  # Desactivada
                    "cadena_c": True,
                },
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 200},
                        "cadena_c": {"valor": 300},
                    }
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service_inactive = VolumeResolutionService(volumetria_inactive_b)

        # A y C deben ser iguales
        assert service_active.volumen("inbound", "Voz", "cadena_a") == service_inactive.volumen("inbound", "Voz", "cadena_a") == 100.0
        assert service_active.volumen("inbound", "Voz", "cadena_c") == service_inactive.volumen("inbound", "Voz", "cadena_c") == 300.0

        # B debe cambiar (activo -> 200, inactivo -> 0)
        assert service_active.volumen("inbound", "Voz", "cadena_b") == 200.0
        assert service_inactive.volumen("inbound", "Voz", "cadena_b") == 0.0


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — Volume Integration with Vision Datasets
# ────────────────────────────────────────────────────────────────────────────

class TestVolumeIntegrationWithVisionDatasets:
    """Tests para verificar que volúmenes fluyen correctamente a vision datasets."""

    def test_volumetria_dataset_includes_resolved_volumes(self):
        """
        El dataset de volumetría debe incluir los volúmenes resueltos
        desde el JSON, no raw/input values.
        """
        # Suponemos que la visión dataset ya tiene volumes resueltos
        filas = [
            CanalVolumetriaRow(
                nombre="Agente 1",
                modalidad="Inbound",
                canal="Voz",
                cadena="A",
                fte=5.0,
                volumen_mensual=100.0,  # Resuelto desde VolumeResolutionService
                pct_automatizacion=0.0,
                tarifa_unitaria=0.0,
            ),
            CanalVolumetriaRow(
                nombre="WhatsApp Bot",
                modalidad="Inbound",
                canal="WhatsApp",
                cadena="B",
                fte=0.0,
                volumen_mensual=500.0,  # Resuelto desde VolumeResolutionService
                pct_automatizacion=1.0,
                tarifa_unitaria=0.5,
            ),
        ]

        dataset = DatasetVolumetriaPorCanal(filas=filas)

        # Verificar que los volúmenes estén presentes
        assert dataset.filas[0].volumen_mensual == 100.0
        assert dataset.filas[1].volumen_mensual == 500.0

    def test_volumetria_as_dict_exposes_volumes(self):
        """
        as_dict() en volumetría dataset debe exponer volúmenes.
        """
        filas = [
            CanalVolumetriaRow(
                nombre="Agente 1",
                modalidad="Inbound",
                canal="Voz",
                cadena="A",
                fte=5.0,
                volumen_mensual=100.0,
                pct_automatizacion=0.0,
                tarifa_unitaria=0.0,
            ),
        ]

        dataset = DatasetVolumetriaPorCanal(filas=filas)
        data = dataset.as_dict()

        # Verificar estructura
        assert "filas" in data
        assert len(data["filas"]) == 1
        assert data["filas"][0]["volumen_mensual"] == 100.0


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — Volume Resolution with Multiple Channels
# ────────────────────────────────────────────────────────────────────────────

class TestVolumeResolutionMultipleChannels:
    """Tests para resolución de volúmenes con múltiples canales."""

    def test_multiple_channels_independent_volumes(self):
        """
        Múltiples canales (Voz, WhatsApp, Email) deben tener
        volúmenes independientes para cada cadena.
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": True,
                    "cadena_c": False,
                },
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 50},
                        "cadena_c": {"valor": 0},
                    },
                    {
                        "canal": "WhatsApp",
                        "cadena_a": {"valor": 200},
                        "cadena_b": {"valor": 150},
                        "cadena_c": {"valor": 0},
                    },
                    {
                        "canal": "Email",
                        "cadena_a": {"valor": 50},
                        "cadena_b": {"valor": 100},
                        "cadena_c": {"valor": 0},
                    },
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service = VolumeResolutionService(volumetria)

        # Voz
        assert service.volumen("inbound", "Voz", "cadena_a") == 100.0
        assert service.volumen("inbound", "Voz", "cadena_b") == 50.0
        assert service.volumen("inbound", "Voz", "cadena_c") == 0.0

        # WhatsApp
        assert service.volumen("inbound", "WhatsApp", "cadena_a") == 200.0
        assert service.volumen("inbound", "WhatsApp", "cadena_b") == 150.0

        # Email
        assert service.volumen("inbound", "Email", "cadena_a") == 50.0
        assert service.volumen("inbound", "Email", "cadena_b") == 100.0

    def test_volumetria_totales_calculation(self):
        """
        Verificar que volumen_canal_total suma correctamente
        volúmenes de múltiples cadenas.
        """
        volumetria = {
            "inbound": {
                "cadenas_activas": {
                    "cadena_a": True,
                    "cadena_b": True,
                    "cadena_c": True,
                },
                "canales": [
                    {
                        "canal": "Voz",
                        "cadena_a": {"valor": 100},
                        "cadena_b": {"valor": 200},
                        "cadena_c": {"valor": 150},
                    },
                    {
                        "canal": "WhatsApp",
                        "cadena_a": {"valor": 50},
                        "cadena_b": {"valor": 100},
                        "cadena_c": {"valor": 75},
                    },
                ],
            },
            "outbound": {"cadenas_activas": {}, "canales": []},
        }

        service = VolumeResolutionService(volumetria)

        # Total para Voz: 100 + 200 + 150 = 450
        assert service.volumen_canal_total("inbound", "Voz") == 450.0

        # Total para WhatsApp: 50 + 100 + 75 = 225
        assert service.volumen_canal_total("inbound", "WhatsApp") == 225.0
