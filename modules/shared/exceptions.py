"""Domain exceptions for the NEXA simulator backend."""

from typing import Optional, List


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AuditIntegrityError(DomainError):
    """La auditoría o los datasets obligatorios no pudieron generarse."""


class ValidationError(DomainError):
    """Raised when input data fails validation rules."""

    def __init__(self, message: str, field: Optional[str] = None, errors: Optional[List[str]] = None, sim_code: str = "SIM-00506"):
        self.field = field
        self.errors = errors or []
        self.sim_code = sim_code
        super().__init__(message)


class StorageError(DomainError):
    """Raised when a storage read/write operation fails."""

    def __init__(self, message: str, path: Optional[str] = None):
        self.path = path
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str, sim_code: str = "SIM-00600"):
        self.resource = resource
        self.identifier = identifier
        self.sim_code = sim_code
        super().__init__(f"{resource} with id '{identifier}' not found")


class UploadError(DomainError):
    """Raised when a file upload fails validation or processing."""

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        code: str = "UPLOAD_ERROR",
        sim_code: str = "SIM-00700",
    ):
        self.filename = filename
        self.code = code
        self.sim_code = sim_code
        super().__init__(message)


class ParametrizationError(DomainError):
    """Raised when parametrization loading or validation fails."""

    def __init__(self, message: str, module: Optional[str] = None, version_id: Optional[str] = None):
        self.module = module
        self.version_id = version_id
        super().__init__(message)


class ParametrizationNotFoundError(NotFoundError):
    """Raised when a parametrization version or module does not exist."""

    def __init__(self, module: str, version_id: Optional[str] = None):
        resource = f"Parametrization {module}"
        identifier = version_id or "active"
        self.module = module
        self.version_id = version_id
        super().__init__(resource, identifier, sim_code="SIM-00602")


class StrictExcelModeError(DomainError):
    """Raised when strict_mode=True and the engine encounters a condition
    that Excel would handle explicitly but our engine would silently ignore."""

    def __init__(self, message: str, component: str = "", detail: str = ""):
        self.component = component
        self.detail = detail
        super().__init__(message)


class LocalityNotFoundError(DomainError):
    """Raised when a requested locality does not exist in parametrization."""

    def __init__(self, module: str, localidad: str):
        self.module = module
        self.localidad = localidad
        super().__init__(f"Locality '{localidad}' not found in {module} parametrization")
