from __future__ import annotations

import copy

import pytest

from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import (
    GNVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import (
    HRVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.op.mappers.op_version_document_codec import (
    OPVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.shared.mappers.version_index_document_codec import (
    VersionIndexDocumentCodec,
)


@pytest.mark.parametrize(
    "codec,payload",
    [
        (GNVersionDocumentCodec(), {"version_id": "gn-v1", "lv": None, "sheets": []}),
        (HRVersionDocumentCodec(), {"version_id": "hr-v1", "niveles": {}, "salarios": []}),
        (OPVersionDocumentCodec(), {"version_id": "op-v1", "sheets": []}),
    ],
)
def test_version_codecs_separate_technical_id_from_payload(codec, payload):
    original = copy.deepcopy(payload)

    record = codec.encode(payload)

    assert record.id == payload["version_id"]
    assert record.payload == original
    assert "id" not in record.payload
    assert payload == original
    assert codec.decode(record) == original


@pytest.mark.parametrize(
    "codec",
    [GNVersionDocumentCodec(), HRVersionDocumentCodec(), OPVersionDocumentCodec()],
)
def test_version_codecs_fail_when_version_id_is_missing(codec):
    with pytest.raises(KeyError):
        codec.encode({"sheets": []})


def test_version_index_codec_preserves_legacy_list_payload():
    versions = [
        {
            "version_id": "v1",
            "filename": "upload.xlsx",
            "uploaded_at": "2026-06-04T00:00:00Z",
            "is_active": True,
            "sheet_count": 1,
            "total_rows": 1,
        }
    ]
    codec = VersionIndexDocumentCodec("gn")

    record = codec.encode(versions)

    assert record == StoredDocument(
        id="gn-versions-index",
        payload=versions,
        partition_value="gn",
    )
    assert isinstance(record.payload, list)
    assert "id" not in record.payload[0]
    assert codec.decode(record) == versions


def test_version_index_codec_can_target_legacy_versions_filename():
    codec = VersionIndexDocumentCodec("gn", record_id="versions")

    record = codec.encode([])

    assert record == StoredDocument(id="versions", payload=[], partition_value="gn")


def test_version_index_codec_rejects_non_list_payload():
    codec = VersionIndexDocumentCodec("hr")

    with pytest.raises(TypeError):
        codec.decode(StoredDocument(id="hr-versions-index", payload={"versions": []}))
