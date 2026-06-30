"""Servicio de dominio HR: orquesta carga, validación, mapeo y almacenamiento."""

from __future__ import annotations

import logging
import time

from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
from nexa_engine.modules.parametrizacion.hr.dto.dto import HRUploadResponse, HRVersionSummary
from nexa_engine.modules.parametrizacion.hr.mappers.mapper import HRMapper
from nexa_engine.modules.parametrizacion.hr.repositories.hr_repository import HRRepository
from nexa_engine.modules.parametrizacion.hr.validators.validator import (
    HRValidator,
    REQUIRED_SHEETS,
    OPTIONAL_SHEETS,
)
from nexa_engine.modules.parametrizacion.shared.helpers.excel_preflight import check_ooxml_safety
from nexa_engine.modules.parametrizacion.shared.helpers.excel_reader import read_excel_sheets
from nexa_engine.modules.parametrizacion.shared.helpers.upload_guards import (
    check_file_size,
    sanitize_filename,
)
from nexa_engine.modules.parametrizacion.shared.contracts.normalizer import normalize_sheets_by_contract
from nexa_engine.modules.shared.exceptions import NotFoundError, UploadError, ValidationError
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary

logger = logging.getLogger("nexa.parametrization.hr")


class HRService:
    """Orquesta cargas Excel HR."""

    def __init__(
        self,
        repository: HRRepository,
        validator: HRValidator | None = None,
        mapper: HRMapper | None = None,
    ) -> None:
        self._repo = repository
        self._validator = validator or HRValidator()
        self._mapper = mapper or HRMapper()

    def process_upload(self, filename: str, file_bytes: bytes) -> HRUploadResponse:
        """Valida, mapea y persiste un archivo Excel HR.

        La nueva versión queda activa automáticamente y desactiva versiones previas.

        Flujo de validación (en orden, sin excepción):
            sanitize_filename
            → check_file_size
            → check_ooxml_safety          (ZIP-level: macros, formulas, ext links)
            → read_excel_sheets + contract (sheet names + exact headers)
            → normalize_sheets_by_contract (typed per column: percentage_decimal, int, money…)
            → HRValidator.validate        (numeric values, empty fields)
            → mapper.map + persist

        Raises:
            UploadError: el archivo no puede parsearse o viola un límite.
            ValidationError: violación de contrato (hojas, encabezados, valores).
        """
        t0 = time.monotonic()

        logger.info("=" * 80)
        logger.info("[PARAMETRIZATION] HR upload started: file=%s", filename)

        # 1. Sanitize filename
        filename = sanitize_filename(filename)

        # 2. Size check — before any parsing
        check_file_size(file_bytes)

        # 3. OOXML security preflight
        check_ooxml_safety(file_bytes)

        previous_active = self._repo.get_active()
        previous_version_id = previous_active.version_id if previous_active else None
        if previous_version_id:
            logger.info(
                "[PARAMETRIZATION] Previous active version: %s",
                previous_version_id,
            )

        # 4. Read with strict contract (raises ValidationError on violation)
        logger.info("[PARAMETRIZATION] → Parsing Excel sheets with contract validation")
        sheets = read_excel_sheets(file_bytes, "HR-", contract=HR_CONTRACT)

        sheets_found = list(sheets.keys())
        sheets_missing = [s for s in REQUIRED_SHEETS if s not in sheets_found]

        logger.info("[PARAMETRIZATION] Sheets found: %s", sheets_found)
        if sheets_missing:
            logger.warning("[PARAMETRIZATION] Missing required: %s", sheets_missing)

        # 5. Normalize cell values by contract column types
        sheets = normalize_sheets_by_contract(sheets, HR_CONTRACT)

        # 6. Business value validation — errors are NEVER silenced into warnings
        validation = self._validator.validate(sheets)
        if not validation.is_valid:
            raise ValidationError(
                "HR Excel validation failed", errors=validation.errors
            )

        # 7. Map to domain model
        logger.info("[PARAMETRIZATION] → Mapping sheets to domain models")
        version_id = self._repo.new_version_id()
        master = self._mapper.map(version_id, sheets)
        data_dict = self._mapper.to_dict(master)

        row_counts = {name: len(rows) for name, rows in sheets.items()}
        total_rows = sum(row_counts.values())

        # 8. Persist only after full validation
        uploaded_at = self._repo.now_iso()
        summary = VersionSummary(
            version_id=version_id,
            filename=filename,
            uploaded_at=uploaded_at,
            is_active=True,
            sheet_count=len(sheets_found),
            total_rows=total_rows,
        )
        self._repo.save_version(summary, data_dict)

        logger.info(
            "[PARAMETRIZATION] HR active version updated: previous=%s, current=%s",
            previous_version_id or "None",
            version_id,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("[PARAMETRIZATION] ✓ HR upload completed in %.1f ms", elapsed_ms)
        logger.info("=" * 80)

        return HRUploadResponse(
            version_id=version_id,
            filename=filename,
            uploaded_at=uploaded_at,
            sheets_found=sheets_found,
            sheets_missing=sheets_missing,
            row_counts=row_counts,
            warnings=validation.warnings,
        )

    def list_versions(self):
        summaries = self._repo.list_versions()
        return [
            HRVersionSummary(
                version_id=s.version_id,
                filename=s.filename,
                uploaded_at=s.uploaded_at,
                is_active=s.is_active,
                sheet_count=s.sheet_count,
                total_rows=s.total_rows,
            )
            for s in summaries
        ]

    def get_active(self):
        summary = self._repo.get_active()
        if summary is None:
            return None

        data = self._repo.get_version(summary.version_id)

        row_counts = {}
        for section_name, section_data in data.items():
            if isinstance(section_data, list):
                row_counts[section_name] = len(section_data)
            elif isinstance(section_data, dict):
                if section_name == "niveles" and "catalogs" in section_data:
                    catalogs = section_data["catalogs"]
                    row_counts[section_name] = sum(len(v) for v in catalogs.values())
                else:
                    row_counts[section_name] = len(section_data)

        preview = {}
        for section in ["costo_fijo", "med_seg", "ratios", "nomina", "salarios"]:
            section_data = data.get(section, [])
            if isinstance(section_data, list) and section_data:
                preview[section] = section_data[:5]

        return {
            "summary": summary.to_dict(),
            "row_counts": row_counts,
            "preview": preview,
            "data": data,
        }

    def activate(self, version_id: str) -> HRVersionSummary:
        s = self._repo.activate_version(version_id)
        return HRVersionSummary(
            version_id=s.version_id,
            filename=s.filename,
            uploaded_at=s.uploaded_at,
            is_active=s.is_active,
            sheet_count=s.sheet_count,
            total_rows=s.total_rows,
        )

    def delete(self, version_id: str) -> None:
        self._repo.delete_version(version_id)

    def get_version(self, version_id: str):
        summary = self._repo.get_summary(version_id)
        data = self._repo.get_version(version_id)
        return {"summary": summary.to_dict(), "data": data}

    def validate_excel_vs_stored(self, filename: str, file_bytes: bytes, version_id: str = None):
        logger.info("[VALIDATION] Excel vs JSON validation started: file=%s", filename)

        sheets = read_excel_sheets(file_bytes, "HR-", contract=HR_CONTRACT)
        sheets = normalize_sheets_by_contract(sheets, HR_CONTRACT)

        if version_id is None:
            active = self._repo.get_active()
            if active is None:
                raise ValidationError("No active HR version to compare against")
            version_id = active.version_id

        stored_data = self._repo.get_version(version_id)
        excel_row_counts = {name: len(rows) for name, rows in sheets.items()}
        json_row_counts = {
            k: len(v)
            for k, v in stored_data.items()
            if isinstance(v, list)
        }

        discrepancies = []

        for section_key, sheet_key in [("costo_fijo", "HR-CostoFijo"), ("med_seg", "HR-Med-Seg")]:
            if sheet_key not in sheets or section_key not in stored_data:
                continue
            excel_rows = sheets[sheet_key]
            json_rows = stored_data[section_key]
            if len(excel_rows) != len(json_rows):
                discrepancies.append({
                    "section": section_key,
                    "type": "row_count_mismatch",
                    "excel_count": len(excel_rows),
                    "json_count": len(json_rows),
                })

        is_valid = len(discrepancies) == 0
        return {
            "valid": is_valid,
            "discrepancies": discrepancies,
            "excel_row_counts": excel_row_counts,
            "json_row_counts": json_row_counts,
            "version_id": version_id,
        }
