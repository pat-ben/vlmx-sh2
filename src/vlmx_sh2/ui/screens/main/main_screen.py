"""Main terminal screen for command execution."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, OptionList

from vlmx_sh2.ui.formatters.results import format_command_result

from ....core.enums.core import ContextLevel
from ....core.models.context import Context
from ....core.models.responses import (
    CommandResult,
    ErrorResult,
    FormRequest,
    PickerRequest,
    QueryRequest,
)
from ....engine.executor import CommandExecutor
from ...widgets.command_block import CommandBlock


class MainScreen(Screen):
    """Main terminal screen for command execution."""

    def __init__(self, context: Context):
        super().__init__()
        self.context = context
        self._current_record_id = None  # Store record ID for updates

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()

        with Horizontal():
            with Vertical(id="left-pane"):
                yield OptionList(id="organisations-option-list")
                yield Label("apps widget")
            with Vertical(id="command-block-container"):
                yield CommandBlock(context=self.context)

        yield Footer()

        self.run_worker(self._populate_organisations_option_list, thread=True)

    def _populate_organisations_option_list(self):
        from ...data_provider import UIDataProvider

        orgs = UIDataProvider.get_org(self.context)
        orgs_option_list = self.query_one("#organisations-option-list", OptionList)
        orgs_option_list.add_options([org.name for org in orgs])

    async def on_command_block_command_submitted(self, message):
        """Handle command submission from CommandBlock."""
        command = message.command
        command_block = message.sender_widget

        # Display the command
        command_block.show_output(f"Command: {command}")

        # ONE LINE to execute - delegate everything to CommandExecutor
        result = await CommandExecutor.execute(command, self.context)

        # Render based on result type
        await self._render_result(result, command_block)

    async def _render_result(self, result, command_block):
        """Route result to appropriate rendering handler based on type."""
        match result.type:
            case "command_result":
                await self._handle_command_result(result, command_block)
            case "error":
                await self._handle_error_result(result, command_block)
            case "form_wizard":
                await self._handle_form_wizard(result, command_block)
            case "record_picker":
                await self._handle_record_picker(result, command_block)
            case "query_wizard":
                await self._handle_query_wizard(result, command_block)
            case _:
                command_block.show_output(
                    f"Unknown result type: {result.type}", is_error=True
                )
                self._create_new_command_block()

    def _create_new_command_block(self):
        """Create and mount a new command block."""
        new_block = CommandBlock(context=self.context)
        command_block_container = self.query_one("#command-block-container")
        command_block_container.mount(new_block)
        self.call_after_refresh(self._focus_command_block, new_block)

    def _focus_command_block(self, block: CommandBlock):
        """Focus the input in the newly created block after it's rendered."""
        try:
            from textual.widgets import Input

            new_input = block.query_one(Input)
            new_input.focus()
        except Exception:
            pass

    async def _handle_command_result(
        self, result: CommandResult, command_block: CommandBlock
    ):
        """Handle and display a CommandResult."""
        # Format and display the command result using existing formatting logic
        formatted_result = format_command_result(result)

        # Split the formatted result into lines and display each
        for line in formatted_result.split("\n"):
            if line.strip():  # Skip empty lines
                is_error = not result.success
                command_block.show_output(line, is_error=is_error)

        # Check if the result requests a context switch
        if result.success and result.data and result.data.get("context_switch"):
            # Update context based on context_switch data
            context_switch = result.data["context_switch"]
            if context_switch["level"] == ContextLevel.SYS:
                self.context = Context(level=ContextLevel.SYS)
            elif context_switch["level"] == ContextLevel.ORG:
                self.context = Context(
                    level=ContextLevel.ORG,
                    org_id=context_switch["org_id"],
                    org_name=context_switch["org_name"],
                    org_db_path=context_switch["org_db_path"],
                )
            elif context_switch["level"] == ContextLevel.APP:
                self.context = Context(
                    level=ContextLevel.APP,
                    org_id=context_switch["org_id"],
                    org_name=context_switch["org_name"],
                    org_db_path=context_switch["org_db_path"],
                    app_id=context_switch["app_id"],
                    app_name=context_switch["app_name"],
                    app_type=context_switch["app_type"],
                )

        # Create new prompt
        self._create_new_command_block()

    async def _handle_error_result(
        self, result: ErrorResult, command_block: CommandBlock
    ):
        """Handle and display an ErrorResult."""
        # Display errors
        for error in result.errors:
            command_block.show_output(f"Error: {error}", is_error=True)

        # Display suggestions
        for suggestion in result.suggestions:
            command_block.show_output(f"  → {suggestion}", is_error=True)

        # Create new prompt
        self._create_new_command_block()

    async def _handle_form_wizard(
        self, wizard_request: FormRequest, command_block: CommandBlock
    ):
        """Handle form wizard request by showing an interactive form."""
        try:
            # Import here to avoid circular imports
            from ...widgets.form_wizard import FormWizard
            from ..modal.form_wizard_screen import FormWizardScreen

            # Create the form wizard widget
            form_wizard = FormWizard(wizard_request)

            # Create the modal screen and push it, waiting for result
            screen = FormWizardScreen(form_wizard, self, wizard_request)
            await self.app.push_screen(screen)

        except Exception as e:
            command_block.show_output(
                f"Error showing form wizard: {str(e)}", is_error=True
            )
            self._create_new_command_block()

    async def _handle_record_picker(
        self, picker_request: PickerRequest, command_block: CommandBlock
    ):
        """Handle record picker request by showing an interactive record selector."""
        try:
            # Create the dynamic entity screen with split layout
            from ..modal.dynamic_entity_screen import DynamicEntityScreen

            # Create the modal screen and push it
            screen = DynamicEntityScreen(picker_request, self)
            await self.app.push_screen(screen)

        except Exception as e:
            command_block.show_output(
                f"Error showing record picker: {str(e)}", is_error=True
            )
            self._create_new_command_block()

    async def _handle_query_wizard(
        self, wizard_request: QueryRequest, command_block: CommandBlock
    ):
        """Handle query wizard request (future implementation)."""
        # Stub for future implementation
        command_block.show_output(
            f"Query wizard requested for {wizard_request.entity_id}"
        )
        command_block.show_output("Query wizard not yet implemented", is_error=True)

        # Create new prompt since wizard is not implemented
        self._create_new_command_block()

    async def _process_wizard_submission(
        self, wizard_request: FormRequest, fields: dict
    ):
        """Process form wizard submission using unified command flow."""
        try:
            # Use unified command executor instead of manually building command
            result = await CommandExecutor.execute_from_wizard(
                action_id="add",
                entity_id=wizard_request.entity_id,
                entity_name=wizard_request.entity_name,
                field_values=fields,
                record_id=None,  # FormWizardScreen is always for creating new records
                context=self.context,
            )

            # Display result using existing result handling - create ONE command block with all output
            self._create_new_command_block_with_result(result)

        except Exception as e:
            error_msg = f"Error processing form submission: {str(e)}"
            self.call_after_refresh(self._show_delayed_output, error_msg, True)

    def _create_new_command_block_with_result(self, result):
        """Create a single new command block and display all result output in it."""
        new_block = CommandBlock(context=self.context)
        self.mount(new_block)

        if result.type == "command_result":
            formatted_result = format_command_result(result)

            # Split the formatted result into lines and display each in the same block
            for line in formatted_result.split("\n"):
                if line.strip():  # Skip empty lines
                    is_error = not result.success
                    new_block.show_output(line, is_error=is_error)
        elif result.type == "error":
            # Display error
            for error in result.errors:
                new_block.show_output(f"Error: {error}", is_error=True)
            for suggestion in result.suggestions:
                new_block.show_output(f"  → {suggestion}", is_error=True)

        self.call_after_refresh(self._focus_command_block, new_block)

    def _show_delayed_output(self, message: str, is_error: bool = False):
        """Show output message and create new command block."""
        # Create new command block and show the output
        new_block = CommandBlock(context=self.context)
        self.mount(new_block)
        new_block.show_output(message, is_error=is_error)
        self.call_after_refresh(self._focus_command_block, new_block)
