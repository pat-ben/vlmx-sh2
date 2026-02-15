"""
Dynamic entity screen with split layout.

Provides a split-screen interface for managing multi-record dynamic schemas.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen

from ....core.models.responses import PickerRequest
from ...widgets.dynamic_entity_manager import DynamicEntityManager


class DynamicEntityScreen(ModalScreen):
    """
    Modal screen for dynamic entity management.
    """

    def __init__(self, picker_request: PickerRequest, main_screen, **kwargs):
        """
        Initialize the dynamic entity screen.

        Args:
            picker_request: The picker request data
            main_screen: Reference to the main screen for result handling
            **kwargs: Additional screen arguments
        """
        super().__init__(**kwargs)
        self.picker_request = picker_request
        self.main_screen = main_screen

    def compose(self) -> ComposeResult:
        """Compose the screen content."""
        yield DynamicEntityManager(self.picker_request, id="entity-manager")

    async def on_dynamic_entity_manager_form_submitted(
        self, message: DynamicEntityManager.FormSubmitted
    ) -> None:
        """Handle form submission from the dynamic entity manager."""
        try:
            # Process the form submission
            await self._process_form_submission(message)

        except Exception as e:
            # Show error within the modal (don't close it)
            self._show_error_message_in_modal(f"❌ Error processing form: {str(e)}")

    async def on_dynamic_entity_manager_cancel(
        self, message: DynamicEntityManager.Cancel
    ) -> None:
        """Handle cancellation from the dynamic entity manager."""
        self.dismiss()
        self.app.call_after_refresh(self.main_screen._create_new_command_block)

    async def _process_form_submission(
        self, message: DynamicEntityManager.FormSubmitted
    ) -> None:
        """Process the form submission using unified command flow."""
        try:
            # Use unified command executor instead of directly calling storage functions
            from ....engine.executor import CommandExecutor

            # Get current context
            context = self.main_screen.context
            entity_type = self.picker_request.entity_id
            form_data = message.form_data

            # Determine action based on whether this is create or update
            action_id = "add"  # Both create and update use "add" action
            record_id = message.record_id  # None for create, string for update

            # Execute through unified pipeline
            result = await CommandExecutor.execute_from_wizard(
                action_id=action_id,
                entity_id=entity_type,
                entity_name=None,  # Dynamic entities don't have entity names
                field_values=form_data,
                record_id=record_id,
                context=context,
            )

            # Handle the result
            if result.type == "command_result" and result.success:
                # Refresh the screen to show updated data
                await self._refresh_screen()

                # Show appropriate success message
                operation = "Updated" if record_id else "Created new"
                self._show_success_message_in_modal(
                    f"✅ {operation} {entity_type} record"
                )

            elif result.type == "error":
                # Show error message within the modal (don't close it)
                error_messages = "; ".join(result.errors)
                self._show_error_message_in_modal(f"❌ {error_messages}")

            else:
                # Unexpected result type
                self._show_error_message_in_modal(
                    f"❌ Unexpected result: {result.type}"
                )

        except Exception as e:
            # Show error message within the modal (don't close it)
            self._show_error_message_in_modal(f"❌ Error processing form: {str(e)}")

    async def _refresh_screen(self) -> None:
        """Refresh the screen with updated data."""
        try:
            # Reload records from database
            from ....storage.database import StorageInterface

            context = self.main_screen.context
            company_name = (
                context.org_name
                if getattr(context, "level", None) is not None and context.org_name
                else None
            )
            entity_type = self.picker_request.entity_id

            # Handle potential None company_name
            if not company_name:
                return

            # Load fresh data
            records_result = StorageInterface.load_all_entities(
                entity_type, company_name, context
            )
            if not records_result.success:
                return  # Silently fail like the existing try/except
            updated_records = records_result.data

            # Update picker request with fresh data
            self.picker_request.records = updated_records

            # Get the entity manager and refresh its data
            entity_manager = self.query_one("#entity-manager", DynamicEntityManager)
            entity_manager.all_records = updated_records.copy()
            entity_manager.filtered_records = updated_records.copy()
            entity_manager._populate_table()

            # Update record count
            from textual.widgets import Static

            count_widget = entity_manager.query_one("#record-count", Static)
            record_text = "record" if len(updated_records) == 1 else "records"
            count_widget.update(f"📈 Total: {len(updated_records)} {record_text}")

        except Exception:
            # Silently handle refresh errors - the screen will still work
            pass

    def _show_success_message_in_modal(self, message: str) -> None:
        """Show success message within the modal without closing it."""
        try:
            # Use Textual's notification system for success messages
            self.notify(message, severity="information")
        except Exception:
            pass

    def _show_error_message_in_modal(self, message: str) -> None:
        """Show error message within the modal without closing it."""
        try:
            # Use Textual's notification system for error messages
            self.notify(message, severity="error")
        except Exception:
            pass

    def _show_success_and_new_prompt(self, message: str) -> None:
        """Show success message and create new command block."""
        from ...widgets.command_block import CommandBlock

        new_block = CommandBlock(context=self.main_screen.context)
        self.main_screen.mount(new_block)
        new_block.show_output(f"✅ {message}", is_error=False)
        self.main_screen.call_after_refresh(
            self.main_screen._focus_command_block, new_block
        )

    def _show_error_and_new_prompt(self, message: str) -> None:
        """Show error message and create new command block."""
        from ...widgets.command_block import CommandBlock

        new_block = CommandBlock(context=self.main_screen.context)
        self.main_screen.mount(new_block)
        new_block.show_output(f"❌ {message}", is_error=True)
        self.main_screen.call_after_refresh(
            self.main_screen._focus_command_block, new_block
        )
