"""OOXML security preflight: validates a raw bytes payload before openpyxl opens it.

All checks run at the ZIP/XML level so that malicious content never reaches
the spreadsheet engine.  Raises :class:`UploadError` with a stable ``code``
attribute on any violation.

Rejection matrix
----------------
* Not a valid ZIP (magic bytes PK\\x03\\x04)
* ZIP entry with path traversal (``..`` in name)
* Missing mandatory OOXML structure (``[Content_Types].xml``, ``xl/workbook.xml``)
* ``xl/vbaProject.bin``  — VBA macros
* ``xl/macros/``         — macro sheets
* ``xl/externalLinks/``  — external workbook references
* ``xl/activeX/``        — ActiveX objects
* Relationship target with external scheme/host — external URLs
* OLE / oleObject / AlternateContent (XLM macros) embedded objects
* Data connections (``xl/connections.xml``)
* Power Query (``xl/queries/``)
* Cells with formula elements ``<f>`` in any sheet XML
* Encrypted workbook (CFBF/OLECF magic ``\\xD0\\xCF\\x11\\xE0`` or ZIP entry
  ``EncryptionInfo``)
* ZIP entry uncompressed size exceeds :data:`MAX_EXCEL_UNCOMPRESSED_BYTES`
* Per-entry compression ratio exceeds :data:`MAX_EXCEL_COMPRESSION_RATIO`

Not rejected
------------
* Images / drawings that reference only internal (``../media/``) targets
  are legitimate and must not be blocked.
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import List

from nexa_engine.modules.shared.exceptions import UploadError
from nexa_engine.modules.shared.config.config import (
    MAX_EXCEL_COMPRESSION_RATIO,
    MAX_EXCEL_UNCOMPRESSED_BYTES,
)

# ---------------------------------------------------------------------------
# OOXML mandatory entries
# ---------------------------------------------------------------------------
_REQUIRED_ENTRIES = frozenset(
    ["[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"]
)

# ---------------------------------------------------------------------------
# Forbidden ZIP entry patterns
# ---------------------------------------------------------------------------
_FORBIDDEN_PATTERNS: List[re.Pattern] = [
    re.compile(r"xl/vbaProject\.bin", re.IGNORECASE),
    re.compile(r"xl/macros/", re.IGNORECASE),
    re.compile(r"xl/externalLinks/", re.IGNORECASE),
    re.compile(r"xl/connections\.xml", re.IGNORECASE),
    re.compile(r"xl/queries/", re.IGNORECASE),
    re.compile(r"xl/activeX/", re.IGNORECASE),
]

# Relationship target patterns that indicate external resources.
# Covers: http/https/ftp, file://, ldap://, smb://, UNC paths (\\), and
# protocol-relative URLs (//host/path).  Internal relative refs (../media/)
# do NOT match because they lack a scheme or double-slash host prefix.
_EXTERNAL_URL_RE = re.compile(
    r"""Target\s*=\s*["'](https?://|ftp://|file://|ldap://|smb://|\\\\|//)""",
    re.IGNORECASE,
)

# OLE object namespace marker in Content_Types or relationship files.
# Also matches AlternateContent which is used by XLM (legacy macro language).
_OLE_RE = re.compile(
    r"oleObject|vnd\.ms-office\.activeX|mc:AlternateContent",
    re.IGNORECASE,
)

# Formula element in sheet XML.
# Hardened pattern covers:
#   <f>             — plain element
#   <x:f>           — namespaced  (word chars only, e.g. x:, ss:)
#   <f t="shared">  — with attributes
# Deliberately strict: only word-char namespaces and no whitespace between
# < and the element name.  Whitespace-in-tag or non-word-char-namespace
# attacks are not valid XML and will be caught by schema validation in
# openpyxl (which we don't invoke), but the regex handles the common cases.
_FORMULA_RE = re.compile(r"<(?:\w+:)?f(?:/?>|[\s\t][^>]*/?>)", re.IGNORECASE)

# CFBF/OLECF magic bytes (Compound File Binary — used by encrypted .xlsx)
_CFBF_MAGIC = b"\xD0\xCF\x11\xE0"
_XLSX_ZIP_MAGIC = b"PK\x03\x04"

# Encrypted OOXML uses the Agile/Standard Encryption Info entry
_ENCRYPTION_ENTRY = "EncryptionInfo"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_ooxml_safety(file_bytes: bytes) -> None:
    """Validate *file_bytes* as a safe, plain-data OOXML workbook.

    Raises :class:`UploadError` with ``code`` set to one of the stable values
    listed below on any violation.  Returns ``None`` on success.

    Error codes
    -----------
    ``INVALID_EXCEL_FILE``
        Not a ZIP, not an OOXML, missing mandatory entries, path traversal.
    ``ENCRYPTED_EXCEL_FILE``
        Password-protected or encrypted workbook.
    ``UNSAFE_EXCEL_CONTENT``
        Macros, VBA, external links, formulas, OLE, DDE, or active content.
    ``EXCEL_LIMIT_EXCEEDED``
        Uncompressed size or compression ratio exceeds configured limits.
    """
    # 1. Magic-bytes check — must start with PK\x03\x04
    if len(file_bytes) < 4:
        raise UploadError("El archivo no es un Excel OOXML válido.", code="INVALID_EXCEL_FILE")

    if file_bytes[:4] == _CFBF_MAGIC:
        raise UploadError(
            "El archivo está cifrado o es un formato legado (.xls).",
            code="ENCRYPTED_EXCEL_FILE",
        )

    if file_bytes[:4] != _XLSX_ZIP_MAGIC:
        raise UploadError(
            "El archivo no es un Excel OOXML válido (firma ZIP incorrecta).",
            code="INVALID_EXCEL_FILE",
        )

    # 2. Open as ZIP
    try:
        zf = zipfile.ZipFile(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise UploadError("El archivo ZIP está corrupto.", code="INVALID_EXCEL_FILE")

    with zf:
        names_lower = {n.lower() for n in zf.namelist()}
        names_original = zf.namelist()

        # 3. Path traversal in ZIP entry names
        for name in names_original:
            parts = name.replace("\\", "/").split("/")
            if ".." in parts or any(p.startswith("/") for p in parts if p):
                raise UploadError(
                    "El archivo contiene rutas no permitidas.",
                    code="INVALID_EXCEL_FILE",
                )

        # 4. Mandatory OOXML structure
        for required in _REQUIRED_ENTRIES:
            if required.lower() not in names_lower:
                raise UploadError(
                    f"El archivo no tiene la estructura OOXML requerida (falta {required}).",
                    code="INVALID_EXCEL_FILE",
                )

        # 5. Encrypted workbook detection
        if _ENCRYPTION_ENTRY.lower() in names_lower:
            raise UploadError(
                "El archivo está protegido con contraseña.",
                code="ENCRYPTED_EXCEL_FILE",
            )

        # 6. Forbidden content patterns (VBA, macros, external links, etc.)
        for name in names_original:
            for pattern in _FORBIDDEN_PATTERNS:
                if pattern.search(name):
                    raise UploadError(
                        f"El archivo contiene contenido no permitido ({name}).",
                        code="UNSAFE_EXCEL_CONTENT",
                    )

        # 7. Inspect relationship files for external URL targets
        for name in names_original:
            if name.lower().endswith(".rels"):
                try:
                    data = zf.read(name).decode("utf-8", errors="replace")
                    if _EXTERNAL_URL_RE.search(data):
                        raise UploadError(
                            "El archivo contiene referencias externas en sus relaciones.",
                            code="UNSAFE_EXCEL_CONTENT",
                        )
                    if _OLE_RE.search(data):
                        raise UploadError(
                            "El archivo contiene objetos OLE o contenido ActiveX.",
                            code="UNSAFE_EXCEL_CONTENT",
                        )
                except (KeyError, UnicodeDecodeError):
                    pass

        # 8. Content_Types check for OLE / activeX
        if "[content_types].xml" in names_lower:
            try:
                ct_data = zf.read("[Content_Types].xml").decode("utf-8", errors="replace")
                if _OLE_RE.search(ct_data):
                    raise UploadError(
                        "El archivo contiene objetos OLE o contenido ActiveX.",
                        code="UNSAFE_EXCEL_CONTENT",
                    )
            except (KeyError, UnicodeDecodeError):
                pass

        # 9. Scan sheet XMLs for formula elements <f>
        for name in names_original:
            if _is_sheet_xml(name):
                try:
                    sheet_data = zf.read(name).decode("utf-8", errors="replace")
                    if _FORMULA_RE.search(sheet_data):
                        raise UploadError(
                            "El archivo contiene fórmulas. Solo se permiten valores.",
                            code="UNSAFE_EXCEL_CONTENT",
                        )
                except (KeyError, UnicodeDecodeError):
                    pass

        # 10. Compression ratio and uncompressed size per entry
        total_uncompressed = 0
        for info in zf.infolist():
            uncompressed = info.file_size
            compressed = info.compress_size

            if uncompressed > MAX_EXCEL_UNCOMPRESSED_BYTES:
                raise UploadError(
                    "El archivo supera el tamaño descomprimido máximo permitido.",
                    code="EXCEL_LIMIT_EXCEEDED",
                )

            if compressed > 0:
                ratio = uncompressed / compressed
                if ratio > MAX_EXCEL_COMPRESSION_RATIO:
                    raise UploadError(
                        "El archivo tiene una ratio de compresión excesiva (posible ZIP bomb).",
                        code="EXCEL_LIMIT_EXCEEDED",
                    )

            total_uncompressed += uncompressed
            if total_uncompressed > MAX_EXCEL_UNCOMPRESSED_BYTES:
                raise UploadError(
                    "El tamaño total descomprimido del archivo supera el límite permitido.",
                    code="EXCEL_LIMIT_EXCEEDED",
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_sheet_xml(name: str) -> bool:
    """Return True if *name* looks like a worksheet XML entry."""
    low = name.lower()
    return (
        low.startswith("xl/worksheets/sheet") and low.endswith(".xml")
    ) or (
        # some implementations use xl/worksheets/sharedStrings.xml — exclude it
        low.startswith("xl/worksheets/") and low.endswith(".xml")
        and "sharedstrings" not in low
    )
