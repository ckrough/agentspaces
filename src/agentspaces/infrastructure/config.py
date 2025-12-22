"""Global configuration persistence.

Handles reading and writing global config.json with schema versioning
and atomic write operations.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import structlog

from agentspaces.infrastructure.paths import PathResolver, default_resolver

__all__ = [
    "ConfigError",
    "GlobalConfig",
    "load_global_config",
    "save_global_config",
]

logger = structlog.get_logger()

# Current schema version - increment when making breaking changes
# v1: Initial schema with plan_mode_by_default
SCHEMA_VERSION = "1"

# Maximum config file size (1MB - same as metadata)
MAX_CONFIG_SIZE = 1 * 1024 * 1024


class ConfigError(Exception):
    """Raised when configuration operations fail."""


@dataclass(frozen=True)
class GlobalConfig:
    """Immutable global configuration for agentspaces.

    Attributes:
        plan_mode_by_default: When true, automatically use --permission-mode plan
            for agent launches unless overridden with --no-plan-mode.
    """

    plan_mode_by_default: bool = False


def save_global_config(
    config: GlobalConfig, resolver: PathResolver | None = None
) -> None:
    """Save global configuration to a JSON file.

    Uses atomic write (temp file + rename) to prevent corruption.

    Args:
        config: Configuration to save.
        resolver: Path resolver (defaults to default_resolver).

    Raises:
        ConfigError: If saving fails.
    """
    if resolver is None:
        resolver = default_resolver

    path = resolver.global_config()
    data = _config_to_dict(config)

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
            json.dump(data, tmp, indent=2)
            tmp_path = Path(tmp.name)

        # Atomic rename
        tmp_path.replace(path)

        logger.debug("config_saved", path=str(path))

    except OSError as e:
        # Clean up temp file if rename failed
        if "tmp_path" in locals():
            tmp_path.unlink(missing_ok=True)
        raise ConfigError(f"Failed to save config: {e}") from e


def load_global_config(resolver: PathResolver | None = None) -> GlobalConfig:
    """Load global configuration from a JSON file.

    Gracefully handles missing files, invalid JSON, and oversized files.
    Returns default config if file doesn't exist or is invalid.

    Args:
        resolver: Path resolver (defaults to default_resolver).

    Returns:
        GlobalConfig instance (uses defaults if file missing or invalid).
    """
    if resolver is None:
        resolver = default_resolver

    path = resolver.global_config()

    if not path.exists():
        logger.debug("config_not_found", path=str(path))
        return GlobalConfig()

    try:
        # Check file size before reading to prevent DoS
        file_size = path.stat().st_size
        if file_size > MAX_CONFIG_SIZE:
            logger.warning(
                "config_too_large",
                path=str(path),
                size=file_size,
                max_size=MAX_CONFIG_SIZE,
            )
            return GlobalConfig()

        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Check schema version
        version = data.get("version")
        if version and version != SCHEMA_VERSION:
            logger.warning(
                "config_version_mismatch",
                path=str(path),
                expected=SCHEMA_VERSION,
                found=version,
            )
            # Still try to load - be forward-compatible

        return _dict_to_config(data)

    except json.JSONDecodeError as e:
        logger.warning("config_invalid_json", path=str(path), error=str(e))
        return GlobalConfig()
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("config_parse_error", path=str(path), error=str(e))
        return GlobalConfig()
    except OSError as e:
        logger.warning("config_read_error", path=str(path), error=str(e))
        return GlobalConfig()


def _config_to_dict(config: GlobalConfig) -> dict[str, Any]:
    """Convert config to JSON-serializable dict.

    Args:
        config: GlobalConfig to convert.

    Returns:
        Dict with version field.
    """
    data = asdict(config)
    data["version"] = SCHEMA_VERSION
    return data


def _dict_to_config(data: dict[str, Any]) -> GlobalConfig:
    """Convert dict to GlobalConfig.

    Args:
        data: Dict from JSON.

    Returns:
        GlobalConfig instance.

    Raises:
        KeyError: If required fields are missing.
        TypeError: If field has invalid type.
    """
    return GlobalConfig(
        plan_mode_by_default=data.get("plan_mode_by_default", False),
    )
