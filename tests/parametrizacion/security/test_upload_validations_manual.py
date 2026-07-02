# -*- coding: utf-8 -*-
"""
Generador de archivos de prueba para las 22 validaciones de seguridad del upload.

Uso:
    python tests/parametrizacion/security/test_upload_validations_manual.py

Genera archivos en /tmp/nexa_test_files/ y muestra los curl para cada caso.
Requiere que la API esté corriendo en http://localhost:8000
"""

import io
import os
import struct
import zipfile
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1/parametrization/hr/upload"
OUT_DIR = Path("tests/parametrizacion/security/test_files")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers para construir archivos de prueba
# ---------------------------------------------------------------------------

def _minimal_xlsx_zip(extra_entries: dict | None = None, omit_entries: set | None = None) -> bytes:
    """Construye un XLSX mínimo válido como ZIP en memoria."""
    buf = io.BytesIO()
    required = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/xl/workbook.xml"'
            ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '</Types>'
        ).encode(),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
            ' Target="xl/workbook.xml"/>'
            '</Relationships>'
        ).encode(),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
            '</sheets></workbook>'
        ).encode(),
    }
    if extra_entries:
        required.update(extra_entries)
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in required.items():
            if omit_entries and name in omit_entries:
                continue
            zf.writestr(name, content)
    return buf.getvalue()


def _write(name: str, data: bytes) -> Path:
    path = OUT_DIR / name
    path.write_bytes(data)
    print(f"  ✓ Generado: {path}")
    return path


def _curl(path: Path, endpoint: str = BASE_URL, extra: str = "") -> str:
    return f'curl -s -X POST "{endpoint}" -F "file=@{path}" -F "user_id=test" {extra}'


# ---------------------------------------------------------------------------
# Generadores de archivos de prueba
# ---------------------------------------------------------------------------

def case_01_wrong_prefix():
    """Caso 1 — Prefijo de nombre incorrecto (GN_ enviado a HR endpoint)."""
    data = _minimal_xlsx_zip()
    p = _write("GN_archivo_enviado_a_hr.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: INVALID_FILENAME_PREFIX\n")


def case_02_wrong_extension():
    """Caso 2 — Extensión no permitida (.csv, .docx, .pdf, .jar)."""
    pdf_content = b"%PDF-1.4 fake pdf content"
    for ext in [".csv", ".docx", ".pdf", ".jar", ".exe"]:
        p = _write(f"HR_archivo{ext}", pdf_content)
        print(f"  curl ({ext}): {_curl(p)}")
    print("  Esperado: INVALID_FILE_EXTENSION\n")


def case_03_file_too_large():
    """Caso 3 — Archivo mayor a 5 MB."""
    # Genera 6 MB de ceros
    large = b"\x00" * (6 * 1024 * 1024)
    p = _write("HR_muy_grande.xlsx", large)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: EXCEL_LIMIT_EXCEEDED\n")


def case_04_wrong_magic_bytes():
    """Caso 4 — Archivo con extensión xlsx pero firma incorrecta.

    Sub-casos:
      a) PDF renombrado a .xlsx
      b) Ejecutable .exe renombrado a .xlsx
      c) Archivo de texto renombrado
    """
    # a) PDF → .xlsx
    p = _write("HR_pdf_renombrado.xlsx", b"%PDF-1.4 Este es un PDF con extension xlsx")
    print(f"  curl (PDF→xlsx): {_curl(p)}")

    # b) Texto → .xlsx
    p = _write("HR_texto_renombrado.xlsx", b"Esto es un texto plano con extension xlsx")
    print(f"  curl (texto→xlsx): {_curl(p)}")

    # c) .docx (también es ZIP, pero sin estructura OOXML Excel) → .xlsx
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml",
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Override PartName="/word/document.xml"'
                    ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                    '</Types>')
        zf.writestr("word/document.xml", "<document/>")
    p = _write("HR_docx_renombrado.xlsx", buf.getvalue())
    print(f"  curl (docx→xlsx): {_curl(p)}")
    print("  Esperado: INVALID_EXCEL_FILE\n")


def case_05_missing_ooxml_structure():
    """Caso 5 — XLSX sin estructura OOXML requerida (falta xl/workbook.xml)."""
    data = _minimal_xlsx_zip(omit_entries={"xl/workbook.xml"})
    p = _write("HR_sin_workbook.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: INVALID_EXCEL_FILE\n")


def case_06_path_traversal():
    """Caso 6 — ZIP con path traversal en nombres de entrada."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Entradas normales requeridas
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("_rels/.rels", "<Relationships/>")
        zf.writestr("xl/workbook.xml", "<workbook/>")
        # Entrada maliciosa con traversal
        info = zipfile.ZipInfo("../../etc/passwd")
        zf.writestr(info, "root:x:0:0:root:/root:/bin/bash")
    p = _write("HR_path_traversal.xlsx", buf.getvalue())
    print(f"  curl: {_curl(p)}")
    print("  Esperado: INVALID_EXCEL_FILE\n")


def case_07_encrypted_workbook():
    """Caso 7 — Workbook cifrado / protegido con contraseña."""
    data = _minimal_xlsx_zip(extra_entries={"EncryptionInfo": b"fake-encryption-data"})
    p = _write("HR_cifrado.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: ENCRYPTED_EXCEL_FILE\n")


def case_08_vba_macros():
    """Caso 8 — Archivo con macros VBA (xl/vbaProject.bin)."""
    data = _minimal_xlsx_zip(extra_entries={"xl/vbaProject.bin": b"fake-vba-binary"})
    p = _write("HR_con_macros.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_09_macro_content_type():
    """Caso 9 — Content_Types.xml declara tipo macro-enabled (xlsm disfrazado de xlsx)."""
    macro_ct = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/xl/workbook.xml"'
        ' ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/>'
        '</Types>'
    ).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", macro_ct)
        zf.writestr("_rels/.rels", b"<Relationships/>")
        zf.writestr("xl/workbook.xml", b"<workbook/>")
    p = _write("HR_xlsm_disfrazado.xlsx", buf.getvalue())
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_10_external_links():
    """Caso 10 — Workbook con vínculos externos a otros archivos Excel."""
    data = _minimal_xlsx_zip(extra_entries={
        "xl/externalLinks/externalLink1.xml": b"<externalLink/>",
        "xl/externalLinks/_rels/externalLink1.xml.rels": b"<Relationships/>",
    })
    p = _write("HR_external_links.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_11_activex():
    """Caso 11 — Objeto ActiveX embebido."""
    data = _minimal_xlsx_zip(extra_entries={"xl/activeX/activeX1.xml": b"<activeX/>"})
    p = _write("HR_activex.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_12_external_url_in_rels():
    """Caso 12 — URL externa en archivo .rels (SSRF / beacon)."""
    evil_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"'
        ' Target="http://attacker.com/beacon.png"/>'
        '</Relationships>'
    ).encode()
    data = _minimal_xlsx_zip(extra_entries={"xl/_rels/workbook.xml.rels": evil_rels})
    p = _write("HR_external_url.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_13_xxe_injection():
    """Caso 13 — XXE injection en XML interno del ZIP."""
    evil_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        '<workbook>&xxe;</workbook>'
    ).encode()
    data = _minimal_xlsx_zip(extra_entries={"xl/workbook.xml": evil_xml})
    p = _write("HR_xxe.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_14_dde_injection():
    """Caso 14 — DDE injection en sharedStrings.xml (sin etiqueta <f>)."""
    evil_strings = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<si><t>=DDE("cmd","/c calc.exe","1")</t></si>'
        '<si><t>=SYSTEM("whoami")</t></si>'
        '</sst>'
    ).encode()
    data = _minimal_xlsx_zip(extra_entries={"xl/sharedStrings.xml": evil_strings})
    p = _write("HR_dde_strings.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_15_formula_in_cell():
    """Caso 15 — Fórmula <f> en hoja XML."""
    evil_sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        '<row r="1"><c r="A1" t="str"><f>=SUM(1,2)</f><v>3</v></c></row>'
        '</sheetData>'
        '</worksheet>'
    ).encode()
    data = _minimal_xlsx_zip(extra_entries={"xl/worksheets/sheet1.xml": evil_sheet})
    p = _write("HR_formula.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_16_ddeauto_in_sheet():
    """Caso 16 — Patrón DDEAUTO en hoja XML (fuera de <f>)."""
    evil_sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        '<row r="1"><c r="A1" t="str"><v>DDEAUTO cmd.exe "/c whoami"</v></c></row>'
        '</sheetData>'
        '</worksheet>'
    ).encode()
    data = _minimal_xlsx_zip(extra_entries={"xl/worksheets/sheet1.xml": evil_sheet})
    p = _write("HR_ddeauto.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def _zip_with_stored_entry(entry_name: str, entry_bytes: bytes) -> bytes:
    """ZIP mínimo válido con una entrada almacenada SIN compresión (ZIP_STORED).

    Necesario para que bytes como 'MZ' o EICAR sean visibles en el stream raw
    del archivo (la detección escanea bytes antes de descomprimir).
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels"'
            ' ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/xl/workbook.xml"'
            ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '</Types>'
        ))
        zf.writestr("_rels/.rels", (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        ))
        zf.writestr("xl/workbook.xml", "<workbook/>")
        info = zipfile.ZipInfo(entry_name)
        zf.writestr(info, entry_bytes, compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()


def case_17_embedded_pe():
    """Caso 17 — Ejecutable Windows (MZ) embebido dentro del ZIP.

    La detección escanea los bytes RAW del archivo (antes de descomprimir),
    por lo que el payload debe almacenarse con ZIP_STORED.
    """
    pe_payload = b"MZ" + b"\x00" * 60 + b"This program cannot be run in DOS mode."
    data = _zip_with_stored_entry("xl/media/image1.bin", pe_payload)
    p = _write("HR_exe_embebido.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_18_eicar():
    """Caso 18 — Firma EICAR (estándar de test antivirus).

    Igual que el caso PE: debe usar ZIP_STORED para que la firma sea visible
    en los bytes raw antes de descompresión.
    """
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    data = _zip_with_stored_entry("xl/media/eicar.bin", eicar)
    p = _write("HR_eicar.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: VIRUS_DETECTED\n")


def case_19_zip_bomb():
    """Caso 19 — ZIP bomb: ratio de compresión excesiva."""
    # 1 MB de ceros → ratio ~1000:1 al comprimir
    big_data = b"\x00" * (1024 * 1024)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("_rels/.rels", b"<Relationships/>")
        zf.writestr("xl/workbook.xml", b"<workbook/>")
        zf.writestr("xl/worksheets/bomb.xml", big_data)
    p = _write("HR_zipbomb.xlsx", buf.getvalue())
    print(f"  curl: {_curl(p)}")
    print("  Esperado: EXCEL_LIMIT_EXCEEDED\n")


def case_20_xls_vba():
    """Caso 20 — Archivo .xls con firma VBA en UTF-16LE."""
    # CFBF header + VBA marker (V\x00B\x00A\x00 en UTF-16LE)
    cfbf_header = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 504
    vba_marker = b"V\x00B\x00A\x00"
    data = cfbf_header + vba_marker + b"\x00" * 512
    p = _write("HR_vba.xls", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_21_xls_xlm_macro():
    """Caso 21 — Archivo .xls con hoja de macro XLM (BIFF8 BOUNDSHEET type=0x01)."""
    cfbf_header = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 504
    # BOUNDSHEET record: ID=0x0085 (2B LE), size=8 (2B LE), position=0 (4B), visibility=0, type=0x01 (macro)
    boundsheet_record = (
        b"\x85\x00"          # record ID = BOUNDSHEET
        b"\x08\x00"          # record size = 8
        b"\x00\x00\x00\x00"  # sheet BOF position
        b"\x00"              # visibility = visible
        b"\x01"              # type = 0x01 (macro sheet)
        b"\x00\x00"          # sheet name (empty)
    )
    data = cfbf_header + b"\x00" * 512 + boundsheet_record + b"\x00" * 512
    p = _write("HR_xlm_macro.xls", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: UNSAFE_EXCEL_CONTENT\n")


def case_22_clamav():
    """Caso 22 — ClamAV (requiere CLAMAV_SOCKET configurado y clamd instalado)."""
    print("  Este caso requiere:")
    print("    1. export CLAMAV_SOCKET=/var/run/clamav/clamd.ctl")
    print("    2. pip install clamd")
    print("    3. clamd corriendo en el socket configurado")
    print("  Con ClamAV activo, el archivo EICAR del caso 18 también activa VIRUS_DETECTED.")
    print("  Sin ClamAV, el scan se omite silenciosamente (solo EICAR por firma estática).\n")


# ---------------------------------------------------------------------------
# Caso válido — debe pasar todas las validaciones
# ---------------------------------------------------------------------------

def case_valid_xlsx():
    """Caso válido — archivo XLSX sin datos de negocio, solo estructura mínima."""
    plain_sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        '<row r="1">'
        '<c r="A1" t="inlineStr"><is><t>Cargo</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t>Salario</t></is></c>'
        '</row>'
        '<row r="2">'
        '<c r="A2" t="inlineStr"><is><t>Agente</t></is></c>'
        '<c r="B2"><v>1500000</v></c>'
        '</row>'
        '</sheetData>'
        '</worksheet>'
    ).encode()
    data = _minimal_xlsx_zip(extra_entries={"xl/worksheets/sheet1.xml": plain_sheet})
    p = _write("HR_valido_estructura.xlsx", data)
    print(f"  curl: {_curl(p)}")
    print("  Esperado: pasa las validaciones de seguridad")
    print("  (puede fallar después por hojas HR requeridas — eso es correcto)\n")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("GENERADOR DE ARCHIVOS DE PRUEBA — Validaciones de seguridad upload")
    print(f"Archivos generados en: {OUT_DIR.resolve()}")
    print(f"Endpoint de prueba: {BASE_URL}")
    print("=" * 70)
    print()

    casos = [
        ("01", "Prefijo de nombre incorrecto",          case_01_wrong_prefix),
        ("02", "Extensión no permitida",                 case_02_wrong_extension),
        ("03", "Archivo > 5 MB",                         case_03_file_too_large),
        ("04", "Firma de archivo incorrecta (magic)",   case_04_wrong_magic_bytes),
        ("05", "Sin estructura OOXML",                   case_05_missing_ooxml_structure),
        ("06", "Path traversal en ZIP",                  case_06_path_traversal),
        ("07", "Workbook cifrado",                        case_07_encrypted_workbook),
        ("08", "Macros VBA",                             case_08_vba_macros),
        ("09", "Content-Type con macros",                case_09_macro_content_type),
        ("10", "Links externos (externalLinks)",         case_10_external_links),
        ("11", "ActiveX embebido",                       case_11_activex),
        ("12", "URL externa en .rels",                   case_12_external_url_in_rels),
        ("13", "XXE injection",                          case_13_xxe_injection),
        ("14", "DDE en sharedStrings",                   case_14_dde_injection),
        ("15", "Fórmula <f> en celda",                   case_15_formula_in_cell),
        ("16", "DDEAUTO en hoja",                        case_16_ddeauto_in_sheet),
        ("17", "Ejecutable PE embebido",                 case_17_embedded_pe),
        ("18", "Firma EICAR (antivirus test)",           case_18_eicar),
        ("19", "ZIP bomb",                               case_19_zip_bomb),
        ("20", "XLS con VBA",                            case_20_xls_vba),
        ("21", "XLS con hoja XLM macro",                 case_21_xls_xlm_macro),
        ("22", "ClamAV (AV externo)",                    case_22_clamav),
        ("00", "CASO VÁLIDO (referencia)",               case_valid_xlsx),
    ]

    for num, nombre, fn in casos:
        sep = "-" * max(1, 48 - len(nombre))
        print(f"--- Caso {num}: {nombre} {sep}")
        fn()

    print("=" * 70)
    print("Todos los archivos generados. Ejecuta los curl contra la API.")
    print()
    print("Para probar todos en batch (bash):")
    print(f"  for f in {OUT_DIR}/*.xlsx {OUT_DIR}/*.xls; do")
    print('    echo "--- $f ---"')
    print(f'    curl -s -X POST "{BASE_URL}" -F "file=@$f" -F "user_id=test" | python -m json.tool')
    print("  done")
    print("=" * 70)
