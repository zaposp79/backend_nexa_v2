"""Servicio de dominio GN."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nexa_engine.modules.parametrizacion.gn.contracts import GN_CONTRACT
from nexa_engine.modules.parametrizacion.gn.dto.dto import GNSheetPreview, GNUploadResponse, GNVersionSummary
from nexa_engine.modules.parametrizacion.gn.mappers.mapper import GNMapper
from nexa_engine.modules.parametrizacion.gn.repositories.gn_repository import GNRepository
from nexa_engine.modules.parametrizacion.gn.validators.validator import GNValidator
from nexa_engine.modules.parametrizacion.shared.helpers.excel_preflight import check_ooxml_safety
from nexa_engine.modules.parametrizacion.shared.helpers.excel_reader import read_excel_sheets
from nexa_engine.modules.parametrizacion.shared.helpers.upload_guards import (
    check_file_size,
    sanitize_filename,
)
from nexa_engine.modules.parametrizacion.shared.contracts.normalizer import normalize_sheets_by_contract
from nexa_engine.modules.shared.exceptions import ValidationError
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary


class GNService:
    """Orquesta cargas Excel GN."""

    def __init__(
        self,
        repository: GNRepository,
        validator: GNValidator | None = None,
        mapper: GNMapper | None = None,
    ) -> None:
        self._repo = repository
        self._validator = validator or GNValidator()
        self._mapper = mapper or GNMapper()

    def process_upload(self, filename: str, file_bytes: bytes) -> GNUploadResponse:
        # 1. Sanitize filename (must not be used for path operations until sanitized)
        filename = sanitize_filename(filename)

        # 2. Size check — before any parsing
        check_file_size(file_bytes)

        # 3. OOXML security preflight — ZIP-level checks, formula detection, VBA, etc.
        check_ooxml_safety(file_bytes)

        # 4. Read sheets with strict contract validation (sheet names + exact headers)
        sheets = read_excel_sheets(file_bytes, "GN-", contract=GN_CONTRACT)

        # 5. Normalize cell values by contract column types
        sheets = normalize_sheets_by_contract(sheets, GN_CONTRACT)

        # 6. Business value validation
        validation = self._validator.validate(sheets)
        if not validation.is_valid:
            raise ValidationError("GN Excel validation failed", errors=validation.errors)

        # 7. Map to domain model
        version_id = self._repo.new_version_id()
        master = self._mapper.map(version_id, sheets)
        data_dict = self._mapper.to_dict(master)

        total_rows = sum(len(rows) for rows in sheets.values())
        uploaded_at = self._repo.now_iso()

        summary = VersionSummary(
            version_id=version_id,
            filename=filename,
            uploaded_at=uploaded_at,
            is_active=False,
            sheet_count=len(sheets),
            total_rows=total_rows,
        )

        # 8. Persist only after full validation
        self._repo.save_version(summary, data_dict)

        return GNUploadResponse(
            version_id=version_id,
            filename=filename,
            uploaded_at=uploaded_at,
            sheets_found=list(sheets.keys()),
            total_rows=total_rows,
            warnings=validation.warnings,
        )

    def list_versions(self) -> List[GNVersionSummary]:
        return [
            GNVersionSummary(
                version_id=s.version_id,
                filename=s.filename,
                uploaded_at=s.uploaded_at,
                is_active=s.is_active,
                sheet_count=s.sheet_count,
                total_rows=s.total_rows,
            )
            for s in self._repo.list_versions()
        ]

    def get_active(self) -> Optional[Dict[str, Any]]:
        summary = self._repo.get_active()
        if summary is None:
            return None
        data = self._repo.get_version(summary.version_id)
        return {"summary": summary.to_dict(), "data": data}

    def get_active_previews(self) -> List[GNSheetPreview]:
        active = self.get_active()
        if active is None:
            return []
        previews = []
        data = active["data"]

        lv = data.get("lv")
        if lv:
            catalogs = lv.get("catalogs", {})
            previews.append(GNSheetPreview(
                name=lv["name"],
                row_count=sum(len(v) for v in catalogs.values()),
                columns=list(catalogs.keys()),
                sample_rows=[],
            ))

        for sheet in data.get("sheets", []):
            rows = sheet.get("rows", [])
            columns = list(rows[0].keys()) if rows else []
            previews.append(GNSheetPreview(
                name=sheet["name"],
                row_count=len(rows),
                columns=columns,
                sample_rows=rows[:3],
            ))
        return previews

    def get_sheet_rows(self, sheet_key: str) -> List[dict]:
        active = self.get_active()
        if active is None:
            return []
        data = active["data"]

        lv = data.get("lv")
        if lv and lv.get("key") == sheet_key:
            return [lv.get("catalogs", {})]

        for sheet in data.get("sheets", []):
            if sheet.get("key") == sheet_key:
                return sheet.get("rows", [])
        return []

    def activate(self, version_id: str) -> GNVersionSummary:
        s = self._repo.activate_version(version_id)
        return GNVersionSummary(
            version_id=s.version_id,
            filename=s.filename,
            uploaded_at=s.uploaded_at,
            is_active=s.is_active,
            sheet_count=s.sheet_count,
            total_rows=s.total_rows,
        )

    def delete(self, version_id: str) -> None:
        self._repo.delete_version(version_id)
