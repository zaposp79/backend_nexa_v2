"""Provider identifiers and persistence-layer environment variable names.

Centralised here so config, factory and providers agree on the same literals.
"""

from __future__ import annotations

# --- Provider identifiers -------------------------------------------------
PROVIDER_JSON = "json"
PROVIDER_COSMOS = "cosmos"
VALID_PROVIDERS = (PROVIDER_JSON, PROVIDER_COSMOS)
DEFAULT_PROVIDER = PROVIDER_JSON

# --- Environment variable names -------------------------------------------
ENV_DB_PROVIDER = "DB_PROVIDER"
ENV_JSON_STORAGE_PATH = "JSON_STORAGE_PATH"
ENV_COSMOS_ENDPOINT = "COSMOS_ENDPOINT"
ENV_COSMOS_KEY = "COSMOS_KEY"
ENV_COSMOS_DATABASE = "COSMOS_DATABASE"
ENV_COSMOS_CONTAINER = "COSMOS_CONTAINER"

# --- Reserved document fields ---------------------------------------------
# Every persisted document must carry an ``id``. The JSON provider also stamps
# the logical collection name so a document remains self-describing on disk.
FIELD_ID = "id"

__all__ = [
    "PROVIDER_JSON",
    "PROVIDER_COSMOS",
    "VALID_PROVIDERS",
    "DEFAULT_PROVIDER",
    "ENV_DB_PROVIDER",
    "ENV_JSON_STORAGE_PATH",
    "ENV_COSMOS_ENDPOINT",
    "ENV_COSMOS_KEY",
    "ENV_COSMOS_DATABASE",
    "ENV_COSMOS_CONTAINER",
    "FIELD_ID",
]
