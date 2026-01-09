"""Textual widgets for workspace TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container, Horizontal  # type: ignore[import-not-found]
from textual.screen import ModalScreen  # type: ignore[import-not-found]
from textual.widgets import (  # type: ignore[import-not-found]
    Button,
    DataTable,
    Footer,
    Header,
    Static,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from agentspaces.modules.workspace.service import WorkspaceInfo

__all__ = [
    "ConfirmRemoveModal",
    "PreviewPanel",
    "WorkspaceFooter",
    "WorkspaceHeader",
    "WorkspaceTable",
]


class WorkspaceTable(DataTable):
    """Interactive table showing workspaces with metadata.

    Displays: name, branch, purpose (truncated), venv indicator.
    Supports keyboard navigation and multi-select.
    """

    def __init__(self) -> None:
        """Initialize workspace table with columns."""
        super().__init__(zebra_stripes=True, cursor_type="row")

        # Configure columns
        self.add_column("Name", key="name", width=25)
        self.add_column("Branch", key="branch", width=25)
        self.add_column("Purpose", key="purpose", width=40)
        self.add_column("Venv", key="venv", width=6)

    def load_workspaces(
        self,
        workspaces: list[WorkspaceInfo],
        current_path: str | None = None,
    ) -> None:
        """Load workspaces into table.

        Args:
            workspaces: List of workspace info objects.
            current_path: Path of current workspace (will be highlighted).
        """
        self.clear()

        for workspace in workspaces:
            # Visual indicators
            name_display = workspace.name
            if current_path and str(workspace.path) == current_path:
                name_display = f"→ {name_display}"

            venv_display = "✓" if workspace.has_venv else ""
            purpose_display = self._truncate(workspace.purpose or "", 38)

            self.add_row(
                name_display,
                workspace.branch,
                purpose_display,
                venv_display,
                key=workspace.name,
            )

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        """Truncate text with ellipsis if too long."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 1] + "…"


class PreviewPanel(Static):
    """Preview panel showing workspace details."""

    def __init__(self) -> None:
        """Initialize preview panel."""
        super().__init__()
        self.border_title = "Workspace Details"
        self.update_preview(None)

    def update_preview(self, workspace: WorkspaceInfo | None) -> None:
        """Update preview with workspace details.

        Args:
            workspace: Workspace to preview, or None to show empty state.
        """
        if workspace is None:
            self.update("[dim]No workspace selected[/dim]")
            return

        # Format creation time
        created = "Unknown"
        if workspace.created_at:
            created = workspace.created_at.strftime("%Y-%m-%d %H:%M")

        # Build preview content
        lines = [
            f"[bold cyan]{workspace.name}[/bold cyan]",
            "",
            f"[bold]Path:[/bold] {workspace.path}",
            f"[bold]Branch:[/bold] {workspace.branch}",
            f"[bold]Base:[/bold] {workspace.base_branch}",
            f"[bold]Created:[/bold] {created}",
            "",
            f"[bold]Python:[/bold] {workspace.python_version or 'N/A'}",
            f"[bold]Venv:[/bold] {'Yes ✓' if workspace.has_venv else 'No'}",
        ]

        if workspace.purpose:
            lines.extend(["", "[bold]Purpose:[/bold]", f"{workspace.purpose}"])

        self.update("\n".join(lines))


class WorkspaceHeader(Header):
    """Header showing main repository checkout info."""

    def __init__(self, main_checkout: WorkspaceInfo | None = None) -> None:
        """Initialize header.

        Args:
            main_checkout: Main repository checkout info (protected from removal).
        """
        super().__init__()
        self._main_checkout = main_checkout
        self._update_title()

    def set_main_checkout(self, main_checkout: WorkspaceInfo | None) -> None:
        """Update main checkout display.

        Args:
            main_checkout: Main repository checkout info.
        """
        self._main_checkout = main_checkout
        self._update_title()

    def _update_title(self) -> None:
        """Update header title with main checkout info."""
        if self._main_checkout:
            project = self._main_checkout.project
            branch = self._main_checkout.branch
            self.tall_title = True
            self._text = f"agentspaces  •  Main: {project} ({branch})"
        else:
            self._text = "agentspaces"


class WorkspaceFooter(Footer):
    """Footer showing keybindings."""

    pass  # Uses Textual's built-in Footer with app BINDINGS


class ConfirmRemoveModal(ModalScreen[bool]):
    """Modal dialog for confirming workspace removal.

    Returns True if user confirms, False if cancelled.
    """

    DEFAULT_CSS = """
    ConfirmRemoveModal {
        align: center middle;
    }

    ConfirmRemoveModal > Container {
        width: 60;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    ConfirmRemoveModal #buttons {
        height: auto;
        align: center middle;
        padding-top: 1;
    }

    ConfirmRemoveModal Button {
        margin: 0 1;
    }
    """

    def __init__(self, workspace_names: list[str]) -> None:
        """Initialize modal with workspace names to confirm.

        Args:
            workspace_names: List of workspace names to be removed.
        """
        super().__init__()
        self.workspace_names = workspace_names

    def compose(self) -> ComposeResult:
        """Compose modal layout."""
        with Container():
            yield Static(
                "[bold red]⚠ Remove Workspaces?[/bold red]\n\n"
                "This will delete the following workspaces:\n"
                + "\n".join(f"  • {name}" for name in self.workspace_names)
                + "\n\n[yellow]This action cannot be undone![/yellow]"
            )

            with Horizontal(id="buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Remove", variant="error", id="confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks.

        Args:
            event: Button press event.
        """
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)
