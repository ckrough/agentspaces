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
SCHEMA_VERSION = "1"

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
        Dict with version field and ISO 8601 timestamp.
    """
    data = asdict(metadata)

    # Add schema version
    data["version"] = SCHEMA_VERSION

    # Convert datetime to ISO 8601 string
    if isinstance(data["created_at"], datetime):
        data["created_at"] = data["created_at"].isoformat()

    return data


def _dict_to_metadata(data: dict[str, Any]) -> WorkspaceMetadata:
    """Convert dict to WorkspaceMetadata.

    Args:
        data: Dict from JSON.

    Returns:
        WorkspaceMetadata instance.

    Raises:
        KeyError: If required fields are missing.
        ValueError: If datetime format is invalid.
        TypeError: If created_at has invalid type.
    """
    # Parse datetime from ISO 8601 string
    created_at = data["created_at"]
    if isinstance(created_at, str):
        # Handle both timezone-aware and naive timestamps
        created_at = datetime.fromisoformat(created_at)
        # Ensure UTC if no timezone specified
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
    elif isinstance(created_at, datetime):
        # Already a datetime object
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
    else:
        raise TypeError(
            f"Invalid created_at type: {type(created_at).__name__}. "
            "Expected str or datetime."
        )

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
