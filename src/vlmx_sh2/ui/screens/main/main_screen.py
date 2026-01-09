"""Main terminal screen for command execution."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header

from ....parser import VLMXParser
from ....models.context import Context
from ....models.results import CommandResult, ErrorResult, FormWizardRequest, RecordPickerWizardRequest, QueryWizardRequest
from ...results import format_command_result
from ...widgets.command_block import CommandBlock


class MainScreen(Screen):
    """Main terminal screen for command execution."""
    
    def __init__(self, parser: VLMXParser, context: Context):
        super().__init__()
        self.parser = parser
        self.context = context
        self._current_record_id = None  # Store record ID for updates

    def compose(self) -> ComposeResult:
        """Create child widgets for the screen."""
        yield Header()
        yield CommandBlock(context=self.context)
        yield Footer()

    async def on_command_block_command_submitted(self, message):
        """Handle command submission from CommandBlock."""
        command = message.command
        command_block = message.sender_widget
        # if not command_block:
        #     # Fallback: create a new command block for output
        #     from ...widgets.command_block import CommandBlock
        #     command_block = CommandBlock(context=self.context)
        #     self.mount(command_block)
        
        try:
            # Parse the command
            parse_result = self.parser.parse(command)
            command_block.show_output(f"Command: {command}")
            
            # Handle parse errors
            if parse_result.errors:
                error_result = ErrorResult(
                    errors=parse_result.errors,
                    suggestions=parse_result.suggestions or []
                )
                await self._handle_error_result(error_result, command_block)
                return
            
            # Validate handler exists
            if not parse_result.action_handler:
                error_result = ErrorResult(
                    errors=["No action handler found"],
                    suggestions=parse_result.suggestions or []
                )
                await self._handle_error_result(error_result, command_block)
                return
            
            # Execute command
            result = await self.parser.execute_parsed_command(parse_result, self.context)
            
            # Route result to appropriate handler
            if result.type == 'form_wizard':
                await self._handle_form_wizard(result, command_block)
            elif result.type == 'record_picker':
                await self._handle_record_picker(result, command_block)
            elif result.type == 'query_wizard':
                await self._handle_query_wizard(result, command_block)
            elif result.type == 'command_result':
                await self._handle_command_result(result, command_block)
            elif result.type == 'error':
                await self._handle_error_result(result, command_block)
            else:
                command_block.show_output(f"Unknown result type: {result.type}", is_error=True)
                self._create_new_command_block()
                
        except Exception as e:
            # Catch ALL exceptions (parsing, execution, unexpected)
            error_result = ErrorResult(
                errors=[f"Error: {str(e)}"],
                suggestions=["Please try again or check command syntax"]
            )
            await self._handle_error_result(error_result, command_block)

    def _create_new_command_block(self):
        """Create and mount a new command block."""
        new_block = CommandBlock(context=self.context)
        self.mount(new_block)
        self.call_after_refresh(self._focus_command_block, new_block)

    def _focus_command_block(self, block: CommandBlock):
        """Focus the input in the newly created block after it's rendered."""
        try:
            from textual.widgets import Input
            new_input = block.query_one(Input)
            new_input.focus()
        except Exception:
            pass

    async def _handle_command_result(self, result: CommandResult, command_block: CommandBlock):
        """Handle and display a CommandResult."""
        # Format and display the command result using existing formatting logic
        formatted_result = format_command_result(result)
        
        # Split the formatted result into lines and display each
        for line in formatted_result.split('\n'):
            if line.strip():  # Skip empty lines
                is_error = not result.success
                command_block.show_output(line, is_error=is_error)
        
        # Check if the result requests a context switch
        if result.success and result.data and result.data.get("context_switch"):
            # Update context based on context_switch data
            context_switch = result.data["context_switch"]
            from ....models.context import Context, ContextLevel
            if context_switch["level"] == "SYS":
                self.context = Context(level=ContextLevel.SYS)
            elif context_switch["level"] == "ORG":
                self.context = Context(
                    level=ContextLevel.ORG,
                    org_id=context_switch["org_id"],
                    org_name=context_switch["org_name"],
                    org_db_path=context_switch["org_db_path"]
                )
        
        # Create new prompt
        self._create_new_command_block()

    async def _handle_error_result(self, result: ErrorResult, command_block: CommandBlock):
        """Handle and display an ErrorResult."""
        # Display errors
        for error in result.errors:
            command_block.show_output(f"Error: {error}", is_error=True)
        
        # Display suggestions
        for suggestion in result.suggestions:
            command_block.show_output(f"  → {suggestion}", is_error=True)
        
        # Create new prompt
        self._create_new_command_block()

    async def _handle_form_wizard(self, wizard_request: FormWizardRequest, command_block: CommandBlock):
        """Handle form wizard request by showing an interactive form."""
        try:
            # Import here to avoid circular imports
            from ..modal.form_wizard_screen import FormWizardScreen
            from ...widgets.form_wizard import FormWizard
            
            # Create the form wizard widget
            form_wizard = FormWizard(wizard_request)
            
            # Create the modal screen and push it, waiting for result
            screen = FormWizardScreen(form_wizard, self, wizard_request)
            await self.app.push_screen(screen)
            
        except Exception as e:
            command_block.show_output(f"Error showing form wizard: {str(e)}", is_error=True)
            self._create_new_command_block()

    async def _handle_record_picker(self, picker_request: RecordPickerWizardRequest, command_block: CommandBlock):
        """Handle record picker request by showing an interactive record selector."""
        try:
            # Create the dynamic entity screen with split layout
            from ..modal.dynamic_entity_screen import DynamicEntityScreen
            
            # Create the modal screen and push it
            screen = DynamicEntityScreen(picker_request, self)
            await self.app.push_screen(screen)
            
        except Exception as e:
            command_block.show_output(f"Error showing record picker: {str(e)}", is_error=True)
            self._create_new_command_block()

    async def _handle_query_wizard(self, wizard_request: QueryWizardRequest, command_block: CommandBlock):
        """Handle query wizard request (future implementation)."""
        # Stub for future implementation
        command_block.show_output(f"Query wizard requested for {wizard_request.entity_id}")
        command_block.show_output("Query wizard not yet implemented", is_error=True)
        
        # Create new prompt since wizard is not implemented
        self._create_new_command_block()

    async def _process_wizard_submission(self, wizard_request: FormWizardRequest, fields: dict):
        """Process form wizard submission by updating entity fields."""
        try:
            from ....handlers.crud import add_handler, update_handler
            from ....dsl.words import get_word, WordType
            
            # Get the entity model for the entity type
            entity_word = get_word(wizard_request.entity_id)
            if not entity_word or entity_word.word_type != WordType.ENTITY:
                error_msg = f"Unknown entity type: {wizard_request.entity_id}"
                self.call_after_refresh(self._show_delayed_output, error_msg, True)
                return
            
            # Determine if this is an update or add based on pre-filled values
            is_update = bool(wizard_request.pre_filled_values)
            
            if is_update:
                # Use update handler with correct signature
                result = await update_handler(
                    entity_model=entity_word.entity_model,
                    entity_value=wizard_request.entity_name,
                    fields=fields,
                    context=self.context,
                    field_words=None,
                    parsed_command=None
                )
            else:
                # Use add handler with correct signature
                result = await add_handler(
                    entity_model=entity_word.entity_model,
                    entity_value=wizard_request.entity_name,
                    fields=fields,
                    context=self.context,
                    field_words=None,
                    parsed_command=None
                )
            
            # Display result using format_command_result - create ONE command block with all output
            self._create_new_command_block_with_result(result)
            
        except Exception as e:
            error_msg = f"Error processing form submission: {str(e)}"
            self.call_after_refresh(self._show_delayed_output, error_msg, True)

    def _create_new_command_block_with_result(self, result):
        """Create a single new command block and display all result output in it."""
        new_block = CommandBlock(context=self.context)
        self.mount(new_block)
        
        if result.type == 'command_result':
            formatted_result = format_command_result(result)
            
            # Split the formatted result into lines and display each in the same block
            for line in formatted_result.split('\n'):
                if line.strip():  # Skip empty lines
                    is_error = not result.success
                    new_block.show_output(line, is_error=is_error)
        elif result.type == 'error':
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