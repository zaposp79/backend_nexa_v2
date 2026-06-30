# DB.7.3.1 intento de certificación SDK real `azure-cosmos`

## Resultado

DB.7.3.1 no puede cerrarse en este entorno porque `azure-cosmos` no está
instalado y la instalación desde PyPI falla por resolución DNS.

## Evidencia

Instalación intentada:

```text
venv/bin/python -m pip install 'azure-cosmos>=4.5,<5'
```

Resultado:

```text
Failed to resolve 'pypi.org'
No matching distribution found for azure-cosmos<5,>=4.5
```

Verificación del SDK:

```text
venv/bin/python -m pip show azure-cosmos
Package(s) not found: azure-cosmos
```

Contrato SDK:

```text
tests/db/unit/test_cosmos_sdk_contract.py
4 skipped
reason: azure-cosmos is not installed in this environment
```

Skeleton funcional sin SDK real:

```text
tests/db/unit/test_cosmos_document_store_skeleton.py
9 passed
```

## Estado

| Criterio DB.7.3.1 | Estado |
| ----------------- | ------ |
| Instalar SDK soportado | Bloqueado por red/DNS |
| Ejecutar contrato SDK sin skips | No cumplido |
| No conectar a cuenta Cosmos | Cumplido |
| No activar `DB_PROVIDER=cosmos` | Cumplido |
| JSON default intacto | Cumplido |

## Comando de cierre pendiente

En un entorno con acceso a PyPI o wheel interno:

```bash
venv/bin/python -m pip install 'azure-cosmos>=4.5,<5'
DB_PROVIDER=json PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv/bin/python -m pytest tests/db/unit/test_cosmos_sdk_contract.py -q
```

El criterio de cierre exige:

```text
4 passed, 0 skipped
```

Después ejecutar:

```bash
DB_PROVIDER=json PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv/bin/python -m pytest tests/db tests/parametrizacion/uploads tests/parity -q
```

Y finalmente gate completo contra baseline de node ids.
