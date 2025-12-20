"""Path resolution for AgentSpaces storage."""

from __future__ import annotations

from pathlib import Path


class PathResolver:
    """Resolves paths for AgentSpaces storage.

    Storage layout:
        ~/.agentspaces/
        ├── config.json
        └── <project>/
            └── <workspace-name>/
                ├── .agentspace/
                │   ├── workspace.json
                │   ├── skills/
                │   │   └── workspace-context/
                │   │       └── SKILL.md
                │   └── sessions/
                ├── .venv/
                └── <project files>
    """

    def __init__(self, base: Path | None = None) -> None:
        """Initialize path resolver.

        Args:
            base: Base directory for storage. Defaults to ~/.agentspaces.
        """
        self.base = base or Path.home() / ".agentspaces"

    def ensure_base(self) -> Path:
        """Ensure base directory exists and return it."""
        self.base.mkdir(parents=True, exist_ok=True)
        return self.base

    def global_config(self) -> Path:
        """Path to global configuration file."""
        return self.base / "config.json"

    def project_dir(self, project: str) -> Path:
        """Directory for a specific project.

        Args:
            project: Project/repository name.
        """
        return self.base / project

    def workspace_dir(self, project: str, workspace: str) -> Path:
        """Directory for a specific workspace (git worktree location).

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.project_dir(project) / workspace

    def metadata_dir(self, project: str, workspace: str) -> Path:
        """Metadata directory within a workspace.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.workspace_dir(project, workspace) / ".agentspace"

    def workspace_json(self, project: str, workspace: str) -> Path:
        """Workspace metadata file.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.metadata_dir(project, workspace) / "workspace.json"

    def skills_dir(self, project: str, workspace: str) -> Path:
        """Skills directory within a workspace.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.metadata_dir(project, workspace) / "skills"

    def workspace_context_skill(self, project: str, workspace: str) -> Path:
        """Path to workspace-context skill directory.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.skills_dir(project, workspace) / "workspace-context"

    def sessions_dir(self, project: str, workspace: str) -> Path:
        """Sessions directory within a workspace.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.metadata_dir(project, workspace) / "sessions"

    def session_dir(self, project: str, workspace: str, session_id: str) -> Path:
        """Directory for a specific session.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
            session_id: Session identifier.
        """
        return self.sessions_dir(project, workspace) / session_id

    def venv_dir(self, project: str, workspace: str) -> Path:
        """Virtual environment directory.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.workspace_dir(project, workspace) / ".venv"

    def workspace_exists(self, project: str, workspace: str) -> bool:
        """Check if a workspace exists.

        Args:
            project: Project/repository name.
            workspace: Workspace name.
        """
        return self.workspace_dir(project, workspace).exists()

    def list_workspaces(self, project: str) -> list[str]:
        """List all workspaces for a project.

        Args:
            project: Project/repository name.

        Returns:
            List of workspace names.
        """
        project_path = self.project_dir(project)
        if not project_path.exists():
            return []

        return [
            d.name
            for d in project_path.iterdir()
            if d.is_dir() and (d / ".agentspace").exists()
        ]

    def list_projects(self) -> list[str]:
        """List all projects.

        Returns:
            List of project names.
        """
        if not self.base.exists():
            return []

        return [
            d.name
            for d in self.base.iterdir()
            if d.is_dir() and d.name != "config.json"
        ]


# Default resolver instance
default_resolver = PathResolver()
