"""
Dynamic entity screen with split layout.

Provides a split-screen interface for managing multi-record dynamic schemas.
"""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from ...widgets.dynamic_entity_manager import DynamicEntityManager
from ....models.responses import PickerRequest


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
    
    async def on_dynamic_entity_manager_form_submitted(self, message: DynamicEntityManager.FormSubmitted) -> None:
        """Handle form submission from the dynamic entity manager."""
        try:
            # Process the form submission
            await self._process_form_submission(message)
            
        except Exception as e:
            # Show error within the modal (don't close it)
            self._show_error_message_in_modal(f"❌ Error processing form: {str(e)}")
    
    async def on_dynamic_entity_manager_cancel(self, message: DynamicEntityManager.Cancel) -> None:
        """Handle cancellation from the dynamic entity manager."""
        self.dismiss()
        self.app.call_after_refresh(self.main_screen._create_new_command_block)
    
    async def _process_form_submission(self, message: DynamicEntityManager.FormSubmitted) -> None:
        """Process the form submission."""
        from ....storage.database import update_dynamic_entity_record, save_entity_array, load_all_entities
        from ....handlers.utils import get_company_name_from_context
        
        # Get current context and company
        context = self.main_screen.context
        company_name = get_company_name_from_context(context)
        
        # Check that we have a valid company context
        if not company_name:
            self.dismiss()
            self.app.call_after_refresh(self._show_error_and_new_prompt, "Error: Not in organization context")
            return
        
        entity_type = self.picker_request.entity_id
        form_data = message.form_data
        
        if message.record_id is None:
            # Creating new record
            
            # Load current entity data (array)
            current_data = load_all_entities(entity_type, company_name, context)
            
            # Add new record with generated ID
            new_record = form_data.copy()
            new_record['id'] = str(len(current_data) + 1)  # Simple ID generation
            
            # Add timestamps
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            new_record['created_at'] = timestamp
            new_record['updated_at'] = timestamp
            
            # Add to array
            current_data.append(new_record)
            
            # Save updated array
            save_result = save_entity_array(entity_type, current_data, company_name, context)
            
            if save_result.get("success", False):
                # Refresh the screen to show new record
                await self._refresh_screen()
                # Show success message within the modal (don't close it)
                self._show_success_message_in_modal(f"✅ Created new {entity_type} record")
                return
            else:
                error_msg = save_result.get("error", f"Failed to create {entity_type} record")
                # Show error message within the modal (don't close it)
                self._show_error_message_in_modal(f"❌ {error_msg}")
                return
        
        else:
            # Updating existing record
            # Update the record in the array
            update_result = update_dynamic_entity_record(
                entity_type=entity_type,
                record_id=message.record_id,
                updated_fields=form_data,
                company_name=company_name,
                context=context
            )
            
            if update_result.get("success", False):
                # Refresh the screen to show updated record
                await self._refresh_screen()
                # Show success message within the modal (don't close it)
                self._show_success_message_in_modal(f"✅ Updated {entity_type} record")
            else:
                error_msg = update_result.get("error", f"Failed to update {entity_type} record")
                # Show error message within the modal (don't close it)
                self._show_error_message_in_modal(f"❌ {error_msg}")
    
    async def _refresh_screen(self) -> None:
        """Refresh the screen with updated data."""
        try:
            # Reload records from database
            from ....storage.database import load_all_entities
            from ....handlers.utils import get_company_name_from_context
            
            context = self.main_screen.context
            company_name = get_company_name_from_context(context)
            entity_type = self.picker_request.entity_id
            
            # Handle potential None company_name
            if not company_name:
                return
            
            # Load fresh data
            updated_records = load_all_entities(entity_type, company_name, context)
            
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
        self.main_screen.call_after_refresh(self.main_screen._focus_command_block, new_block)

    def _show_error_and_new_prompt(self, message: str) -> None:
        """Show error message and create new command block."""
        from ...widgets.command_block import CommandBlock
        new_block = CommandBlock(context=self.main_screen.context)
        self.main_screen.mount(new_block)
        new_block.show_output(f"❌ {message}", is_error=True)
        self.main_screen.call_after_refresh(self.main_screen._focus_command_block, new_block)