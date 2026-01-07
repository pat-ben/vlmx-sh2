
"""
Textual UI application.

Provides the main terminal UI interface using Textual framework. Handles
command input, parsing, execution, and result display in a conversational
command-line style interface.
"""

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label, Input
from textual.containers import VerticalGroup, Container
from textual.css.query import NoMatches
from textual.screen import ModalScreen

from ..parser import VLMXParser
from ..models.context import Context
from ..models.results import CommandResult, ErrorResult, FormWizardRequest, RecordPickerWizardRequest, QueryWizardRequest
from ..models.schema.enums import Cardinality
from .results import format_command_result
from .widgets.form_wizard import FormWizard


class VLMX(App):
    """VLMX-SH: A command-line style app for managing companies and financial data."""

    CSS_PATH = "styles/design.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize parser and context - no command registration needed in new system
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
        self._current_record_id = None  # Store record ID for updates

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
            # Parse the command
            parse_result = self.parser.parse(user_input)
            self.show_output(f"Command: {user_input}")
            
            # Handle parse errors
            if parse_result.errors:
                error_result = ErrorResult(
                    errors=parse_result.errors,
                    suggestions=parse_result.suggestions or []
                )
                await self._handle_error_result(error_result, event)
                return
            
            # Validate handler exists
            if not parse_result.action_handler:
                error_result = ErrorResult(
                    errors=["No action handler found"],
                    suggestions=parse_result.suggestions or []
                )
                await self._handle_error_result(error_result, event)
                return
            
            # Execute command (no inner try/except)
            result = await self.parser.execute_parsed_command(parse_result, self.context)
            
            # Route result to appropriate handler
            if result.type == 'form_wizard':
                await self._handle_form_wizard(result, event)
            elif result.type == 'record_picker':
                await self._handle_record_picker(result, event)
            elif result.type == 'query_wizard':
                await self._handle_query_wizard(result, event)
            elif result.type == 'command_result':
                await self._handle_command_result(result, event)
            elif result.type == 'error':
                await self._handle_error_result(result, event)
            else:
                self.show_output(f"Unknown result type: {result.type}", is_error=True)
                self._create_new_prompt()
                
        except Exception as e:
            # Catch ALL exceptions (parsing, execution, unexpected)
            error_result = ErrorResult(
                errors=[f"Error: {str(e)}"],
                suggestions=["Please try again or check command syntax"]
            )
            await self._handle_error_result(error_result, event)

    def _create_new_prompt(self):
        """Create a new command prompt after disabling the current input."""
        # Disable the current input
        try:
            current_input = self.query_one(Input)
            current_input.disabled = True
        except NoMatches:
            pass

        # Create a new command block for the next command (with potentially updated context)
        new_block = CommandBlock(parser=self.parser, context=self.context)
        self.app.mount(new_block)

        # Use call_after_refresh to ensure the block is fully composed before querying
        self.app.call_after_refresh(self._focus_new_input, new_block)

    async def _handle_command_result(self, result: CommandResult, event):
        """Handle and display a CommandResult."""
        # Format and display the command result using existing formatting logic
        formatted_result = format_command_result(result)
        
        # Split the formatted result into lines and display each
        for line in formatted_result.split('\n'):
            if line.strip():  # Skip empty lines
                is_error = not result.success
                self.show_output(line, is_error=is_error)
        
        # Check if the result requests a context switch
        if result.success and result.data and result.data.get("context_switch"):
            # Update context based on context_switch data
            context_switch = result.data["context_switch"]
            from ..models.context import Context, ContextLevel
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
        self._create_new_prompt()

    async def _handle_error_result(self, result: ErrorResult, event):
        """Handle and display an ErrorResult."""
        # Display errors
        for error in result.errors:
            self.show_output(f"Error: {error}", is_error=True)
        
        # Display suggestions
        for suggestion in result.suggestions:
            self.show_output(f"  → {suggestion}", is_error=True)
        
        # Create new prompt
        self._create_new_prompt()

    async def _handle_form_wizard(self, wizard_request: FormWizardRequest, event):
        """Handle form wizard request by showing an interactive form."""
        try:
            # Create the form wizard widget
            form_wizard = FormWizard(wizard_request)
            
            # Create the modal screen and push it, waiting for result
            screen = FormWizardScreen(form_wizard, self, wizard_request)
            await self.app.push_screen(screen)
            
        except Exception as e:
            self.show_output(f"Error showing form wizard: {str(e)}", is_error=True)
            self._create_new_prompt()

    async def _handle_record_picker(self, picker_request: RecordPickerWizardRequest, event):
        """Handle record picker request by showing an interactive record selector."""
        try:
            # Create the dynamic entity screen with split layout
            from .screens.dynamic_entity_screen import DynamicEntityScreen
            
            # Create the modal screen and push it
            screen = DynamicEntityScreen(picker_request, self)
            await self.app.push_screen(screen)
            
        except Exception as e:
            self.show_output(f"Error showing record picker: {str(e)}", is_error=True)
            self._create_new_prompt()

    async def _handle_query_wizard(self, wizard_request: QueryWizardRequest, event):
        """Handle query wizard request (future implementation)."""
        # Stub for future implementation
        self.show_output(f"Query wizard requested for {wizard_request.entity_id}")
        self.show_output("Query wizard not yet implemented", is_error=True)
        
        # Create new prompt since wizard is not implemented
        self._create_new_prompt()

    async def _process_wizard_submission(self, wizard_request: FormWizardRequest, fields: dict):
        """Process form wizard submission by updating entity fields."""
        try:
            from ..handlers.crud import add_handler, update_handler
            from ..dsl.words import get_word
            from ..models.words import EntityWord
            
            # Get the entity model from the wizard request
            entity_word = get_word(wizard_request.entity_id)
            if not entity_word:
                self.show_output(f"Unknown entity type: {wizard_request.entity_id}", is_error=True)
                return
            
            # Ensure we have an EntityWord with entity_model
            if not isinstance(entity_word, EntityWord):
                self.show_output(f"Invalid entity type: {wizard_request.entity_id}", is_error=True)
                return
            
            # Determine if this is an update (editing existing record) or create (new record)
            is_editing_existing = hasattr(self, '_current_record_id') and self._current_record_id is not None
            
            if is_editing_existing:
                # Editing existing record - check if dynamic or static entity
                self.show_output(f"Updating existing {wizard_request.entity_id} record (ID: {self._current_record_id})")
                
                # Determine if this is a dynamic entity (multiple records) or static entity (single record)
                is_dynamic_entity = hasattr(entity_word.entity_model, 'cardinality') and entity_word.entity_model.cardinality == Cardinality.MULTIPLE
                
                if is_dynamic_entity:
                    # Dynamic entity - update specific record in array
                    from ..storage.database import update_dynamic_entity_record
                    from ..handlers.utils import get_company_name_from_context
                    
                    company_name = get_company_name_from_context(self.context)
                    if not company_name:
                        self.show_output("Error: No company context for dynamic entity update", is_error=True)
                        return
                    
                    # Use specialized dynamic entity update function
                    result_dict = update_dynamic_entity_record(
                        entity_type=wizard_request.entity_id,
                        record_id=self._current_record_id,
                        updated_fields=fields,
                        company_name=company_name,
                        context=self.context
                    )
                    
                    # Convert dict result to result object for consistent handling
                    class DictResult:
                        def __init__(self, data):
                            self.success = data.get('success', False)
                            self.message = data.get('message', '')
                            self.errors = [data.get('error', '')] if not self.success else []
                    
                    result = DictResult(result_dict)
                    
                else:
                    # Static entity - use standard update_handler
                    # Add the record ID to the fields for identification
                    update_fields = fields.copy()
                    update_fields['id'] = self._current_record_id
                    
                    result = await update_handler(
                        entity_model=entity_word.entity_model,
                        entity_value=wizard_request.entity_name,
                        fields=update_fields,
                        context=self.context,
                        field_words=list(fields.keys()),
                        parsed_command=None
                    )
                
                # Clear the current record ID after use
                self._current_record_id = None
                
            else:
                # Creating new record - use add_handler
                self.show_output(f"Creating new {wizard_request.entity_id} record")
                
                result = await add_handler(
                    entity_model=entity_word.entity_model,
                    entity_value=wizard_request.entity_name,
                    fields=fields,
                    context=self.context,
                    field_words=list(fields.keys()),
                    parsed_command=None
                )
            
            # Display the result
            if hasattr(result, 'success') and result.success:
                action = "Updated" if is_editing_existing else "Created"
                self.show_output(f"✅ {action} {wizard_request.entity_id} successfully")
                field_list = ", ".join([f"{k}={v}" for k, v in fields.items()])
                self.show_output(f"Fields: {field_list}")
            else:
                error_msg = result.errors[0] if hasattr(result, 'errors') and result.errors else "Unknown error"
                self.show_output(f"❌ {error_msg}", is_error=True)
                
        except Exception as e:
            self.show_output(f"Error processing form: {str(e)}", is_error=True)


class FormWizardScreen(ModalScreen):
    """Modal screen for displaying form wizards."""
    
    def __init__(self, form_wizard, command_block, wizard_request):
        super().__init__()
        self.form_wizard = form_wizard
        self.command_block = command_block
        self.wizard_request = wizard_request

    def compose(self) -> ComposeResult:
        """Compose the modal screen with the form wizard."""
        yield self.form_wizard

    async def on_form_wizard_submit(self, message) -> None:
        """Handle form submission."""
        # Process the submitted form data
        await self.command_block._process_wizard_submission(self.wizard_request, message.data)
        self.dismiss()
        # Create new prompt after modal is dismissed
        self.app.call_after_refresh(self.command_block._create_new_prompt)

    async def on_form_wizard_cancel(self, message) -> None:
        """Handle form cancellation."""
        self.command_block.show_output("Form wizard cancelled", is_error=True)
        self.dismiss()
        # Create new prompt after modal is dismissed
        self.app.call_after_refresh(self.command_block._create_new_prompt)
    
    def key_escape(self) -> None:
        """Handle escape key to cancel form."""
        self.command_block.show_output("Form wizard cancelled", is_error=True)
        self.dismiss()
        # Create new prompt after modal is dismissed
        self.app.call_after_refresh(self.command_block._create_new_prompt)




