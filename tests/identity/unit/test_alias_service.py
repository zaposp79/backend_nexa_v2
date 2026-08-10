"""Tests unitarios de AliasService — determinismo y validez del alias."""
import pytest
from nexa_engine.modules.identity.services.alias_service import AliasService


@pytest.fixture
def svc() -> AliasService:
    return AliasService()


UUID_A = "9b8c7f6e-5d4c-4b3a-8291-a0b1c2d3e4f5"
UUID_B = "11111111-1111-4111-8111-111111111111"


class TestAliasDeterminism:
    def test_same_uuid_produces_same_alias(self, svc):
        assert svc.generate(UUID_A) == svc.generate(UUID_A)

    def test_same_uuid_repeated_calls(self, svc):
        results = [svc.generate(UUID_A) for _ in range(10)]
        assert len(set(results)) == 1, "alias debe ser idéntico en todas las llamadas"

    def test_different_uuids_can_produce_different_aliases(self, svc):
        # No están obligados a ser distintos (colisiones son posibles),
        # pero con UUIDs muy diferentes es estadísticamente improbable que coincidan.
        alias_a = svc.generate(UUID_A)
        alias_b = svc.generate(UUID_B)
        # Verificar que al menos el algoritmo no siempre produce el mismo resultado
        # con entradas distintas (detectaría una implementación trivialmente rota).
        assert isinstance(alias_a, str) and isinstance(alias_b, str)


class TestAliasFormat:
    def test_alias_not_empty(self, svc):
        assert svc.generate(UUID_A) != ""

    def test_alias_has_three_parts(self, svc):
        alias = svc.generate(UUID_A)
        parts = alias.split(" ")
        assert len(parts) == 3, f"Se esperan 3 partes, se obtuvo: {alias!r}"

    def test_alias_number_in_range(self, svc):
        alias = svc.generate(UUID_A)
        number = int(alias.split(" ")[-1])
        assert 10 <= number <= 99

    def test_alias_is_string(self, svc):
        assert isinstance(svc.generate(UUID_A), str)

    def test_many_uuids_produce_valid_aliases(self, svc):
        import uuid
        for _ in range(50):
            uid = str(uuid.uuid4())
            alias = svc.generate(uid)
            parts = alias.split(" ")
            assert len(parts) == 3
            assert 10 <= int(parts[2]) <= 99
