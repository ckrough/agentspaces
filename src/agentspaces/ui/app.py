"""Textual application for workspace management."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import structlog
from textual import work
from textual.app import App
from textual.binding import Binding
from textual.widgets import DataTable, Footer

if TYPE_CHECKING:
    from textual.app import ComposeResult

from agentspaces.modules.workspace.service import (
    WorkspaceError,
    WorkspaceInfo,
    WorkspaceNotFoundError,
    WorkspaceService,
)
from agentspaces.ui.terminal import detect_terminal, navigate_to_workspace
from agentspaces.ui.widgets import (
    ConfirmRemoveModal,
    PreviewPanel,
    WorkspaceHeader,
    WorkspaceTable,
)

__all__ = ["WorkspacesTUI"]

logger = structlog.get_logger()


class WorkspacesTUI(App[None]):
    """Interactive TUI for workspace management.

    Features:
    - Browse workspaces with arrow keys
    - Navigate to workspace (CD + activate venv + start claude)
    - Remove single or multiple workspaces
    - Preview workspace details before actions
    """

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-rows: auto 1fr;
        grid-columns: 2fr 1fr;
    }

    Header {
        column-span: 2;
    }

    WorkspaceTable {
        height: 100%;
        border: solid $primary;
    }

    PreviewPanel {
        height: 100%;
        border: solid $accent;
        padding: 1 2;
    }

    Footer {
        column-span: 2;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [  # type: ignore[assignment]
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "navigate", "Navigate"),
        Binding("d", "remove", "Remove"),
        Binding("space", "toggle_select", "Select"),
    ]

    TITLE = "agentspaces"

    def __init__(self, service: WorkspaceService | None = None) -> None:
        """Initialize TUI with service dependencies.

        Args:
            service: Workspace service instance (optional, for testing).
        """
        super().__init__()

        # Dependency injection
        self.service = service or WorkspaceService()
        self.workspaces: list[WorkspaceInfo] = []
        self.main_checkout: WorkspaceInfo | None = None
        self.current_path = str(Path.cwd())
        self.selected_rows: set[int] = set()

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield WorkspaceHeader()
        yield WorkspaceTable()
        yield PreviewPanel()
        yield Footer()

    def on_mount(self) -> None:
        """Load initial data when app starts."""
        self.action_refresh()

    def action_refresh(self) -> None:
        """Refresh workspace list from service."""
        # Clear selections since indices will be invalid after reload
        self.selected_rows.clear()

        try:
            all_workspaces = self.service.list()

            # Separate main checkout (first worktree with is_main flag)
            # Main is determined by matching workspace name to project name
            project = self.service.get_project_name()
            main = next(
                (w for w in all_workspaces if w.name == project),
                None,
            )

            # Filter out main from actionable list
            self.workspaces = [w for w in all_workspaces if w != main]
            self.main_checkout = main

            # Update UI
            table = self.query_one(WorkspaceTable)
            table.load_workspaces(self.workspaces, self.current_path)

            header = self.query_one(WorkspaceHeader)
            header.set_main_checkout(main)

            # Update preview with first workspace
            if self.workspaces:
                preview = self.query_one(PreviewPanel)
                preview.update_preview(self.workspaces[0])

            logger.info(
                "workspaces_loaded",
                count=len(self.workspaces),
                has_main=main is not None,
            )

        except WorkspaceError as e:
            self.notify(f"Error loading workspaces: {e}", severity="error")
            logger.error("workspace_load_failed", error=str(e))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update preview when cursor moves.

        Args:
            event: Row highlighted event from DataTable.
        """
        if 0 <= event.cursor_row < len(self.workspaces):
            workspace = self.workspaces[event.cursor_row]
            preview = self.query_one(PreviewPanel)
            preview.update_preview(workspace)

    def action_toggle_select(self) -> None:
        """Toggle selection of current row."""
        table = self.query_one(WorkspaceTable)
        cursor_row = table.cursor_row

        # Bounds check before operating on selection
        if cursor_row < 0 or cursor_row >= len(self.workspaces):
            return

        if cursor_row in self.selected_rows:
            self.selected_rows.remove(cursor_row)
        else:
            self.selected_rows.add(cursor_row)

        # Visual feedback
        self.notify(f"Selected: {len(self.selected_rows)} workspace(s)")

    async def action_navigate(self) -> None:
        """Navigate to selected workspace."""
        table = self.query_one(WorkspaceTable)
        cursor_row = table.cursor_row

        if cursor_row < 0 or cursor_row >= len(self.workspaces):
            return

        workspace = self.workspaces[cursor_row]

        # Check if Ghostty is available before attempting
        is_ghostty, _ = detect_terminal()

        if is_ghostty:
            self.notify(
                f"Opening {workspace.name} in new Ghostty tab...",
                severity="information",
            )
        else:
            self.notify(
                "Ghostty not detected - check console for commands",
                severity="warning",
            )

        # Navigate (Ghostty tab or print instructions)
        navigate_to_workspace(workspace)

    @work()
    async def action_remove(self) -> None:
        """Remove selected workspace(s) after confirmation."""
        # Determine which workspaces to remove
        workspaces_to_remove = []

        if self.selected_rows:
            # Remove all selected
            workspaces_to_remove = [
                self.workspaces[i]
                for i in self.selected_rows
                if i < len(self.workspaces)
            ]
        else:
            # Remove current cursor row
            table = self.query_one(WorkspaceTable)
            cursor_row = table.cursor_row
            if cursor_row < len(self.workspaces):
                workspaces_to_remove = [self.workspaces[cursor_row]]

        if not workspaces_to_remove:
            self.notify("No workspace selected", severity="warning")
            return

        # Check for protected workspaces
        protected = []
        current_cwd = str(Path.cwd())  # Get fresh current directory

        for workspace in workspaces_to_remove:
            # Block removal of current workspace
            if str(workspace.path) == current_cwd:
                protected.append(f"{workspace.name} (current workspace)")

        if protected:
            message = "Cannot remove:\n" + "\n".join(
                f"  • {name}" for name in protected
            )
            self.notify(message, severity="error")
            return

        # Show confirmation modal
        workspace_names = [w.name for w in workspaces_to_remove]
        confirmed = await self.push_screen_wait(ConfirmRemoveModal(workspace_names))

        if not confirmed:
            self.notify("Removal cancelled", severity="information")
            return

        # Execute removal
        removed_count = 0
        failed = []

        for workspace in workspaces_to_remove:
            try:
                self.service.remove(workspace.name, force=False)
                removed_count += 1
                logger.info("workspace_removed", name=workspace.name)
            except WorkspaceNotFoundError:
                failed.append(f"{workspace.name} (not found)")
            except WorkspaceError as e:
                failed.append(f"{workspace.name} ({e})")
                logger.error(
                    "workspace_removal_failed",
                    workspace=workspace.name,
                    error=str(e),
                )

        # Clear selection
        self.selected_rows.clear()

        # Refresh list
        self.action_refresh()

        # Notify user
        if removed_count > 0:
            self.notify(
                f"Removed {removed_count} workspace(s)",
                severity="information",
            )

        if failed:
            message = "Failed to remove:\n" + "\n".join(
                f"  • {name}" for name in failed
            )
            self.notify(message, severity="error")
