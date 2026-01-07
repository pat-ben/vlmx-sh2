"""
Dynamic entity screen with split layout.

Provides a split-screen interface for managing multi-record dynamic entities.
"""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from ..widgets.dynamic_entity_manager import DynamicEntityManager
from ...models.results import RecordPickerWizardRequest


class DynamicEntityScreen(ModalScreen):
    """
    Modal screen for dynamic entity management.
    """
    
    def __init__(self, picker_request: RecordPickerWizardRequest, command_block, **kwargs):
        """
        Initialize the dynamic entity screen.
        
        Args:
            picker_request: The picker request data
            command_block: Reference to the command block for result handling
            **kwargs: Additional screen arguments
        """
        super().__init__(**kwargs)
        self.picker_request = picker_request
        self.command_block = command_block
    
    def compose(self) -> ComposeResult:
        """Compose the screen content."""
        yield DynamicEntityManager(self.picker_request, id="entity-manager")
    
    async def on_dynamic_entity_manager_form_submitted(self, message: DynamicEntityManager.FormSubmitted) -> None:
        """Handle form submission from the dynamic entity manager."""
        try:
            # Process the form submission
            await self._process_form_submission(message)
            
        except Exception as e:
            self.command_block.show_output(f"Error processing form: {str(e)}", is_error=True)
    
    async def on_dynamic_entity_manager_cancel(self, message: DynamicEntityManager.Cancel) -> None:
        """Handle cancellation from the dynamic entity manager."""
        self.dismiss()
        self.app.call_after_refresh(self.command_block._create_new_prompt)
    
    async def _process_form_submission(self, message: DynamicEntityManager.FormSubmitted) -> None:
        """Process the form submission."""
        from ...storage.database import update_dynamic_entity_record, save_entity, load_entity
        from ...handlers.utils import get_company_name_from_context
        
        # Get current context and company
        context = self.command_block.context
        company_name = get_company_name_from_context(context)
        
        if not company_name:
            self.command_block.show_output("Error: Not in organization context", is_error=True)
            return
        
        entity_type = self.picker_request.entity_id
        form_data = message.form_data
        
        if message.record_id is None:
            # Creating new record
            self.command_block.show_output(f"Creating new {entity_type} record...")
            
            # Load current entity data (array)
            current_data = load_entity(entity_type, company_name, context) or []
            
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
            save_result = save_entity(entity_type, current_data, company_name, context)
            
            if save_result.get("success", False):
                self.command_block.show_output(f"✅ Created new {entity_type} record")
                # Refresh the screen to show new record
                await self._refresh_screen()
            else:
                error_msg = save_result.get("error", f"Failed to create {entity_type} record")
                self.command_block.show_output(f"❌ {error_msg}", is_error=True)
        
        else:
            # Updating existing record
            self.command_block.show_output(f"Updating {entity_type} record (ID: {message.record_id})...")
            
            # Update the record in the array
            update_result = update_dynamic_entity_record(
                entity_type=entity_type,
                record_id=message.record_id,
                updated_fields=form_data,
                company_name=company_name,
                context=context
            )
            
            if update_result.get("success", False):
                self.command_block.show_output(f"✅ Updated {entity_type} record")
                # Refresh the screen to show updated record
                await self._refresh_screen()
            else:
                error_msg = update_result.get("error", f"Failed to update {entity_type} record")
                self.command_block.show_output(f"❌ {error_msg}", is_error=True)
    
    async def _refresh_screen(self) -> None:
        """Refresh the screen with updated data."""
        try:
            # Reload records from database
            from ...storage.database import load_entity
            from ...handlers.utils import get_company_name_from_context
            
            context = self.command_block.context
            company_name = get_company_name_from_context(context)
            entity_type = self.picker_request.entity_id
            
            # Load fresh data
            updated_records = load_entity(entity_type, company_name, context) or []
            
            # Update picker request with fresh data
            self.picker_request.records = updated_records
            
            # Get the entity manager and refresh its data
            entity_manager = self.query_one("#entity-manager", DynamicEntityManager)
            entity_manager.all_records = updated_records.copy()
            entity_manager.filtered_records = updated_records.copy()
            entity_manager._populate_table()
            
            # Update record count
            count_widget = entity_manager.query_one("#record-count")
            count_widget.update(f"Total: {len(updated_records)} records")
            
        except Exception as e:
            self.command_block.show_output(f"Error refreshing screen: {str(e)}", is_error=True)