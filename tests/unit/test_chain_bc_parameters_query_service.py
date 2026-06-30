from __future__ import annotations

from nexa_engine.modules.cadena_b.services.parameters_query_service import (
    CadenaBParametersQueryService,
)
from nexa_engine.modules.cadena_c.services.parameters_query_service import (
    CadenaCParametersQueryService,
)


class _StubRepo:
    def __init__(self, data: dict) -> None:
        self._data = data

    def get_active_data(self) -> dict:
        return self._data


def _build_op_data() -> dict:
    return {
        "sheets": [
            {
                "key": "dispositivorequerido",
                "catalogs": {
                    "dispositivorequerido": [
                        {"name": "Headset"},
                        {"name": "Laptop"},
                    ]
                },
            }
        ]
    }


def test_chain_b_parameters_allow_missing_hitl_ratio() -> None:
    service = CadenaBParametersQueryService(
        hr_repo=_StubRepo(
            {
                "extra_sheets": {
                    "HR-EquipoHITL": [
                        {"equipohitl": "Human Reviewers"},
                        {"equipohitl": "Conversation Analyst", "ratio": 560},
                    ]
                }
            }
        ),
        op_repo=_StubRepo(_build_op_data()),
    )

    payload = service.get_active_parameters()

    assert [item.nombre for item in payload.dispositivos_requeridos] == ["Headset", "Laptop"]
    assert [item.nombre for item in payload.equipo_hitl] == [
        "Human Reviewers",
        "Conversation Analyst",
    ]
    assert [item.ratio for item in payload.equipo_hitl] == [None, 560]


def test_chain_b_and_c_services_keep_identical_payload_when_ratio_is_missing() -> None:
    hr_data = {
        "extra_sheets": {
            "HR-EquipoHITL": [
                {"equipohitl": "Human Reviewers"},
                {"equipohitl": "Conversation Analyst"},
            ]
        }
    }
    op_data = _build_op_data()

    chain_b = CadenaBParametersQueryService(
        hr_repo=_StubRepo(hr_data),
        op_repo=_StubRepo(op_data),
    ).get_active_parameters()
    chain_c = CadenaCParametersQueryService(
        hr_repo=_StubRepo(hr_data),
        op_repo=_StubRepo(op_data),
    ).get_active_parameters()

    assert chain_b.model_dump() == chain_c.model_dump()
    assert chain_b.model_dump()["equipo_hitl"] == [
        {"nombre": "Human Reviewers", "ratio": None},
        {"nombre": "Conversation Analyst", "ratio": None},
    ]
