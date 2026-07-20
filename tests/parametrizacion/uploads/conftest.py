from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from typing import Iterable

import openpyxl
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECTS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECTS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECTS_ROOT))
import backend_nexa_v2  # noqa: F401,E402


def workbook_bytes(sheets: dict[str, tuple[Iterable[str], list[Iterable[object]]]]) -> bytes:
    workbook = openpyxl.Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    for sheet_name, (headers, rows) in sheets.items():
        worksheet = workbook.create_sheet(sheet_name)
        worksheet.append(list(headers))
        for row in rows:
            worksheet.append(list(row))

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def read_json(path: Path):
    import json

    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def isolated_app() -> FastAPI:
    return FastAPI()


def client_for_router(app: FastAPI, router) -> TestClient:
    app.include_router(router)
    return TestClient(app)
