"""Puerto ``DocumentStore``: API de persistencia documental agnóstica al backend.

Esta abstracción es puramente *técnica*: conoce documentos, colecciones,
ids y claves de partición, pero no conoce el dominio de negocio de NEXA.
Los repositorios de dominio (ubicados en ``modules/<capability>/``) dependen
de este puerto y reciben una implementación concreta desde la raíz de composición.

Notas de contrato
-----------------
Los filtros de ``query`` están limitados intencionalmente (FASE 2):
  * solo igualdad,
  * solo campos de primer nivel,
  * combinados con AND lógico.
Rangos, ``LIKE``, ``IN``, ``OR`` y expresiones anidadas quedan fuera del alcance
y deben resolverse dentro del repositorio de dominio.

Semántica de ``upsert``: crea el documento si no existe; si existe, lo
*reemplaza completamente*. No hay merge parcial silencioso.

Paginación: ``list`` y ``query`` retornan ``(documents, continuation_token)``.
Un token ``None`` significa que no hay más páginas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument


class DocumentStore(ABC):
    """Almacén documental abstracto. Implementado por providers JSON y Cosmos.

    Dos APIs coexisten temporalmente:

    * API legacy de dict (`get`, `list`, `query`, `upsert`): espera metadata
      como `id` dentro del dict persistido.
    * API de registro (`get_record`, `list_records`, `query_records`,
      `upsert_record`): mantiene la metadata técnica en `StoredDocument` y
      escribe solo el payload lógico.
    """

    @abstractmethod
    def get_record(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> StoredDocument | None:
        """Retorna un registro almacenado sin inyectar metadata en su payload."""

    @abstractmethod
    def list_records(
        self,
        collection: CollectionConfig,
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[StoredDocument], str | None]:
        """Retorna una página de registros almacenados y un token de continuación."""

    @abstractmethod
    def query_records(
        self,
        collection: CollectionConfig,
        filters: dict[str, object],
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[StoredDocument], str | None]:
        """Retorna registros cuyo payload lógico coincide con filtros de primer nivel."""

    @abstractmethod
    def upsert_record(
        self,
        collection: CollectionConfig,
        record: StoredDocument,
    ) -> StoredDocument:
        """Crea o reemplaza un registro preservando exactamente `record.payload`."""

    @abstractmethod
    def get(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> dict | None:
        """Retorna el documento con ``document_id`` o ``None`` si no existe.

        Lanza:
            DbSerializationError: el documento almacenado está mal formado.
            DbConnectionError: el backend no está disponible.
        """

    @abstractmethod
    def list(
        self,
        collection: CollectionConfig,
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Retorna una página de documentos y un token de continuación, o ``None``."""

    @abstractmethod
    def query(
        self,
        collection: CollectionConfig,
        filters: dict[str, object],
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Retorna documentos que coinciden con ``filters`` (igualdad AND), paginados.

        ``filters`` mapea nombres de campos de primer nivel al valor exacto que
        deben igualar. Un mapping vacío se comporta como :meth:`list`.
        """

    @abstractmethod
    def upsert(
        self,
        collection: CollectionConfig,
        document: dict,
    ) -> dict:
        """Crea o reemplaza completamente ``document``; retorna el documento guardado.

        Lanza:
            DbSerializationError: ``document`` no tiene ``id`` o una clave de
                partición requerida, o no puede serializarse.
        """

    @abstractmethod
    def put_immutable(
        self,
        collection: CollectionConfig,
        record: StoredDocument,
    ) -> StoredDocument:
        """Persiste ``record`` solo si no existe todavía en la colección.

        Garantiza semántica create-only: una vez escrito, el documento no puede
        ser sobreescrito por este método. Usar ``upsert_record`` para escrituras
        mutables.

        Lanza:
            DbConflictError: ya existe un documento con el mismo ``record.id``.
            DbSerializationError: el payload no es serializable.
        """

    @abstractmethod
    def get_snapshot(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> StoredDocument | None:
        """Retorna un snapshot inmutable por id, o ``None`` si no existe.

        Alias semántico de ``get_record`` para colecciones immutables. No impone
        restricciones adicionales sobre el formato del payload.
        """

    @abstractmethod
    def delete(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> None:
        """Elimina un documento.

        Lanza:
            DbNotFoundError: el documento no existe.
        """

    def ping(self) -> None:
        """Lightweight connectivity check for readiness probes.

        Returns None when the store is reachable.
        Raises DbConnectionError (or any Exception) when unavailable.

        Default implementation: no-op (subclasses override for real checks).
        """


__all__ = ["DocumentStore"]
