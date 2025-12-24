

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label, Input
from textual.containers import VerticalGroup, Container
from textual.css.query import NoMatches

from ..parser.core import Parser
from ..parser.context import Context
from ..parser.base import Result


class VLMX(App):
    """VLMX-SH: A command-line style app for managing companies and financial data."""

    CSS_PATH = "design.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = Parser()
        self.context = Context(level=0)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield CommandBlock(parser=self.parser, context=self.context)
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

class CommandBlock(VerticalGroup):
    """A command and context block"""

    def __init__(self, parser: Parser, context: Context, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = parser
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
            return f"/VLMX/{self.context.company_name}"
        else:  # level 2
            return f"/VLMX/{self.context.company_name}/{self.context.plugin_id}"

    def show_output(self, message: str, is_error: bool = False):
        """Helper method to display output message"""
        try:
            output = self.query_one("#output")
            style = "[bold red]" if is_error else "[green]"
            output.mount(Label(f"{style}{message}[/]"))
        except NoMatches:
            # Container not yet mounted, ignore
            pass

    def _focus_new_input(self, block: "CommandBlock"):
        """Focus the input in the newly created block after it's rendered."""
        try:
            new_input = block.query_one(Input)
            new_input.focus()
        except NoMatches:
            pass

    def on_input_submitted(self, event: Input.Submitted):
        """Handle the input being submitted."""
        user_input = event.value.strip()

        if not user_input:
            return

        # Parse the command using the parser
        parsed = self.parser.parse(user_input, self.context)

        # Check if it's a Result (error) or a Command
        if isinstance(parsed, Result):
            # It's an error result
            self.show_output(f"Error: {parsed.message}", is_error=True)
            if parsed.suggestions:
                for suggestion in parsed.suggestions:
                    self.show_output(f"  → {suggestion}", is_error=True)
        else:
            # It's a valid command, execute it
            result = parsed.execute(self.context)

            if result.success:
                self.show_output(result.message)
            else:
                self.show_output(f"Error: {result.message}", is_error=True)
                if result.suggestions:
                    for suggestion in result.suggestions:
                        self.show_output(f"  → {suggestion}", is_error=True)

        # Disable the current input
        event.input.disabled = True

        # Create a new command block for the next command
        new_block = CommandBlock(parser=self.parser, context=self.context)
        self.app.mount(new_block)

        # Use call_after_refresh to ensure the block is fully composed before querying
        self.app.call_after_refresh(self._focus_new_input, new_block)




if __name__ == "__main__":
    app = VLMX()
    app.run()