"""
Dynamic entity manager widget with split-screen layout.

Provides a split view with:
- Left panel: Searchable list of existing records
- Right panel: Form for editing selected record or creating new record
"""

from typing import Dict, Any, Optional
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Button, Static, DataTable, Input
from textual.containers import Vertical, Horizontal
from textual.message import Message
from ...models.responses import PickerRequest
from .form_wizard import FormWizard
from ...models.responses import FormRequest
from ...constants import SYSTEM_FIELDS


CSS = """
/* Main layout */
#main-container {
    height: 100%;
    background: $surface;
}

.panel {
    border: round $primary;
    background: $panel;
    height: 100%;
    width: 50%;
    padding: 1 2;
    margin: 1;
}

#left-panel {
    margin-right: 1;
    border: round $accent;
}

#right-panel {
    margin-left: 1;
    border: round $success;
}

/* Panel headers */
.panel-title {
    text-style: bold;
    color: $text;
    background: $primary;
    padding: 0 1;
    text-align: center;
    border: round;
    margin-bottom: 1;
}

#left-panel .panel-title {
    background: $accent;
    color: $text;
}

#right-panel .panel-title {
    background: $success;
    color: $text;
}

/* Search and table styling */
.search-box {
    border: round $accent;
    margin-bottom: 1;
    background: $surface;
}

#records-table {
    border: round;
    scrollbar-background: $panel;
    scrollbar-color: $accent;
}

.record-count {
    text-style: italic;
    color: $text-muted;
    margin-top: 1;
    text-align: center;
    background: $surface;
    padding: 0 1;
    border: round;
}

/* Form styling */
.form-placeholder {
    text-align: center;
    color: $text-muted;
    margin: 3 2;
    padding: 2;
    border: dashed $text-muted;
    background: $surface;
}

#form-container {
    min-height: 20;
    background: $surface;
    border: round;
    padding: 1;
    margin-bottom: 1;
}

.form-actions {
    margin-top: 1;
    padding: 1;
    background: $panel;
    border: round;
    align: center middle;
}

.form-actions Button {
    margin: 0 1;
    min-width: 12;
}

/* Visual feedback */
.error {
    color: $error;
    text-style: bold;
    background: $error 20%;
    padding: 1;
    border: round;
}

.header {
    text-style: bold;
    text-align: center;
    margin-bottom: 2;
    color: $primary;
    background: $primary 20%;
    padding: 1;
    border: round;
}

/* Form field styling */
Input {
    border: round;
    background: $surface;
    margin-bottom: 1;
}

Label {
    color: $text;
    text-style: bold;
    margin-bottom: 0;
}

/* Table row hover effect */
DataTable > .datatable--cursor {
    background: $accent 30%;
}
"""




class DynamicEntityManager(Widget):
    """
    Split-screen dynamic entity manager for multi-record schemas.
    """
    
    class RecordSelected(Message):
        """Message sent when a record is selected for editing."""
        def __init__(self, record_id: str, record_data: Dict[str, Any]) -> None:
            super().__init__()
            self.record_id = record_id
            self.record_data = record_data
    
    class NewRecord(Message):
        """Message sent when user wants to create a new record."""
        pass
    
    class FormSubmitted(Message):
        """Message sent when form is submitted."""
        def __init__(self, form_data: Dict[str, Any], record_id: Optional[str] = None) -> None:
            super().__init__()
            self.form_data = form_data
            self.record_id = record_id  # None for new record, ID for update
    
    class Cancel(Message):
        """Message sent when manager is cancelled."""
        pass
    
    def __init__(self, picker_request: PickerRequest, **kwargs):
        """
        Initialize the dynamic entity manager.
        
        Args:
            picker_request: The picker request data containing records and display fields
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.picker_request = picker_request
        self.data_table: Optional[DataTable] = None
        self.form_widget: Optional[FormWizard] = None
        self.search_input: Optional[Input] = None
        self.selected_record_id: Optional[str] = None
        self.all_records = picker_request.records.copy()
        self.filtered_records = picker_request.records.copy()
    
    def compose(self) -> ComposeResult:
        """Compose the split-screen interface."""
        yield Static(f"🔧 {self.picker_request.title}", classes="header")
        
        with Horizontal(id="main-container"):
            # Left panel - Record list
            with Vertical(id="left-panel", classes="panel"):
                yield Static("📊 Browse Records", classes="panel-title")
                
                # Search box with better placeholder
                entity_name = self.picker_request.entity_id.title()
                yield Input(
                    placeholder=f"🔍 Search {entity_name.lower()} records...", 
                    id="search-input",
                    classes="search-box"
                )
                
                # Records table
                table = DataTable(id="records-table")
                table.cursor_type = "row"
                table.zebra_stripes = True
                table.show_header = True
                self.data_table = table
                yield table
                
                # Record count with better formatting
                total_records = len(self.all_records)
                record_text = "record" if total_records == 1 else "records"
                yield Static(
                    f"📈 Total: {total_records} {record_text}",
                    id="record-count",
                    classes="record-count"
                )
            
            # Right panel - Form
            with Vertical(id="right-panel", classes="panel"):
                yield Static("📝 Edit Details", classes="panel-title")
                
                # Form area (will be populated dynamically)
                with Vertical(id="form-container"):
                    yield Static(
                        f"👈 Select a {self.picker_request.entity_id} record from the table to edit it\n\n💡 Or click 'New Record' below to create a fresh one",
                        id="form-placeholder",
                        classes="form-placeholder"
                    )
                
                # Action buttons with better spacing and labels
                with Horizontal(id="form-actions", classes="form-actions"):
                    yield Button("✨ New Record", variant="primary", id="new-btn")
                    yield Button("💾 Submit", variant="success", id="save-btn", disabled=True)
                    yield Button("🚫 Cancel", variant="error", id="cancel-btn")
    
    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self._setup_table()
        self.search_input = self.query_one("#search-input", Input)
    
    def _setup_table(self) -> None:
        """Set up the records table."""
        if not self.data_table:
            return
        
        # Add columns based on display fields with better formatting
        for field in self.picker_request.display_fields:
            # Create a nice column header
            header = field.replace('_', ' ').title()
            # Add icons for common field types
            if 'date' in field.lower():
                header = f"📅 {header}"
            elif field.lower() in ['name', 'title', 'headline']:
                header = f"📝 {header}"
            elif field.lower() in ['category', 'type', 'status']:
                header = f"🏷️ {header}"
            
            self.data_table.add_column(header, key=field)
        
        # Add records
        self._populate_table()
    
    def _populate_table(self) -> None:
        """Populate table with filtered records."""
        if not self.data_table:
            return
        
        self.data_table.clear()
        
        for i, record in enumerate(self.filtered_records):
            row_data = []
            for field in self.picker_request.display_fields:
                value = record.get(field, "")
                # Truncate long values for display
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                row_data.append(str(value))
            
            # Use record index as row key

            self.data_table.add_row(*row_data, key=str(i))
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            search_term = event.value.lower().strip()
            
            if not search_term:
                self.filtered_records = self.all_records.copy()
            else:
                # Filter records based on search term
                self.filtered_records = []
                for record in self.all_records:
                    # Search in all display fields
                    for field in self.picker_request.display_fields:
                        value = str(record.get(field, "")).lower()
                        if search_term in value:
                            self.filtered_records.append(record)
                            break
            
            # Update table
            self._populate_table()
            
            # Update record count with better formatting
            count_widget = self.query_one("#record-count", Static)
            filtered_count = len(self.filtered_records)
            total_count = len(self.all_records)
            
            if filtered_count == total_count:
                count_widget.update(f"📈 Total: {total_count} record{'s' if total_count != 1 else ''}")
            else:
                count_widget.update(f"🔍 Showing: {filtered_count} of {total_count} record{'s' if total_count != 1 else ''}")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle record selection."""
        if event.data_table is self.data_table:
            try:
                # Extract the actual value from RowKey object
                if event.row_key.value is None:
                    return
                record_index = int(event.row_key.value)
                if 0 <= record_index < len(self.filtered_records):
                    selected_record = self.filtered_records[record_index]
                    
                    # Extract record ID
                    record_id = (
                        selected_record.get('id') or 
                        selected_record.get('_id') or 
                        str(record_index)
                    )
                    
                    self.selected_record_id = str(record_id)
                    
                    # Show loading state
                    form_container = self.query_one("#form-container")
                    form_container.remove_children()
                    form_container.mount(Static("⏳ Loading record details...", classes="form-placeholder"))
                    
                    self._load_record_form(selected_record)
                    
                    # Enable submit button
                    save_btn = self.query_one("#save-btn", Button)
                    save_btn.disabled = False
                    
            except (ValueError, IndexError, AttributeError):
                pass
    
    def _load_record_form(self, record_data: Dict[str, Any]) -> None:
        """Load the form with record data for editing."""
        try:
            from ...words import get_word
            from ...models.words import EntityWord
            
            # Get entity model
            entity_word = get_word(self.picker_request.entity_id)
            if not entity_word or not isinstance(entity_word, EntityWord):
                return
            
            # Create form wizard request
            requested_fields = [
                field for field in entity_word.entity_model.model_fields.keys() 
                if field not in SYSTEM_FIELDS
            ]
            
            # Extract pre-filled values
            pre_filled_values = {}
            for field in requested_fields:
                if field in record_data and record_data[field] is not None:
                    pre_filled_values[field] = str(record_data[field])
            
            form_wizard_request = FormRequest(
                entity_id=self.picker_request.entity_id,
                entity_name=self.picker_request.entity_name,
                fields=requested_fields,
                pre_filled_values=pre_filled_values,
                title=f"Edit {self.picker_request.entity_id.title()} Record"
            )
            
            # Create form widget without built-in buttons
            self.form_widget = FormWizard(form_wizard_request, show_buttons=False)
            
            # Replace form placeholder with actual form
            form_container = self.query_one("#form-container")
            form_container.remove_children()
            form_container.mount(self.form_widget)
            
        except Exception as e:
            # Show error in form area
            form_container = self.query_one("#form-container")
            form_container.remove_children()
            form_container.mount(Static(f"Error loading form: {str(e)}", classes="error"))
    
    def _load_new_record_form(self) -> None:
        """Load an empty form for creating a new record."""
        try:
            from ...words import get_word
            from ...models.words import EntityWord
            
            # Get entity model
            entity_word = get_word(self.picker_request.entity_id)
            if not entity_word or not isinstance(entity_word, EntityWord):
                return
            
            # Create form wizard request for new record
            requested_fields = [
                field for field in entity_word.entity_model.model_fields.keys() 
                if field not in SYSTEM_FIELDS
            ]
            
            form_wizard_request = FormRequest(
                entity_id=self.picker_request.entity_id,
                entity_name=self.picker_request.entity_name,
                fields=requested_fields,
                pre_filled_values={},  # Empty for new record
                title=f"New {self.picker_request.entity_id.title()} Record"
            )
            
            # Create form widget without built-in buttons
            self.form_widget = FormWizard(form_wizard_request, show_buttons=False)
            self.selected_record_id = None  # Clear selection for new record
            
            # Replace form placeholder with actual form
            form_container = self.query_one("#form-container")
            form_container.remove_children()
            form_container.mount(self.form_widget)
            
            # Enable save button
            save_btn = self.query_one("#save-btn", Button)
            save_btn.disabled = False
            
        except Exception as e:
            # Show error in form area
            form_container = self.query_one("#form-container")
            form_container.remove_children()
            form_container.mount(Static(f"Error creating new form: {str(e)}", classes="error"))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "new-btn":
            self._load_new_record_form()
        elif event.button.id == "save-btn":
            self._handle_save()
        elif event.button.id == "cancel-btn":
            self._handle_cancel()
    
    def _handle_save(self) -> None:
        """Handle form save."""
        if not self.form_widget:
            return
        
        # Get form data
        form_data = self.form_widget.get_form_data()
        
        # Post form submission message
        self.post_message(self.FormSubmitted(
            form_data=form_data,
            record_id=self.selected_record_id
        ))
    
    def _handle_cancel(self) -> None:
        """Handle cancellation."""
        self.post_message(self.Cancel())