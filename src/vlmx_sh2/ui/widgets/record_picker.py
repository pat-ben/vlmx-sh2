"""
Record picker widget.

Provides interactive record selection for multi-record entities.
Displays existing records in a table format with "Add New" option.
"""

from typing import Dict, List, Any
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Button, Label, Static
from textual.containers import Vertical, Horizontal
from textual.message import Message
from ...models.responses import PickerRequest


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
    
    def __init__(self, picker_request: PickerRequest, **kwargs):
        """
        Initialize the record picker.
        
        Args:
            picker_request: The picker request data containing records and display fields
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.picker_request = picker_request
    
    def compose(self) -> ComposeResult:
        """Compose the record picker interface."""
        yield Static(f"📋 {self.picker_request.title}")
        yield Static("")
        
        # Show records with edit buttons
        with Vertical(id="records-container"):
            if self.picker_request.records:
                yield Static(f"Found {len(self.picker_request.records)} record(s):")
                yield Static("")
                
                # Create a card for each record with an edit button
                for i, record in enumerate(self.picker_request.records):
                    with Horizontal(classes="record-row"):
                        # Show key fields for identification
                        display_parts = []
                        for field in self.picker_request.display_fields:
                            value = record.get(field, "")
                            if value:
                                display_parts.append(f"{field}: {value}")
                        
                        record_info = " | ".join(display_parts[:3])  # Limit to 3 fields for readability
                        if len(display_parts) > 3:
                            record_info += "..."
                            
                        yield Static(record_info, classes="record-info")
                        yield Button("✏️ Edit", variant="primary", id=f"edit-btn-{i}", classes="edit-button")
                
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
        elif event.button.id.startswith("edit-btn-"):
            # Extract record index from button ID
            try:
                record_index = int(event.button.id.replace("edit-btn-", ""))
                self._handle_record_edit(record_index)
            except (ValueError, IndexError):
                # Invalid button ID, ignore
                pass
    
    def _handle_record_edit(self, record_index: int) -> None:
        """Handle edit button click for a specific record."""
        try:
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
            # Invalid record index, ignore
            pass
    
    def _handle_add_new(self) -> None:
        """Handle add new record request."""
        self.post_message(self.AddNew())
    
    def _handle_cancel(self) -> None:
        """Handle picker cancellation."""
        self.post_message(self.Cancel())