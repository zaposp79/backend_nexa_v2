"""
nexa_engine/repositories/frozen_parametrization_repository.py
==============================================================
Repositorio para cargar versiones frozen de parametrización desde archivos JSON.

Almacenamiento:
  storage/parametrization/frozen/
    v2-5.json  (futuro)
    v2-6.json  (current)
    v2-7.json  (futuro)
"""

import json
import logging
from pathlib import Path
from typing import Optional

from nexa_engine.modules.shared.config.config import FROZEN_PARAMETRIZATION_DIR
from nexa_engine.modules.parametrizacion.shared.models.frozen_parametrization import FrozenParametrizationV26

logger = logging.getLogger("nexa.frozen_parametrization")


class FrozenParametrizationRepository:
    """
    Repositorio de parametrizaciones congeladas (versionadas).

    Carga desde storage/parametrization/frozen/{version}.json.
    Cada versión es inmutable y auditada.
    """

    # refactor modular-pure (P3a): pasó de repositories/ (1 nivel) a
    # modules/parametrizacion/ (2 niveles); +1 .parent para resolver al MISMO
    # backend_nexa/storage/parametrization/frozen — sin cambio de lógica.
    _STORAGE_DIR = FROZEN_PARAMETRIZATION_DIR  # from config — location-independent

    @classmethod
    def load(cls, version: str = "v2-6") -> Optional[FrozenParametrizationV26]:
        """
        Carga una versión frozen desde storage.

        Args:
            version: Identificador de versión (ej: "v2-6", "v2-7")

        Returns:
            FrozenParametrizationV26 si existe, None si no.

        Raises:
            FileNotFoundError si el archivo no existe y se solicita una versión specific.
            (Solo en modo no-permissive)
        """
        frozen_file = cls._STORAGE_DIR / f"{version}.json"

        if not frozen_file.exists():
            logger.warning(f"[frozen] No frozen parametrization found for {version}")
            return None

        try:
            with open(frozen_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            frozen = FrozenParametrizationV26.from_dict(data)
            logger.info(f"[frozen] Loaded {version} from {frozen_file}")
            return frozen
        except Exception as exc:
            logger.error(f"[frozen] Error loading {version}: {exc}")
            return None

    @classmethod
    def load_latest(cls) -> Optional[FrozenParametrizationV26]:
        """
        Carga la versión frozen más reciente disponible.

        Busca en storage/parametrization/frozen/ y ordena por nombre de archivo.
        """
        if not cls._STORAGE_DIR.exists():
            logger.warning("[frozen] Storage directory does not exist")
            return None

        frozen_files = sorted(cls._STORAGE_DIR.glob("v*.json"), reverse=True)
        if not frozen_files:
            logger.warning("[frozen] No frozen versions found in storage")
            return None

        latest_file = frozen_files[0]
        version = latest_file.stem  # "v2-6" from "v2-6.json"
        logger.info(f"[frozen] Latest frozen version: {version}")
        return cls.load(version)

    @classmethod
    def save(cls, frozen: FrozenParametrizationV26, version: Optional[str] = None) -> Path:
        """
        Persiste una parametrización frozen a storage.

        Args:
            frozen: Instancia de FrozenParametrizationV26
            version: Versión (default: frozen.version)

        Returns:
            Ruta del archivo guardado.
        """
        version = version or frozen.version
        cls._STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        output_file = cls._STORAGE_DIR / f"{version}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(frozen.as_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"[frozen] Saved {version} to {output_file}")
        return output_file

    @classmethod
    def list_versions(cls) -> list:
        """Lista todas las versiones frozen disponibles."""
        if not cls._STORAGE_DIR.exists():
            return []
        files = sorted(cls._STORAGE_DIR.glob("v*.json"))
        return [f.stem for f in files]
