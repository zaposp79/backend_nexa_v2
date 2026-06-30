"""Tests for the OOXML security preflight component.

Covers the 25 rejection cases and partial positive cases at the preflight level.
Integration-level positive tests (full upload pipeline) live in
``test_excel_contracts.py``.
"""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

import openpyxl
import pytest

from nexa_engine.modules.parametrizacion.shared.helpers.excel_preflight import check_ooxml_safety
from nexa_engine.modules.shared.exceptions import UploadError, ValidationError

BACKEND_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Helpers to build synthetic workbooks
# ---------------------------------------------------------------------------

def _plain_xlsx(sheets: dict = None) -> bytes:
    """Create a minimal valid xlsx with no macros, formulas, or external refs."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Col1", "Col2"])
    ws.append(["val1", "val2"])
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def _make_zip_with_entries(entries: dict[str, bytes]) -> bytes:
    """Build a raw ZIP from {entry_name: content} mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _minimal_ooxml_entries() -> dict[str, bytes]:
    return {
        "[Content_Types].xml": b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        "_rels/.rels": b'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
        "xl/workbook.xml": b'<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"></workbook>',
        "xl/worksheets/sheet1.xml": b'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData></sheetData></worksheet>',
    }


# ===========================================================================
# NEGATIVE tests — every case must raise UploadError or ValidationError
# ===========================================================================

class TestRejectInvalidFiles:

    def test_rejects_empty_bytes(self):
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(b"")
        assert exc_info.value.code == "INVALID_EXCEL_FILE"

    def test_rejects_non_zip_content_with_xlsx_name(self):
        """PDF-like bytes — not a ZIP."""
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(b"%PDF-1.4 fake content")
        assert exc_info.value.code == "INVALID_EXCEL_FILE"

    def test_rejects_valid_zip_that_is_not_ooxml(self):
        """Valid ZIP but missing OOXML mandatory entries."""
        content = _make_zip_with_entries({"README.txt": b"hello"})
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "INVALID_EXCEL_FILE"

    def test_rejects_corrupted_zip(self):
        """Truncated ZIP bytes."""
        content = _plain_xlsx()[:50]
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code in ("INVALID_EXCEL_FILE",)

    def test_rejects_cfbf_magic_bytes(self):
        """CFBF/OLECF magic = encrypted .xlsx or legacy .xls."""
        cfbf = b"\xD0\xCF\x11\xE0" + b"\x00" * 100
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(cfbf)
        assert exc_info.value.code == "ENCRYPTED_EXCEL_FILE"


class TestRejectUnsafeContent:

    def test_rejects_workbook_with_vba_project(self):
        entries = _minimal_ooxml_entries()
        entries["xl/vbaProject.bin"] = b"\xD0\xCF\x11\xE0" + b"\x00" * 10
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "UNSAFE_EXCEL_CONTENT"

    def test_rejects_workbook_with_external_links_dir(self):
        entries = _minimal_ooxml_entries()
        entries["xl/externalLinks/externalLink1.xml"] = b"<externalLink/>"
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "UNSAFE_EXCEL_CONTENT"

    def test_rejects_workbook_with_macros_dir(self):
        entries = _minimal_ooxml_entries()
        entries["xl/macros/sheet1.bin"] = b"\x00"
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "UNSAFE_EXCEL_CONTENT"

    def test_rejects_workbook_with_connections_xml(self):
        entries = _minimal_ooxml_entries()
        entries["xl/connections.xml"] = b"<connections/>"
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "UNSAFE_EXCEL_CONTENT"

    def test_rejects_workbook_with_external_url_in_rels(self):
        entries = _minimal_ooxml_entries()
        entries["xl/_rels/workbook.xml.rels"] = (
            b'<Relationships><Relationship Target="https://evil.com/data.xml"/></Relationships>'
        )
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "UNSAFE_EXCEL_CONTENT"

    def test_rejects_workbook_with_ole_object_in_content_types(self):
        entries = _minimal_ooxml_entries()
        entries["[Content_Types].xml"] = (
            b'<Types><Override ContentType="application/vnd.ms-office.activeX+xml"/></Types>'
        )
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "UNSAFE_EXCEL_CONTENT"

    def test_rejects_workbook_with_formula_element_in_sheet_xml(self):
        """Sheet XML contains a <f> element — formula present."""
        sheet_xml = (
            b'<?xml version="1.0"?>'
            b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            b'<sheetData><row><c><f>SUM(A1:A10)</f><v>55</v></c></row></sheetData>'
            b'</worksheet>'
        )
        entries = _minimal_ooxml_entries()
        entries["xl/worksheets/sheet1.xml"] = sheet_xml
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "UNSAFE_EXCEL_CONTENT"

    def test_rejects_workbook_with_encryption_info_entry(self):
        entries = _minimal_ooxml_entries()
        entries["EncryptionInfo"] = b"\x04\x00\x04\x00"
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "ENCRYPTED_EXCEL_FILE"

    def test_rejects_zip_entry_with_path_traversal(self):
        entries = _minimal_ooxml_entries()
        entries["../../etc/passwd"] = b"root:x:0:0"
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "INVALID_EXCEL_FILE"


class TestRejectLimits:

    def test_rejects_file_with_excessive_uncompressed_entry(self, monkeypatch):
        """A single entry whose uncompressed size exceeds the limit."""
        import nexa_engine.modules.parametrizacion.shared.helpers.excel_preflight as pf
        monkeypatch.setattr(pf, "MAX_EXCEL_UNCOMPRESSED_BYTES", 100)

        entries = _minimal_ooxml_entries()
        entries["xl/worksheets/sheet1.xml"] = b"A" * 200  # 200 bytes uncompressed
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "EXCEL_LIMIT_EXCEEDED"

    def test_rejects_zip_bomb_via_compression_ratio(self, monkeypatch):
        """Entry whose compression ratio exceeds the limit."""
        import nexa_engine.modules.parametrizacion.shared.helpers.excel_preflight as pf
        monkeypatch.setattr(pf, "MAX_EXCEL_COMPRESSION_RATIO", 2)

        # Create highly compressible content: repeating bytes compress very well
        large_compressible = b"A" * 10_000
        entries = _minimal_ooxml_entries()
        entries["xl/worksheets/sheet1.xml"] = large_compressible
        content = _make_zip_with_entries(entries)
        with pytest.raises(UploadError) as exc_info:
            check_ooxml_safety(content)
        assert exc_info.value.code == "EXCEL_LIMIT_EXCEEDED"


# ===========================================================================
# POSITIVE test — valid minimal xlsx passes
# ===========================================================================

class TestAcceptValidFile:

    def test_accepts_minimal_valid_xlsx(self):
        """A plain xlsx with no macros, formulas, or external refs passes."""
        content = _plain_xlsx()
        check_ooxml_safety(content)  # must not raise

    def test_accepts_xlsx_with_internal_image(self):
        """Workbook with an image in media/ — internal refs are allowed."""
        entries = _minimal_ooxml_entries()
        # Internal relationship — target has no http scheme
        entries["xl/_rels/workbook.xml.rels"] = (
            b'<Relationships>'
            b'<Relationship Target="../media/image1.png" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"/>'
            b'</Relationships>'
        )
        entries["xl/media/image1.png"] = b"\x89PNG\r\n"
        content = _make_zip_with_entries(entries)
        check_ooxml_safety(content)  # must not raise
