"""
Record picker widget.

Provides interactive record selection for multi-record entities.
Displays existing records in a table format with "Add New" option.
"""

from typing import Dict, List, Any, Optional
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Button, Label, Static, DataTable
from textual.containers import Vertical, Horizontal
from textual.message import Message
from ...models.results import RecordPickerWizardRequest


class RecordPicker(Widget):
    """
    Record picker widget for selecting from multiple records.
    """
    
    class RecordSelected(Message):
        """Message sent when a record is selected."""
        def __init__(self, record_id: str, record_data: Dict[str, Any]) -> None:
            super().__init__()
            self.record_id = record_id
            self.record_data = record_data
    
    class AddNew(Message):
        """Message sent when user wants to add a new record."""
        pass
    
    class Cancel(Message):
        """Message sent when picker is cancelled."""
        pass
    
    def __init__(self, picker_request: RecordPickerWizardRequest, **kwargs):
        """
        Initialize the record picker.
        
        Args:
            picker_request: The picker request data containing records and display fields
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.picker_request = picker_request
        self.data_table: Optional[DataTable] = None
    
    def compose(self) -> ComposeResult:
        """Compose the record picker interface."""
        yield Static(f"📋 {self.picker_request.title}")
        yield Static("")
        
        # Show records in a data table
        with Vertical(id="records-container"):
            if self.picker_request.records:
                # Create data table for records
                table = DataTable(id="records-table")
                self.data_table = table
                yield table
                
                # Add table headers
                display_fields = self.picker_request.display_fields
                table.add_columns(*display_fields)
                
                # Add table rows
                for i, record in enumerate(self.picker_request.records):
                    row_data = []
                    for field in display_fields:
                        value = record.get(field, "")
                        # Convert value to string for display
                        row_data.append(str(value) if value is not None else "")
                    
                    table.add_row(*row_data, key=str(i))
                
                yield Static("")
            else:
                yield Static("No existing records found.", id="no-records-msg")
                yield Static("")
        
        # Buttons
        with Horizontal(id="button-container"):
            if self.picker_request.show_add_new_option:
                yield Button("➕ Add New", variant="primary", id="add-new-btn")
            yield Button("Cancel", variant="error", id="cancel-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add-new-btn":
            self._handle_add_new()
        elif event.button.id == "cancel-btn":
            self._handle_cancel()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle data table row selection."""
        if self.data_table and event.data_table is self.data_table:
            # Get the selected record index
            row_key = event.row_key
            try:
                record_index = int(row_key)
                if 0 <= record_index < len(self.picker_request.records):
                    selected_record = self.picker_request.records[record_index]
                    
                    # Extract record ID - try common ID fields
                    record_id = (
                        selected_record.get('id') or 
                        selected_record.get('_id') or 
                        str(record_index)
                    )
                    
                    self.post_message(self.RecordSelected(
                        record_id=str(record_id),
                        record_data=selected_record
                    ))
            except (ValueError, IndexError):
                # Invalid selection, ignore
                pass
    
    def _handle_add_new(self) -> None:
        """Handle add new record request."""
        self.post_message(self.AddNew())
    
    def _handle_cancel(self) -> None:
        """Handle picker cancellation."""
        self.post_message(self.Cancel())