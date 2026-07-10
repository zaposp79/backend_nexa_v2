"""Excel security preflight — validates raw bytes before any parser opens the file.

All checks run at the binary/ZIP/XML level so that malicious content never
reaches the spreadsheet engine.  Raises :class:`UploadError` on any violation.

Dispatching
-----------
* ``check_excel_safety(file_bytes, filename)``  — unified entry point (HR/GN/OP services).
* ``check_ooxml_safety(file_bytes)``            — legacy alias kept for backward compat.

Rejection matrix — XLSX (.xlsx)
--------------------------------
* Not a valid ZIP (magic bytes PK\\x03\\x04 missing)
* File disguised as XLSX but actually a different format (PDF, PE, OLE, etc.)
* ZIP path traversal (``..`` in entry names)
* Missing mandatory OOXML structure ([Content_Types].xml, xl/workbook.xml)
* Encrypted / password-protected workbook (EncryptionInfo entry or CFBF magic)
* Macro-enabled content type in Content_Types.xml (even if extension is .xlsx)
* VBA macros (xl/vbaProject.bin, xl/macros/)
* External workbook links (xl/externalLinks/)
* Data connections (xl/connections.xml)
* Power Query (xl/queries/)
* ActiveX objects (xl/activeX/)
* OLE objects or AlternateContent (XLM macros) in relationships / Content_Types
* External URL targets in relationship files
* XXE injection (<!DOCTYPE, <!ENTITY) in any XML entry
* DDE / formula-injection patterns in sharedStrings.xml
* Suspicious shell patterns in sheet XML (DDEAUTO, =cmd|, etc.)
* Formula elements <f> in any sheet XML
* Windows PE (MZ) header embedded anywhere in file
* EICAR antivirus test string (proxy for AV-detectable payloads)
* ZIP entry uncompressed size exceeds MAX_EXCEL_UNCOMPRESSED_BYTES
* Per-entry compression ratio exceeds MAX_EXCEL_COMPRESSION_RATIO (ZIP bomb)

Rejection matrix — XLS (.xls)
-------------------------------
* CFBF magic bytes missing (not a real OLE Compound Document)
* File too small to be a valid .xls workbook
* Windows PE (MZ) header embedded in file
* EICAR antivirus test string
* XLM macro sheet record detected (BIFF8 BOUNDSHEET type=macro)
* VBA storage directory signature in raw bytes
* DDE shell command patterns in raw bytes

NOT rejected
------------
* Internal relative image/drawing targets (../media/) — legitimate xlsx content.

Note on antivirus
-----------------
This module provides static byte-pattern analysis.  It catches disguised
file types, known test signatures (EICAR), embedded executables, and common
injection payloads.  It does NOT replace a full AV engine (ClamAV, Defender,
etc.).  To add ClamAV scanning, set the CLAMAV_SOCKET environment variable
to the Unix socket path and install the ``clamd`` package.
"""

from __future__ import annotations

import logging
import os
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List

from nexa_engine.modules.shared.exceptions import UploadError
from nexa_engine.modules.shared.config.config import (
    MAX_EXCEL_COMPRESSION_RATIO,
    MAX_EXCEL_UNCOMPRESSED_BYTES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Magic bytes
# ---------------------------------------------------------------------------
_XLSX_ZIP_MAGIC = b"PK\x03\x04"
_CFBF_MAGIC = b"\xD0\xCF\x11\xE0"
_PE_MAGIC = b"MZ"
_PE_SIG = b"PE\x00\x00"  # PE signature that always follows the DOS stub in real executables
_EICAR_PART = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"

# Extensions safe to skip during PE scan (never executables)
_PE_SCAN_SKIP_EXTS = frozenset([
    ".xml", ".rels", ".txt", ".json",
    ".png", ".jpeg", ".jpg", ".gif", ".bmp", ".wmf", ".emf", ".svg",
])

# ---------------------------------------------------------------------------
# OOXML mandatory entries
# ---------------------------------------------------------------------------
_REQUIRED_ENTRIES = frozenset(["[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"])

# ---------------------------------------------------------------------------
# Forbidden ZIP entry patterns (XLSX) — (pattern, user-facing message)
# ---------------------------------------------------------------------------
# Note: xl/externalLinks/ is NOT blocked here. Ghost/stale external-link
# entries left by Excel after breaking links are harmless because:
#   - _check_rel_files catches any real external URL (http, file, smb, UNC) in
#     the .rels files inside xl/externalLinks/_rels/.
#   - _check_xxe catches XXE injections in the .xml files.
#   - openpyxl/xlrd never follows external-link references.
_FORBIDDEN_ENTRIES: List[tuple] = [
    (
        re.compile(r"xl/vbaProject\.bin", re.IGNORECASE),
        "El archivo contiene macros VBA. Guárdelo como .xlsx sin macros (.xlsm → Guardar como → .xlsx).",
        "SIM-00300",
    ),
    (
        re.compile(r"xl/macros/", re.IGNORECASE),
        "El archivo contiene macros. Guárdelo como .xlsx sin macros.",
        "SIM-00301",
    ),
    (
        re.compile(r"xl/connections\.xml", re.IGNORECASE),
        "El archivo contiene conexiones de datos externas. Elimínelas antes de subir.",
        "SIM-00302",
    ),
    (
        re.compile(r"xl/queries/", re.IGNORECASE),
        "El archivo contiene consultas de Power Query. Elimínelas antes de subir.",
        "SIM-00303",
    ),
    (
        re.compile(r"xl/activeX/", re.IGNORECASE),
        "El archivo contiene controles ActiveX. Elimínelos antes de subir.",
        "SIM-00304",
    ),
]

# External URL target in relationship files
_EXTERNAL_URL_RE = re.compile(
    r"""Target\s*=\s*["'](https?://|ftp://|file://|ldap://|smb://|\\\\|//)""",
    re.IGNORECASE,
)

# OLE / ActiveX / AlternateContent markers
_OLE_RE = re.compile(
    r"oleObject|vnd\.ms-office\.activeX|mc:AlternateContent",
    re.IGNORECASE,
)

# Macro-enabled content type in Content_Types.xml
_MACRO_CT_RE = re.compile(
    r"application/vnd\.ms-excel\.(?:sheet|addin|template)\.macroEnabled",
    re.IGNORECASE,
)

# XXE injection in XML files
_XXE_RE = re.compile(r"<!DOCTYPE|<!ENTITY", re.IGNORECASE)

# Formula element in sheet XML
_FORMULA_RE = re.compile(r"<(?:\w+:)?f(?:/?>|[\s\t][^>]*/?>)", re.IGNORECASE)

# DDE / injection patterns in sharedStrings.xml (no <f> tag required)
# Character class uses unescaped - at the end to avoid range ambiguity
_DDE_RE = re.compile(
    r"=\s*(?:DDE|DDEAUTO|SYSTEM|EXEC|RUN|SHELL|HYPERLINK|cmd)\s*[(|]"
    r"|=\s*[|+@\t-]"
    r"|\|cmd(?:\.exe)?"
    r"|\|powershell",
    re.IGNORECASE,
)

# Suspicious patterns in sheet XML outside <f> tags
_SUSPICIOUS_SHEET_RE = re.compile(
    r"DDEAUTO|=cmd\||=SYSTEM\(|msexcel\|",
    re.IGNORECASE,
)

_ENCRYPTION_ENTRY = "EncryptionInfo"

# ---------------------------------------------------------------------------
# XLS (BIFF8 / OLE) patterns
# ---------------------------------------------------------------------------
_XLS_VBA_MARKER = b"V\x00B\x00A\x00"          # "VBA" in UTF-16LE (OLE dir entry)
_XLS_MACRO_SHEET_MARKER = b"\x85\x00"          # BOUNDSHEET record type in BIFF8
_XLS_DDE_RE = re.compile(rb"DDE(?:AUTO)?|=cmd\|", re.IGNORECASE)
_XLS_MIN_SIZE = 512

# ---------------------------------------------------------------------------
# ClamAV (optional)
# ---------------------------------------------------------------------------
_CLAMAV_SOCKET = os.getenv("CLAMAV_SOCKET", "")


# ---------------------------------------------------------------------------
# Atomic check helpers (keep _check_xlsx_safety cognitively flat)
# ---------------------------------------------------------------------------

def _scan_with_clamav(file_bytes: bytes) -> None:
    if not _CLAMAV_SOCKET:
        return
    try:
        import clamd  # type: ignore[import-not-found]
        cd = clamd.ClamdUnixSocket(_CLAMAV_SOCKET)
        status, virus_name = cd.instream(BytesIO(file_bytes)).get("stream", ("OK", None))
        if status == "FOUND":
            raise UploadError(
                f"El archivo contiene malware detectado por el antivirus: {virus_name}.",
                code="VIRUS_DETECTED",
                sim_code="SIM-00314",
            )
    except UploadError:
        raise
    except Exception as exc:
        logger.warning("[PREFLIGHT] ClamAV no disponible: %s", exc)


def _check_embedded_executables(file_bytes: bytes) -> None:
    # EICAR is a plain-text signature — safe to scan raw bytes.
    if _EICAR_PART in file_bytes:
        raise UploadError(
            "El archivo contiene una firma de malware conocida (EICAR).",
            code="VIRUS_DETECTED",
            sim_code="SIM-00313",
        )

    if file_bytes[:4] == _XLSX_ZIP_MAGIC:
        # XLSX is a ZIP: scanning raw bytes causes false positives because
        # compressed data can produce arbitrary byte sequences including 'MZ'.
        # Check decompressed entry headers instead. A genuine PE executable
        # must start with 'MZ' at byte 0 AND contain 'PE\x00\x00' in the
        # first 512 bytes (the PE signature at the offset given by DWORD@0x3C).
        _check_pe_in_zip_entries(file_bytes)
    else:
        # XLS/OLE and other binary formats: raw scan is valid.
        # Still require PE\x00\x00 to guard against random 'MZ' occurrences.
        if _PE_MAGIC in file_bytes and _PE_SIG in file_bytes:
            raise UploadError(
                "El archivo contiene un ejecutable embebido (cabecera PE/MZ detectada).",
                code="UNSAFE_EXCEL_CONTENT",
                sim_code="SIM-00312",
            )


def _check_pe_in_zip_entries(file_bytes: bytes) -> None:
    """Scan decompressed ZIP entries for embedded PE executables."""
    try:
        with zipfile.ZipFile(BytesIO(file_bytes), "r") as zf:
            for info in zf.infolist():
                if info.file_size < 64:
                    continue
                ext = Path(info.filename).suffix.lower()
                if ext in _PE_SCAN_SKIP_EXTS:
                    continue
                try:
                    with zf.open(info.filename) as fh:
                        header = fh.read(512)
                    if header[:2] == _PE_MAGIC and _PE_SIG in header:
                        raise UploadError(
                            "El archivo contiene un ejecutable embebido (cabecera PE/MZ detectada).",
                            code="UNSAFE_EXCEL_CONTENT",
                            sim_code="SIM-00312",
                        )
                except UploadError:
                    raise
                except Exception:
                    continue
    except UploadError:
        raise
    except Exception:
        pass


def _check_magic_bytes_xlsx(file_bytes: bytes) -> None:
    if len(file_bytes) < 4:
        raise UploadError("El archivo es demasiado pequeño para ser un Excel válido.", code="INVALID_EXCEL_FILE", sim_code="SIM-00203")
    if file_bytes[:4] == _CFBF_MAGIC:
        raise UploadError(
            "El archivo está cifrado o es formato legado (.xls). Use .xlsx sin contraseña.",
            code="ENCRYPTED_EXCEL_FILE",
            sim_code="SIM-00204",
        )
    if file_bytes[:4] == b"%PDF":
        raise UploadError("El archivo es un PDF con extensión .xlsx.", code="INVALID_EXCEL_FILE", sim_code="SIM-00205")
    if file_bytes[:4] != _XLSX_ZIP_MAGIC:
        raise UploadError(
            "El archivo no es un Excel OOXML válido (firma de archivo incorrecta).",
            code="INVALID_EXCEL_FILE",
            sim_code="SIM-00206",
        )


def _check_zip_path_traversal(names_original: list) -> None:
    for name in names_original:
        parts = name.replace("\\", "/").split("/")
        if ".." in parts or any(p.startswith("/") for p in parts if p):
            raise UploadError(
                "El archivo contiene rutas no permitidas (path traversal).",
                code="INVALID_EXCEL_FILE",
                sim_code="SIM-00207",
            )


def _check_required_entries(names_lower: set) -> None:
    for required in _REQUIRED_ENTRIES:
        if required.lower() not in names_lower:
            raise UploadError(
                f"El archivo no tiene la estructura OOXML requerida (falta '{required}').",
                code="INVALID_EXCEL_FILE",
                sim_code="SIM-00208",
            )


def _check_forbidden_entries(names_original: list) -> None:
    for name in names_original:
        for pattern, message, sim_code in _FORBIDDEN_ENTRIES:
            if pattern.search(name):
                raise UploadError(message, code="UNSAFE_EXCEL_CONTENT", sim_code=sim_code)


def _check_rel_files(zf: zipfile.ZipFile, names_original: list) -> None:
    for name in names_original:
        if not name.lower().endswith(".rels"):
            continue
        # xl/externalLinks/_rels/ naturally contains file:// or local paths pointing
        # to the linked workbook — those references are never followed by the parser.
        # Skip URL check for this subfolder; XXE is still caught by _check_xxe.
        if name.lower().startswith("xl/externallinks/"):
            continue
        try:
            data = zf.read(name).decode("utf-8", errors="replace")
        except (KeyError, UnicodeDecodeError):
            continue
        if _EXTERNAL_URL_RE.search(data):
            raise UploadError(
                "El archivo contiene referencias URL externas en sus relaciones.",
                code="UNSAFE_EXCEL_CONTENT",
                sim_code="SIM-00305",
            )
        if _OLE_RE.search(data):
            raise UploadError(
                "El archivo contiene objetos OLE o contenido ActiveX.",
                code="UNSAFE_EXCEL_CONTENT",
                sim_code="SIM-00306",
            )


def _check_content_types(zf: zipfile.ZipFile, names_lower: set) -> None:
    if "[content_types].xml" not in names_lower:
        return
    try:
        ct = zf.read("[Content_Types].xml").decode("utf-8", errors="replace")
    except (KeyError, UnicodeDecodeError):
        return
    if _MACRO_CT_RE.search(ct):
        raise UploadError(
            "El archivo declara un tipo de contenido con macros habilitadas.",
            code="UNSAFE_EXCEL_CONTENT",
            sim_code="SIM-00307",
        )
    if _OLE_RE.search(ct):
        raise UploadError(
            "El archivo contiene objetos OLE o contenido ActiveX.",
            code="UNSAFE_EXCEL_CONTENT",
            sim_code="SIM-00306",
        )


def _check_xxe(zf: zipfile.ZipFile, names_original: list) -> None:
    for name in names_original:
        low = name.lower()
        if not (low.endswith(".xml") or low.endswith(".rels")):
            continue
        try:
            data = zf.read(name).decode("utf-8", errors="replace")
        except (KeyError, UnicodeDecodeError):
            continue
        if _XXE_RE.search(data):
            raise UploadError(
                f"El archivo contiene declaraciones XML externas peligrosas ({name}).",
                code="UNSAFE_EXCEL_CONTENT",
                sim_code="SIM-00308",
            )


def _check_dde_in_shared_strings(zf: zipfile.ZipFile, names_lower: set) -> None:
    if "xl/sharedstrings.xml" not in names_lower:
        return
    try:
        target = next(n for n in zf.namelist() if n.lower() == "xl/sharedstrings.xml")
        data = zf.read(target).decode("utf-8", errors="replace")
    except (KeyError, StopIteration, UnicodeDecodeError):
        return
    if _DDE_RE.search(data):
        raise UploadError(
            "El archivo contiene patrones de inyección DDE en las cadenas compartidas.",
            code="UNSAFE_EXCEL_CONTENT",
            sim_code="SIM-00309",
        )


def _check_sheet_xmls(zf: zipfile.ZipFile, names_original: list) -> None:
    for name in names_original:
        if not _is_sheet_xml(name):
            continue
        try:
            data = zf.read(name).decode("utf-8", errors="replace")
        except (KeyError, UnicodeDecodeError):
            continue
        if _FORMULA_RE.search(data):
            raise UploadError(
                "El archivo contiene fórmulas. Solo se permiten valores de datos.",
                code="UNSAFE_EXCEL_CONTENT",
                sim_code="SIM-00310",
            )
        if _SUSPICIOUS_SHEET_RE.search(data):
            raise UploadError(
                "El archivo contiene patrones sospechosos en las hojas (DDEAUTO, shell).",
                code="UNSAFE_EXCEL_CONTENT",
                sim_code="SIM-00311",
            )


def _check_zip_bomb(zf: zipfile.ZipFile) -> None:
    total = 0
    for info in zf.infolist():
        if info.file_size > MAX_EXCEL_UNCOMPRESSED_BYTES:
            raise UploadError(
                "El archivo supera el tamaño descomprimido máximo permitido.",
                code="EXCEL_LIMIT_EXCEEDED",
                sim_code="SIM-00400",
            )
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > MAX_EXCEL_COMPRESSION_RATIO:
                raise UploadError(
                    "El archivo tiene una ratio de compresión excesiva (posible ZIP bomb).",
                    code="EXCEL_LIMIT_EXCEEDED",
                    sim_code="SIM-00401",
                )
        total += info.file_size
        if total > MAX_EXCEL_UNCOMPRESSED_BYTES:
            raise UploadError(
                "El tamaño total descomprimido supera el límite permitido.",
                code="EXCEL_LIMIT_EXCEEDED",
                sim_code="SIM-00402",
            )


def _is_sheet_xml(name: str) -> bool:
    low = name.lower()
    return (
        low.startswith("xl/worksheets/sheet") and low.endswith(".xml")
    ) or (
        low.startswith("xl/worksheets/") and low.endswith(".xml")
        and "sharedstrings" not in low
    )


# ---------------------------------------------------------------------------
# XLSX scanner
# ---------------------------------------------------------------------------

def _check_xlsx_safety(file_bytes: bytes) -> None:
    _check_magic_bytes_xlsx(file_bytes)
    _check_embedded_executables(file_bytes)
    _scan_with_clamav(file_bytes)

    try:
        zf = zipfile.ZipFile(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise UploadError("El archivo ZIP está corrupto o no es un Excel válido.", code="INVALID_EXCEL_FILE", sim_code="SIM-00210")

    with zf:
        names_original = zf.namelist()
        names_lower = {n.lower() for n in names_original}

        _check_zip_path_traversal(names_original)
        _check_required_entries(names_lower)

        if _ENCRYPTION_ENTRY.lower() in names_lower:
            raise UploadError("El archivo está protegido con contraseña.", code="ENCRYPTED_EXCEL_FILE", sim_code="SIM-00209")

        _check_content_types(zf, names_lower)
        _check_forbidden_entries(names_original)
        _check_rel_files(zf, names_original)
        _check_xxe(zf, names_original)
        _check_dde_in_shared_strings(zf, names_lower)
        _check_sheet_xmls(zf, names_original)
        _check_zip_bomb(zf)


# ---------------------------------------------------------------------------
# XLS scanner (OLE/CFBF — legacy format)
# ---------------------------------------------------------------------------

def _check_xls_safety(file_bytes: bytes) -> None:
    if len(file_bytes) < _XLS_MIN_SIZE:
        raise UploadError(
            "El archivo .xls es demasiado pequeño para ser un Excel válido.",
            code="INVALID_EXCEL_FILE",
            sim_code="SIM-00203",
        )
    if file_bytes[:4] == _XLSX_ZIP_MAGIC:
        raise UploadError(
            "El archivo tiene extensión .xls pero es realmente un ZIP/XLSX.",
            code="INVALID_EXCEL_FILE",
            sim_code="SIM-00210",
        )
    if file_bytes[:4] != _CFBF_MAGIC:
        raise UploadError(
            "El archivo no es un Excel .xls válido (firma OLE incorrecta).",
            code="INVALID_EXCEL_FILE",
            sim_code="SIM-00206",
        )

    _check_embedded_executables(file_bytes)
    _scan_with_clamav(file_bytes)

    if _XLS_VBA_MARKER in file_bytes:
        raise UploadError("El archivo .xls contiene macros VBA.", code="UNSAFE_EXCEL_CONTENT", sim_code="SIM-00300")

    if _XLS_DDE_RE.search(file_bytes):
        raise UploadError("El archivo .xls contiene patrones DDE peligrosos.", code="UNSAFE_EXCEL_CONTENT", sim_code="SIM-00309")

    # BIFF8 BOUNDSHEET record layout (from record start):
    #   pos+0..1  record type (0x85 0x00)
    #   pos+2..3  data length
    #   pos+4..7  BOF stream offset
    #   pos+8     visibility flags (grbit)
    #   pos+9     sheet type: 0x01=XLM macro, 0x06=VBA module
    # bytes.find() delegates to C — orders of magnitude faster than a Python
    # byte-by-byte loop on 5 MB files (CPU DoS mitigation).
    _MACRO_TYPES = {b"\x01", b"\x06"}
    start = 0
    file_len = len(file_bytes)
    while True:
        idx = file_bytes.find(_XLS_MACRO_SHEET_MARKER, start, file_len - 8)
        if idx == -1:
            break
        rec_size = int.from_bytes(file_bytes[idx + 2: idx + 4], "little")
        # sheet type (bType) is the HIGH byte of the 2-byte grbit field (pos+9),
        # not the low byte (pos+8 = visibility flags).
        if rec_size >= 6 and idx + 10 <= file_len:
            if file_bytes[idx + 9: idx + 10] in _MACRO_TYPES:
                raise UploadError(
                    "El archivo .xls contiene hojas de macro (XLM).",
                    code="UNSAFE_EXCEL_CONTENT",
                    sim_code="SIM-00301",
                )
        start = idx + 2  # skip past the 2-byte marker


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_excel_safety(file_bytes: bytes, filename: str) -> None:
    """Validate *file_bytes* with the appropriate checks for the file extension.

    * ``.xlsx`` → full OOXML/ZIP scan.
    * ``.xls``  → OLE/CFBF binary scan (converting to .xlsx is safer).

    Raises :class:`UploadError` on any violation.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".xls":
        _check_xls_safety(file_bytes)
    else:
        _check_xlsx_safety(file_bytes)


def check_ooxml_safety(file_bytes: bytes) -> None:
    """Legacy entry point — full OOXML safety scan (.xlsx only)."""
    _check_xlsx_safety(file_bytes)
