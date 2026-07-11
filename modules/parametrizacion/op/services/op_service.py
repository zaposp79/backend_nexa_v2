"""Servicio de dominio OP."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
from nexa_engine.modules.parametrizacion.op.dto.dto import OPUploadResponse, OPUploadSummary, OPVersionSummary, OPSheetPreview
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
            raise ValidationError("OP Excel validation failed", errors=validation.errors, sim_code="SIM-00505")

        # 7. Map to domain model
        version_id = self._repo.new_version_id()
        master = self._mapper.map(version_id, sheets)
        data_dict = self._mapper.to_dict(master)

        colombia_version_id = datetime.now(_COLOMBIA_TZ).strftime("%Y-%m-%d %H-%M-%S")

        total_rows = sum(len(r) for r in sheets.values())
        uploaded_at = self._repo.now_iso()
        created_at_utc = datetime.now(timezone.utc).isoformat()
        sheets_found = list(sheets.keys())
        sheet_count = len(sheets)

        summary = VersionSummary(
            version_id=version_id,
            filename=filename,
            uploaded_at=uploaded_at,
            is_active=False,
            sheet_count=sheet_count,
            total_rows=total_rows,
            display_version_id=colombia_version_id,
            sheets_found=sheets_found,
        )

        # 8. Persist only after full validation
        metadata = {
            "pk": "op",
            "version_id": colombia_version_id,
            "type": "parametrization_version",
            "status": "active",
            "created_at": created_at_utc,
            "file_name": filename,
            "sheet_count": sheet_count,
            "total_rows": total_rows,
            "user_id": user_id,
            "sheets_found": sheets_found,
        }
        self._repo.save_version(summary, data_dict, metadata)

        full_payload = {**data_dict, "status": "active", "domain": "op"}

        return OPUploadResponse(
            summary=OPUploadSummary(
                id=version_id,
                domain="op",
                pk="op",
                version_id=colombia_version_id,
                type="parametrization_version",
                status="active",
                created_at=created_at_utc,
                file_name=filename,
                sheet_count=sheet_count,
                total_rows=total_rows,
                user_id=user_id if user_id != "anonymous" else None,
                sheets_found=sheets_found,
            ),
            payload=full_payload,
            warnings=validation.warnings,
        )

    def list_versions(self) -> List[OPVersionSummary]:
        summaries = sorted(
            self._repo.list_versions(),
            key=lambda s: s.uploaded_at or "",
            reverse=True,
        )
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
            for s in summaries
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
        _skip = {"extra_sheets", "status", "domain"}

        for key, value in data.items():
            if key in _skip:
                continue
            if isinstance(value, dict) and "catalogs" in value:
                catalogs = value["catalogs"]
                previews.append(OPSheetPreview(
                    name=key,
                    row_count=sum(len(v) for v in catalogs.values()),
                    columns=list(catalogs.keys()),
                    sample_rows=[],
                ))
            elif isinstance(value, list):
                columns = list(value[0].keys()) if value else []
                previews.append(OPSheetPreview(
                    name=key,
                    row_count=len(value),
                    columns=columns,
                    sample_rows=value[:3],
                ))
        return previews

    def get_sheet_rows(self, sheet_key: str) -> Any:
        active = self.get_active()
        if active is None:
            return []
        data = active["data"]
        value = data.get(sheet_key)
        if value is None:
            return []
        if isinstance(value, dict) and "catalogs" in value:
            return value["catalogs"]
        return value

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

    def get_by_id(self, version_id: str) -> dict:
        return self._repo.get_document_raw(version_id)
