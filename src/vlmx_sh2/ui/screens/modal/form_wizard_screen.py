"""Form wizard modal screen."""

from textual.app import ComposeResult
from textual.screen import ModalScreen


class FormWizardScreen(ModalScreen):
    """Modal screen for displaying form wizards."""
    
    def __init__(self, form_wizard, main_screen, wizard_request):
        super().__init__()
        self.form_wizard = form_wizard
        self.main_screen = main_screen
        self.wizard_request = wizard_request

    def compose(self) -> ComposeResult:
        """Compose the modal screen with the form wizard."""
        yield self.form_wizard

    async def on_form_wizard_submit(self, message) -> None:
        """Handle form submission."""
        # Process the submitted form data
        await self.main_screen._process_wizard_submission(self.wizard_request, message.data)
        self.dismiss()
        # _process_wizard_submission already creates a new command block via _show_delayed_output

    def _handle_cancellation(self) -> None:
        """Common cancellation logic for both explicit cancel and escape key."""
        # Show cancellation message and create new prompt
        self.dismiss()
        self.app.call_after_refresh(self._show_cancellation_and_new_prompt)

    def _show_cancellation_and_new_prompt(self) -> None:
        """Show cancellation message and create new command block."""
        from ...widgets.command_block import CommandBlock
        new_block = CommandBlock(context=self.main_screen.context)
        self.main_screen.mount(new_block)
        new_block.show_output("Form wizard cancelled", is_error=True)
        self.main_screen.call_after_refresh(self.main_screen._focus_command_block, new_block)

    async def on_form_wizard_cancel(self, message) -> None:
        """Handle form cancellation."""
        self._handle_cancellation()
    
    def key_escape(self) -> None:
        """Handle escape key to cancel form."""
        self._handle_cancellation()