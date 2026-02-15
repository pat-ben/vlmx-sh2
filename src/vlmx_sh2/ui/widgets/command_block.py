"""Command block widget for input/output display."""

from textual.app import ComposeResult
from textual.containers import VerticalGroup, Container
from textual.widgets import Label, Input
from textual.css.query import NoMatches
from textual.message import Message

from ...core.models.context import Context


class CommandBlock(VerticalGroup):
    """A command input/output block widget."""
    
    class CommandSubmitted(Message):
        """Custom message when command is submitted."""
        def __init__(self, command: str, sender_widget=None):
            super().__init__()
            self.command = command
            self.sender_widget = sender_widget

    def __init__(self, context: Context, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = context

    def compose(self) -> ComposeResult:
        """Create child widgets of the command block."""
        # Display current context
        context_path = self._get_context_path()
        yield Label(f"[bold cyan]{context_path}[/bold cyan]", id="context-label")
        yield Input(placeholder="Enter a command (type 'help' for available commands)...")
        yield Container(id="output")

    def _get_context_path(self) -> str:
        """Get the current context path for display."""
        if self.context.level == 0:
            return "/VLMX"
        elif self.context.level == 1:
            return f"/VLMX/{self.context.org_name}"
        else:  # level 2
            return f"/VLMX/{self.context.org_name}/{self.context.app_id}"

    async def on_input_submitted(self, event: Input.Submitted):
        """Handle the input being submitted."""
        user_input = event.value.strip()

        if not user_input:
            return

        # Disable the current input to prevent further editing
        try:
            current_input = self.query_one(Input)
            current_input.disabled = True
        except NoMatches:
            pass

        # Post CommandSubmitted message with command text
        # Let MainScreen handle the rest
        self.post_message(self.CommandSubmitted(user_input, sender_widget=self))

    def show_output(self, message: str, is_error: bool = False):
        """Helper method to display output message."""
        try:
            output = self.query_one("#output")
            style = "[bold red]" if is_error else "[green]"
            output.mount(Label(f"{style}{message}[/]"))
        except NoMatches:
            # Container not yet mounted, ignore
            pass