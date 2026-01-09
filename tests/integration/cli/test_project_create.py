"""Integration tests for project create command."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from agentspaces.cli.app import app
from tests.integration.cli.conftest import runner

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.mark.integration
class TestProjectCreateBasic:
    """Tests for basic project creation scenarios."""

    def test_create_in_empty_directory(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should create skeleton in empty directory and init git."""
        chdir_to(empty_dir)

        result = invoke_project_create()

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Project Created" in result.output
        # Git was initialized
        assert (empty_dir / ".git").is_dir()
        # Skeleton files exist
        assert (empty_dir / "README.md").exists()
        assert (empty_dir / "CLAUDE.md").exists()
        assert (empty_dir / ".claude" / "agents" / "README.md").exists()
        assert (empty_dir / ".claude" / "commands" / "README.md").exists()
        assert (empty_dir / "docs" / "design" / "architecture.md").exists()
        assert (empty_dir / "docs" / "design" / "development-standards.md").exists()
        # ADR example is created (no required variables)
        assert (empty_dir / "docs" / "adr" / "001-example.md").exists()
        # Note: 000-template.md may fail if template has required variables not provided

    def test_create_in_existing_git_repo(
        self,
        empty_git_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should create skeleton without re-initializing git."""
        chdir_to(empty_git_dir)

        result = invoke_project_create()

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Git was NOT re-initialized (no message about it)
        assert "Initialized git" not in result.output
        # But files were created
        assert (empty_git_dir / "README.md").exists()
        assert (empty_git_dir / "CLAUDE.md").exists()

    def test_create_with_python_flag(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should create Python language pack files with --python flag."""
        chdir_to(empty_dir)

        result = invoke_project_create("--python", name="MyPythonApp")

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Python pack files exist
        assert (empty_dir / "pyproject.toml").exists()
        assert (empty_dir / ".gitignore").exists()
        assert (empty_dir / ".python-version").exists()
        assert (empty_dir / ".pre-commit-config.yaml").exists()
        assert (empty_dir / ".github" / "workflows" / "ci.yml").exists()
        # Package structure with derived name
        assert (empty_dir / "src" / "mypythonapp" / "__init__.py").exists()
        assert (empty_dir / "tests" / "conftest.py").exists()


@pytest.mark.integration
class TestProjectCreatePythonPackageNaming:
    """Tests for Python package name derivation."""

    @pytest.mark.parametrize(
        ("project_name", "expected_package"),
        [
            ("My Project", "my_project"),
            ("CLI-Tool", "cli_tool"),
            ("api", "api"),
            ("123App", "pkg_123app"),  # Can't start with number
            ("for", "for_pkg"),  # Python keyword
        ],
    )
    def test_package_name_derivation(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        project_name: str,
        expected_package: str,
    ) -> None:
        """Should derive valid Python package name from project name."""
        chdir_to(empty_dir)

        result = runner.invoke(
            app,
            [
                "project",
                "create",
                "--python",
                "-y",
                "-n",
                project_name,
                "-d",
                "Test",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert (empty_dir / "src" / expected_package / "__init__.py").exists()

    def test_custom_python_version(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should use specified Python version in generated files."""
        chdir_to(empty_dir)

        result = invoke_project_create(
            "--python",
            "--python-version",
            "3.12",
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        pyproject = (empty_dir / "pyproject.toml").read_text()
        assert ">=3.12" in pyproject
        python_version = (empty_dir / ".python-version").read_text()
        assert "3.12" in python_version


@pytest.mark.integration
class TestProjectCreateErrors:
    """Tests for error conditions."""

    def test_fails_in_non_empty_directory(
        self,
        non_empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should fail if directory contains non-git files."""
        chdir_to(non_empty_dir)

        result = invoke_project_create()

        assert result.exit_code == 1
        # Error message suggests creating a new directory
        assert "directory" in result.output.lower()

    def test_allows_directory_with_only_git(
        self,
        empty_git_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should allow creation in dir with only .git directory."""
        chdir_to(empty_git_dir)

        result = invoke_project_create()

        assert result.exit_code == 0

    def test_respects_confirmation_prompt_no(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
    ) -> None:
        """Should abort when user declines confirmation."""
        chdir_to(empty_dir)

        result = runner.invoke(
            app,
            ["project", "create", "-n", "Test", "-d", "Desc"],
            input="n\n",
        )

        assert result.exit_code == 0  # Clean exit
        assert "Cancelled" in result.output
        assert not (empty_dir / "README.md").exists()


@pytest.mark.integration
class TestProjectCreateContent:
    """Tests for generated file content."""

    def test_readme_contains_project_info(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Generated README should contain project name and description."""
        chdir_to(empty_dir)

        invoke_project_create(name="AwesomeApp", description="Does amazing things")

        readme = (empty_dir / "README.md").read_text()
        assert "AwesomeApp" in readme
        assert "Does amazing things" in readme

    def test_claude_md_contains_project_name(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Generated CLAUDE.md should reference project name."""
        chdir_to(empty_dir)

        invoke_project_create(name="TestProject")

        claude_md = (empty_dir / "CLAUDE.md").read_text()
        assert "TestProject" in claude_md

    def test_pyproject_contains_project_metadata(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Generated pyproject.toml should have correct metadata."""
        chdir_to(empty_dir)

        invoke_project_create(
            "--python",
            name="My CLI Tool",
            description="A command line tool",
        )

        pyproject = (empty_dir / "pyproject.toml").read_text()
        # Name uses project_name variable
        assert "my_cli_tool" in pyproject.lower() or "my-cli-tool" in pyproject.lower()
        assert "A command line tool" in pyproject

    def test_files_have_valid_frontmatter(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Markdown files should have valid YAML frontmatter."""
        chdir_to(empty_dir)

        invoke_project_create()

        # Check a sample of generated files
        for md_file in [
            empty_dir / "README.md",
            empty_dir / "CLAUDE.md",
            empty_dir / "docs" / "design" / "architecture.md",
        ]:
            content = md_file.read_text()
            assert content.startswith("---\n"), f"{md_file} missing frontmatter"
            # Find end of frontmatter
            end = content.find("\n---\n", 4)
            assert end > 0, f"{md_file} has unclosed frontmatter"


@pytest.mark.integration
class TestProjectCreateGitIntegration:
    """Tests for git-related behavior."""

    def test_git_init_creates_valid_repo(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Git init should create a valid repository."""
        chdir_to(empty_dir)

        invoke_project_create()

        # Verify it's a valid git repo
        result = subprocess.run(
            ["git", "status"],
            cwd=empty_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0

    def test_generated_files_are_untracked(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Generated files should be untracked (ready for initial commit)."""
        chdir_to(empty_dir)

        invoke_project_create()

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=empty_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        # All files should be untracked (??)
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line:  # Skip empty lines
                assert line.startswith("??"), f"Unexpected status: {line}"

    def test_does_not_modify_existing_git_config(
        self,
        empty_git_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should not modify existing git configuration."""
        chdir_to(empty_git_dir)

        # Get config before
        before = subprocess.run(
            ["git", "config", "--local", "--list"],
            cwd=empty_git_dir,
            capture_output=True,
            text=True,
            check=False,
        ).stdout

        invoke_project_create()

        # Get config after
        after = subprocess.run(
            ["git", "config", "--local", "--list"],
            cwd=empty_git_dir,
            capture_output=True,
            text=True,
            check=False,
        ).stdout

        assert before == after


@pytest.mark.integration
class TestProjectCreateEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_handles_special_characters_in_project_name(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should handle special characters in project name."""
        chdir_to(empty_dir)

        result = invoke_project_create(
            name="Project (Alpha) - v1.0",
            description="Test",
        )

        assert result.exit_code == 0
        assert (empty_dir / "README.md").exists()

    def test_handles_long_project_name(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should handle very long project names."""
        chdir_to(empty_dir)

        long_name = "A" * 200
        result = invoke_project_create(name=long_name)

        assert result.exit_code == 0
        readme = (empty_dir / "README.md").read_text()
        assert long_name in readme

    def test_handles_unicode_in_description(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should handle unicode characters in description."""
        chdir_to(empty_dir)

        result = invoke_project_create(
            description="A project for handling emoji and unicode: café, naïve",
        )

        assert result.exit_code == 0
        readme = (empty_dir / "README.md").read_text()
        assert "café" in readme
        assert "naïve" in readme

    def test_creates_nested_directories(
        self,
        empty_dir: Path,
        chdir_to: Callable[[Path], None],
        invoke_project_create: Callable[..., Any],
    ) -> None:
        """Should create deeply nested directory structures."""
        chdir_to(empty_dir)

        invoke_project_create("--python")

        # Verify nested structure
        assert (empty_dir / ".github" / "workflows" / "ci.yml").exists()
        assert (empty_dir / "docs" / "design" / "architecture.md").exists()
        assert (empty_dir / "docs" / "adr" / "001-example.md").exists()
