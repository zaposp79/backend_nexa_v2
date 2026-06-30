"""Storage constants for parametrization persistence."""
from __future__ import annotations

VERSIONS_INDEX_FILE = "versions.json"
DEFAULT_BACKEND     = "json"

# Environment variable name constants (no os.getenv at import time)
COSMOS_ENV_ENDPOINT   = "COSMOS_ENDPOINT"
COSMOS_ENV_KEY        = "COSMOS_KEY"
COSMOS_ENV_DATABASE   = "COSMOS_DATABASE"
COSMOS_ENV_CONTAINER  = "COSMOS_CONTAINER"

# Default values (static strings — no environment access at module load)
COSMOS_DATABASE_DEFAULT  = "nexa_pricing_db"
COSMOS_CONTAINER_DEFAULT = "parametrization"
COSMOS_PARTITION_KEY     = "/domain"

VALID_DOMAINS = ("gn", "hr", "op")


def get_cosmos_database() -> str:
    """Return the Cosmos database name, resolved at call time.

    Evaluated lazily so monkeypatching in tests works correctly.
    Using this instead of COSMOS_DATABASE_NAME prevents import-time freeze.
    """
    import os
    return os.getenv(COSMOS_ENV_DATABASE, COSMOS_DATABASE_DEFAULT) or COSMOS_DATABASE_DEFAULT


def get_cosmos_container() -> str:
    """Return the Cosmos container name, resolved at call time."""
    import os
    return os.getenv(COSMOS_ENV_CONTAINER, COSMOS_CONTAINER_DEFAULT) or COSMOS_CONTAINER_DEFAULT


# Backward-compat aliases — evaluated once at first import.
# WARNING: monkeypatching COSMOS_DATABASE / COSMOS_CONTAINER after import
# will NOT affect these values. Migrate callers to get_cosmos_database() /
# get_cosmos_container() for correct behavior in tests.
import os as _os
COSMOS_DATABASE_NAME  = _os.getenv(COSMOS_ENV_DATABASE, COSMOS_DATABASE_DEFAULT)
COSMOS_CONTAINER_NAME = _os.getenv(COSMOS_ENV_CONTAINER, COSMOS_CONTAINER_DEFAULT)
del _os

__all__ = [
    "VERSIONS_INDEX_FILE", "DEFAULT_BACKEND",
    "COSMOS_ENV_ENDPOINT", "COSMOS_ENV_KEY", "COSMOS_ENV_DATABASE", "COSMOS_ENV_CONTAINER",
    "COSMOS_DATABASE_DEFAULT", "COSMOS_CONTAINER_DEFAULT",
    "COSMOS_DATABASE_NAME", "COSMOS_CONTAINER_NAME",
    "COSMOS_PARTITION_KEY",
    "VALID_DOMAINS",
    "get_cosmos_database", "get_cosmos_container",
]
