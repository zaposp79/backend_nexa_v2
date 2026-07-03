"""Servicio de dominio OP."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
from nexa_engine.modules.parametrizacion.op.dto.dto import OPUploadResponse, OPVersionSummary, OPSheetPreview
from nexa_engine.modules.parametrizacion.op.mappers.mapper import OPMapper
from nexa_engine.modules.parametrizacion.op.repositories.op_repository import OPRepository
from nexa_engine.modules.parametrizacion.op.validators.validator import OPValidator
from nexa_engine.modules.parametrizacion.shared.helpers.excel_preflight import check_excel_safety
from nexa_engine.modules.parametrizacion.shared.helpers.excel_reader import read_excel_sheets
from nexa_engine.modules.parametrizacion.shared.helpers.upload_guards import (
    check_file_size,
    sanitize_filename,
)
from nexa_engine.modules.parametrizacion.shared.contracts.normalizer import normalize_sheets_by_contract
from nexa_engine.modules.shared.exceptions import NotFoundError, ValidationError
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary

_COLOMBIA_TZ = timezone(timedelta(hours=-5))


class OPService:
    """Orquesta cargas Excel OP."""

    def __init__(
        self,
        repository: OPRepository,
        validator: OPValidator | None = None,
        mapper: OPMapper | None = None,
    ) -> None:
        self._repo = repository
        self._validator = validator or OPValidator()
        self._mapper = mapper or OPMapper()

    def process_upload(self, filename: str, file_bytes: bytes, user_id: str = "anonymous") -> OPUploadResponse:
        # 1. Sanitize filename
        filename = sanitize_filename(filename)

        # 2. Size check
        check_file_size(file_bytes)

        # 3. OOXML security preflight
        check_excel_safety(file_bytes, filename)

        # 4. Read with strict contract validation
        sheets = read_excel_sheets(file_bytes, "OP-", contract=OP_CONTRACT)

        # 5. Normalize values by contract column types
        sheets = normalize_sheets_by_contract(sheets, OP_CONTRACT)

        # 6. Business validation
        validation = self._validator.validate(sheets)
        if not validation.is_valid:
            raise ValidationError("OP Excel validation failed", errors=validation.errors)

        # 7. Map to domain model
        version_id = self._repo.new_version_id()
        master = self._mapper.map(version_id, sheets)
        data_dict = self._mapper.to_dict(master)

        colombia_version_id = datetime.now(_COLOMBIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        data_dict["version_id"] = colombia_version_id

        total_rows = sum(len(r) for r in sheets.values())
        uploaded_at = self._repo.now_iso()

        summary = VersionSummary(
            version_id=version_id,
            filename=filename,
            uploaded_at=uploaded_at,
            is_active=False,
            sheet_count=len(sheets),
            total_rows=total_rows,
            display_version_id=colombia_version_id,
            sheets_found=list(sheets.keys()),
        )

        # 8. Persist only after full validation
        metadata = {
            "pk": "op",
            "version_id": colombia_version_id,
            "type": "parametrization_version",
            "status": "active",
            "created_at": datetime.now(_COLOMBIA_TZ).isoformat(),
            "file_name": filename,
            "sheet_count": len(sheets),
            "total_rows": total_rows,
            "user_id": user_id,
            "sheets_found": list(sheets.keys()),
        }
        self._repo.save_version(summary, data_dict, metadata)

        return OPUploadResponse(
            version_id=colombia_version_id,
            filename=filename,
            uploaded_at=uploaded_at,
            sheets_found=list(sheets.keys()),
            total_rows=total_rows,
            warnings=validation.warnings,
        )

    def list_versions(self) -> List[OPVersionSummary]:
        return [
            OPVersionSummary(
                id=s.version_id,
                version_id=s.display_version_id or s.version_id,
                filename=s.filename,
                uploaded_at=s.uploaded_at,
                is_active=s.is_active,
                sheet_count=s.sheet_count,
                total_rows=s.total_rows,
                sheets_found=s.sheets_found,
            )
            for s in self._repo.list_versions()
        ]

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        try:
            summary = self._repo.get_summary(version_id)
        except (NotFoundError, KeyError, FileNotFoundError):
            return None
        data = self._repo.get_version(version_id)
        return {"summary": summary.to_dict(), "data": data}

    def get_active(self) -> Optional[Dict[str, Any]]:
        summary, data = self._repo.get_active_record()
        if summary is None or data is None:
            return None
        return {"summary": summary.to_dict(), "data": data}

    def get_active_previews(self) -> List[OPSheetPreview]:
        active = self.get_active()
        if active is None:
            return []
        previews = []
        data = active["data"]

        for sheet in data.get("sheets", []):
            if "catalogs" in sheet:
                catalogs = sheet.get("catalogs", {})
                previews.append(OPSheetPreview(
                    name=sheet["name"],
                    row_count=sum(len(v) for v in catalogs.values()),
                    columns=list(catalogs.keys()),
                    sample_rows=[],
                ))
                continue

            rows = sheet.get("rows", [])
            columns = list(rows[0].keys()) if rows else []
            previews.append(OPSheetPreview(
                name=sheet["name"],
                row_count=len(rows),
                columns=columns,
                sample_rows=rows[:3],
            ))
        return previews

    def get_sheet_rows(self, sheet_key: str) -> Any:
        active = self.get_active()
        if active is None:
            return []
        data = active["data"]

        for sheet in data.get("sheets", []):
            if sheet.get("key") != sheet_key:
                continue
            if "catalogs" in sheet:
                return sheet.get("catalogs", {})
            return sheet.get("rows", [])
        return []

    def activate(self, version_id: str) -> OPVersionSummary:
        s = self._repo.activate_version(version_id)
        return OPVersionSummary(
            id=s.version_id,
            version_id=s.display_version_id or s.version_id,
            filename=s.filename,
            uploaded_at=s.uploaded_at,
            is_active=s.is_active,
            sheet_count=s.sheet_count,
            total_rows=s.total_rows,
            sheets_found=s.sheets_found,
        )

    def delete(self, version_id: str) -> None:
        self._repo.delete_version(version_id)
