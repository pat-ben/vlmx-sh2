"""Textual UI application."""

from textual.app import App

from ..core.models.context import Context
from ..core.enums.core import ContextLevel
from .screens import MainScreen


class VLMX(App):
    """VLMX-SH: A command-line style app for managing companies and financial data."""

    CSS_PATH = "styles/design.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = Context(level=ContextLevel.SYS)

    def on_mount(self) -> None:
        """Push the main screen when app mounts."""
        self.push_screen(MainScreen(self.context))

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )