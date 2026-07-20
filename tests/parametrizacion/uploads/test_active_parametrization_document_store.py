from __future__ import annotations

import inspect

import pytest

from nexa_engine.modules.parametrizacion.gn.repositories.gn_active_parametrization_repository import (
    GNActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
    HRActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
    OPActiveParametrizationRepository,
)


@pytest.mark.parametrize(
    "repository_cls",
    [
        GNActiveParametrizationRepository,
        HRActiveParametrizationRepository,
        OPActiveParametrizationRepository,
    ],
)
def test_active_repositories_use_query_as_primary_route(repository_cls: type) -> None:
    """Active repos must call self._store.query() to look up the active parametrization.

    The legacy get_record() + filesystem fallback path was removed when the repositories
    were updated to use query(domain=X, status='active') directly, which works with both
    Cosmos and the JSON document store.
    """
    source = inspect.getsource(repository_cls.get_active_data)

    assert "self._store.query(" in source
    assert "self._store.get(" not in source
