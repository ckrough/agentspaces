"""Workspace metadata persistence.

Handles reading and writing workspace.json files with schema versioning
and atomic write operations.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

__all__ = [
    "MetadataError",
    "WorkspaceMetadata",
    "load_workspace_metadata",
    "save_workspace_metadata",
]

logger = structlog.get_logger()

# Current schema version - increment when making breaking changes
# v1: Initial schema
# v2: Added deps_synced_at and last_activity_at fields (removed in v3)
# v3: Removed unused timestamp fields (deps_synced_at, last_activity_at)
SCHEMA_VERSION = "3"

# Maximum metadata file size (1MB - generous for workspace metadata)
MAX_METADATA_SIZE = 1 * 1024 * 1024


class MetadataError(Exception):
    """Raised when metadata operations fail."""


@dataclass(frozen=True)
class WorkspaceMetadata:
    """Immutable workspace metadata for persistence.

    Attributes:
        name: Workspace name (e.g., "eager-turing").
        project: Project/repository name.
        branch: Git branch name (same as workspace name).
        base_branch: Branch the workspace was created from.
        created_at: Timestamp when workspace was created.
        purpose: User-provided description of workspace purpose.
        python_version: Python version used for venv.
        has_venv: Whether a virtual environment was created.
        status: Workspace status (active, archived).
    """

    name: str
    project: str
    branch: str
    base_branch: str
    created_at: datetime
    purpose: str | None = None
    python_version: str | None = None
    has_venv: bool = False
    status: str = "active"


def save_workspace_metadata(metadata: WorkspaceMetadata, path: Path) -> None:
    """Save workspace metadata to a JSON file.

    Uses atomic write (temp file + rename) to prevent corruption.

    Args:
        metadata: Metadata to save.
        path: Path to the workspace.json file.

    Raises:
        MetadataError: If saving fails.
    """
    data = _metadata_to_dict(metadata)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Atomic write: write to temp file, then rename
        # This prevents corruption if process is interrupted
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump(data, tmp, indent=2, default=str)
            tmp_path = Path(tmp.name)

        # Atomic rename
        tmp_path.replace(path)

        logger.debug("metadata_saved", path=str(path))

    except OSError as e:
        # Clean up temp file if rename failed
        if "tmp_path" in locals():
            tmp_path.unlink(missing_ok=True)
        raise MetadataError(f"Failed to save metadata: {e}") from e


def load_workspace_metadata(path: Path) -> WorkspaceMetadata | None:
    """Load workspace metadata from a JSON file.

    Gracefully handles missing files, invalid JSON, and oversized files.

    Args:
        path: Path to the workspace.json file.

    Returns:
        WorkspaceMetadata if file exists and is valid, None otherwise.
    """
    if not path.exists():
        return None

    try:
        # Check file size before reading to prevent DoS
        file_size = path.stat().st_size
        if file_size > MAX_METADATA_SIZE:
            logger.warning(
                "metadata_too_large",
                path=str(path),
                size=file_size,
                max_size=MAX_METADATA_SIZE,
            )
            return None

        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Check schema version
        version = data.get("version")
        if version and version != SCHEMA_VERSION:
            logger.warning(
                "metadata_version_mismatch",
                path=str(path),
                expected=SCHEMA_VERSION,
                found=version,
            )
            # Still try to load - be forward-compatible

        return _dict_to_metadata(data)

    except json.JSONDecodeError as e:
        logger.warning("metadata_invalid_json", path=str(path), error=str(e))
        return None
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("metadata_parse_error", path=str(path), error=str(e))
        return None
    except OSError as e:
        logger.warning("metadata_read_error", path=str(path), error=str(e))
        return None


def _metadata_to_dict(metadata: WorkspaceMetadata) -> dict[str, Any]:
    """Convert metadata to JSON-serializable dict.

    Args:
        metadata: WorkspaceMetadata to convert.

    Returns:
        Dict with version field and ISO 8601 timestamps.
    """
    data = asdict(metadata)

    # Add schema version
    data["version"] = SCHEMA_VERSION

    # Convert datetime fields to ISO 8601 strings
    if isinstance(data.get("created_at"), datetime):
        data["created_at"] = data["created_at"].isoformat()

    return data


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse a datetime from string or datetime object.

    Args:
        value: ISO 8601 string, datetime, or None.

    Returns:
        UTC-aware datetime or None.

    Raises:
        TypeError: If value has invalid type.
    """
    if value is None:
        return None

    if isinstance(value, str):
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            result = result.replace(tzinfo=UTC)
        return result

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    raise TypeError(
        f"Invalid datetime type: {type(value).__name__}. Expected str or datetime."
    )


def _dict_to_metadata(data: dict[str, Any]) -> WorkspaceMetadata:
    """Convert dict to WorkspaceMetadata.

    Args:
        data: Dict from JSON (may contain legacy fields that are ignored).

    Returns:
        WorkspaceMetadata instance.

    Raises:
        KeyError: If required fields are missing.
        ValueError: If datetime format is invalid.
        TypeError: If datetime field has invalid type.
    """
    created_at = _parse_datetime(data["created_at"])
    if created_at is None:
        raise ValueError("created_at is required and cannot be None")

    return WorkspaceMetadata(
        name=data["name"],
        project=data["project"],
        branch=data["branch"],
        base_branch=data["base_branch"],
        created_at=created_at,
        purpose=data.get("purpose"),
        python_version=data.get("python_version"),
        has_venv=data.get("has_venv", False),
        status=data.get("status", "active"),
    )
