

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label, Input
from textual.containers import VerticalGroup, Container
from textual.css.query import NoMatches

from .parser import VLMXParser
from .context import Context
from .results import CommandResult, format_command_result





class VLMX(App):
    """VLMX-SH: A command-line style app for managing companies and financial data."""

    CSS_PATH = "design.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = VLMXParser()
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

    def __init__(self, parser: VLMXParser, context: Context, *args, **kwargs):
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

    async def on_input_submitted(self, event: Input.Submitted):
        """Handle the input being submitted."""
        user_input = event.value.strip()

        if not user_input:
            return

        try:
            # Parse the command using the parser
            parse_result = self.parser.parse(user_input)
            
            # Show parsing information
            self.show_output(f"Command: {user_input}")
            
            if parse_result.errors:
                # Show parsing errors
                for error in parse_result.errors:
                    self.show_output(f"Parse Error: {error}", is_error=True)
                
                # Show suggestions
                if parse_result.suggestions:
                    for suggestion in parse_result.suggestions:
                        self.show_output(f"  → {suggestion}", is_error=True)
                return
            
            if not parse_result.best_command:
                self.show_output("No matching command found", is_error=True)
                if parse_result.suggestions:
                    for suggestion in parse_result.suggestions:
                        self.show_output(f"  → {suggestion}", is_error=True)
                return
            
            # Execute the command using the new handler signature
            command_id = parse_result.best_command.command_id
            
            # Get the handler function
            handler = parse_result.best_command.handler
            if not handler:
                self.show_output(f"No handler found for command: {command_id}", is_error=True)
                return
            
            # Execute the handler with ParseResult
            result = await handler(parse_result, self.context)
            
            # Display the result using the results.py formatting
            if isinstance(result, CommandResult):
                formatted_result = format_command_result(result, parse_result)
                
                # Split the formatted result into lines and display each
                for line in formatted_result.split('\n'):
                    if line.strip():  # Skip empty lines
                        is_error = not result.success
                        self.show_output(line, is_error=is_error)
            else:
                # Fallback for handlers that still return dicts
                if result.get("success", False):
                    message = result.get("message", "Command executed successfully")
                    self.show_output(message)
                else:
                    error = result.get("error", "Command failed")
                    self.show_output(f"Error: {error}", is_error=True)
                
        except Exception as e:
            self.show_output(f"Execution Error: {str(e)}", is_error=True)
        
        finally:
            # Disable the current input
            event.input.disabled = True

            # Create a new command block for the next command
            new_block = CommandBlock(parser=self.parser, context=self.context)
            self.app.mount(new_block)

            # Use call_after_refresh to ensure the block is fully composed before querying
            self.app.call_after_refresh(self._focus_new_input, new_block)




def main():
    """Main entry point for the application."""
    app = VLMX()
    app.run()


if __name__ == "__main__":
    main()