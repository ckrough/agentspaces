"""UI module for agentspaces TUI."""

from agentspaces.ui.app import WorkspacesTUI
from agentspaces.ui.terminal import detect_terminal
from agentspaces.ui.widgets import (
    ConfirmRemoveModal,
    PreviewPanel,
    WorkspaceFooter,
    WorkspaceHeader,
    WorkspaceTable,
)

__all__ = [
    "ConfirmRemoveModal",
    "PreviewPanel",
    "WorkspaceFooter",
    "WorkspaceHeader",
    "WorkspaceTable",
    "WorkspacesTUI",
    "detect_terminal",
]
