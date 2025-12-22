"""Tests for global configuration module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from agentspaces.infrastructure.config import (
    GlobalConfig,
    load_global_config,
    save_global_config,
)
from agentspaces.infrastructure.paths import PathResolver

if TYPE_CHECKING:
    from pathlib import Path


class TestGlobalConfig:
    """Tests for GlobalConfig dataclass."""

    def test_config_is_frozen(self) -> None:
        """GlobalConfig should be immutable."""
        config = GlobalConfig()

        with pytest.raises((AttributeError, TypeError)):  # Frozen dataclass error
            config.plan_mode_by_default = True  # type: ignore

    def test_config_defaults(self) -> None:
        """Should have sensible defaults."""
        config = GlobalConfig()

        assert config.plan_mode_by_default is False

    def test_config_can_be_created_with_values(self) -> None:
        """Can create config with custom values."""
        config = GlobalConfig(plan_mode_by_default=True)

        assert config.plan_mode_by_default is True


class TestLoadGlobalConfig:
    """Tests for load_global_config function."""

    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        """Returns default config when file doesn't exist."""
        resolver = PathResolver(base=tmp_path)

        config = load_global_config(resolver)

        assert isinstance(config, GlobalConfig)
        assert config.plan_mode_by_default is False

    def test_loads_config_from_file(self, tmp_path: Path) -> None:
        """Loads configuration from JSON file."""
        resolver = PathResolver(base=tmp_path)
        config_path = resolver.global_config()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_path.write_text(
            json.dumps(
                {
                    "version": "1",
                    "plan_mode_by_default": True,
                }
            )
        )

        config = load_global_config(resolver)

        assert config.plan_mode_by_default is True

    def test_handles_invalid_json(self, tmp_path: Path) -> None:
        """Returns defaults on invalid JSON."""
        resolver = PathResolver(base=tmp_path)
        config_path = resolver.global_config()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_path.write_text("not valid json {")

        config = load_global_config(resolver)

        # Should return defaults, not raise
        assert isinstance(config, GlobalConfig)
        assert config.plan_mode_by_default is False

    def test_handles_schema_version_mismatch(self, tmp_path: Path) -> None:
        """Handles schema version mismatches gracefully."""
        resolver = PathResolver(base=tmp_path)
        config_path = resolver.global_config()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Future version
        config_path.write_text(
            json.dumps(
                {
                    "version": "999",
                    "plan_mode_by_default": True,
                }
            )
        )

        config = load_global_config(resolver)

        # Should still try to load
        assert config.plan_mode_by_default is True

    def test_rejects_oversized_file(self, tmp_path: Path) -> None:
        """Rejects files over MAX_CONFIG_SIZE."""
        resolver = PathResolver(base=tmp_path)
        config_path = resolver.global_config()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a file > 1MB
        large_content = "x" * (1024 * 1024 + 1)
        config_path.write_text(large_content)

        config = load_global_config(resolver)

        # Should return defaults
        assert isinstance(config, GlobalConfig)
        assert config.plan_mode_by_default is False

    def test_handles_missing_fields_with_defaults(self, tmp_path: Path) -> None:
        """Uses defaults for missing fields."""
        resolver = PathResolver(base=tmp_path)
        config_path = resolver.global_config()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Config with no plan_mode_by_default field
        config_path.write_text(json.dumps({"version": "1"}))

        config = load_global_config(resolver)

        assert config.plan_mode_by_default is False


class TestSaveGlobalConfig:
    """Tests for save_global_config function."""

    def test_saves_config_atomically(self, tmp_path: Path) -> None:
        """Saves config using atomic write."""
        resolver = PathResolver(base=tmp_path)
        config = GlobalConfig(plan_mode_by_default=True)

        save_global_config(config, resolver)

        # Config should exist
        config_path = resolver.global_config()
        assert config_path.exists()

        # Should be valid JSON
        data = json.loads(config_path.read_text())
        assert data["plan_mode_by_default"] is True

    def test_includes_schema_version(self, tmp_path: Path) -> None:
        """Saved JSON includes version field."""
        resolver = PathResolver(base=tmp_path)
        config = GlobalConfig()

        save_global_config(config, resolver)

        config_path = resolver.global_config()
        data = json.loads(config_path.read_text())

        assert "version" in data
        assert data["version"] == "1"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Creates parent directory if it doesn't exist."""
        resolver = PathResolver(base=tmp_path / "nonexistent")
        config = GlobalConfig()

        save_global_config(config, resolver)

        config_path = resolver.global_config()
        assert config_path.exists()
        assert config_path.parent.exists()

    def test_overwrites_existing_config(self, tmp_path: Path) -> None:
        """Overwrites existing config file."""
        resolver = PathResolver(base=tmp_path)

        # Save initial config
        config1 = GlobalConfig(plan_mode_by_default=False)
        save_global_config(config1, resolver)

        # Save updated config
        config2 = GlobalConfig(plan_mode_by_default=True)
        save_global_config(config2, resolver)

        # Should have new value
        loaded = load_global_config(resolver)
        assert loaded.plan_mode_by_default is True


class TestGlobalConfigRoundTrip:
    """Tests for save/load round trip."""

    def test_save_then_load(self, tmp_path: Path) -> None:
        """Can save and load config."""
        resolver = PathResolver(base=tmp_path)
        config = GlobalConfig(plan_mode_by_default=True)

        save_global_config(config, resolver)
        loaded = load_global_config(resolver)

        assert loaded.plan_mode_by_default == config.plan_mode_by_default

    def test_multiple_save_load_cycles(self, tmp_path: Path) -> None:
        """Multiple save/load cycles work correctly."""
        resolver = PathResolver(base=tmp_path)

        # Cycle 1: False
        config1 = GlobalConfig(plan_mode_by_default=False)
        save_global_config(config1, resolver)
        loaded1 = load_global_config(resolver)
        assert loaded1.plan_mode_by_default is False

        # Cycle 2: True
        config2 = GlobalConfig(plan_mode_by_default=True)
        save_global_config(config2, resolver)
        loaded2 = load_global_config(resolver)
        assert loaded2.plan_mode_by_default is True

        # Cycle 3: Back to False
        config3 = GlobalConfig(plan_mode_by_default=False)
        save_global_config(config3, resolver)
        loaded3 = load_global_config(resolver)
        assert loaded3.plan_mode_by_default is False
