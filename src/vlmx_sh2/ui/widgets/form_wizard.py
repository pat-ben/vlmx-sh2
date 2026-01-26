"""
Form wizard widget.

Provides interactive form-based data collection for entity field values.
"""

from typing import Dict, Any
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Input, Button, Label, Static, TextArea, Checkbox, Select
from textual.containers import Vertical, Horizontal
from textual.message import Message
from ...models.responses import FormRequest, FieldSpec


class FormWizard(Widget):
    """
    Form wizard widget for interactive data collection.
    """
    
    class Submit(Message):
        """Message sent when form is submitted."""
        def __init__(self, data: Dict[str, Any]) -> None:
            super().__init__()
            self.data = data
    
    class Cancel(Message):
        """Message sent when form is cancelled."""
        pass
    
    def __init__(self, wizard_request: FormRequest, show_buttons: bool = True, **kwargs):
        """
        Initialize the form wizard.
        
        Args:
            wizard_request: The wizard request data containing entity info and FieldSpecs
            show_buttons: Whether to show the form's built-in buttons (default True)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.wizard_request = wizard_request
        self.show_buttons = show_buttons
        self.inputs: Dict[str, Widget] = {}  # Can contain Input, TextArea, Checkbox, Select
    
    def compose(self) -> ComposeResult:
        """Compose the form wizard interface using FieldSpec."""
        yield Static(f"✨ {self.wizard_request.title}")
        yield Static("")
        
        with Vertical(id="form-container"):
            for field_spec in self.wizard_request.fields:
                # Create label with required indicator
                label_text = field_spec.label
                if field_spec.required:
                    label_text += " *"
                yield Label(label_text)
                
                # Create input widget based on field type
                input_widget = self._create_input_for_field(field_spec)
                self.inputs[field_spec.name] = input_widget
                yield input_widget
                
                # Show help text if available
                if field_spec.help_text:
                    yield Static(f"💡 {field_spec.help_text}", classes="help-text")
                
                yield Static("")  # Spacing
        
        # Buttons (only if show_buttons is True)
        if self.show_buttons:
            with Horizontal(id="button-container"):
                yield Button(self.wizard_request.submit_label, variant="success", id="submit-btn")
                yield Button(self.wizard_request.cancel_label, variant="error", id="cancel-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-btn":
            self._handle_submit()
        elif event.button.id == "cancel-btn":
            self._handle_cancel()
    
    def _create_input_for_field(self, spec: FieldSpec) -> Widget:
        """Create appropriate input widget based on FieldSpec."""
        value = self.wizard_request.pre_filled_values.get(spec.name, spec.default_value)
        
        match spec.field_type:
            case "text":
                return Input(
                    value=str(value) if value else "",
                    placeholder=spec.placeholder or f"Enter {spec.label.lower()}...",
                    id=f"input-{spec.name}"
                )
            case "textarea":
                return TextArea(
                    text=str(value) if value else "",
                    id=f"textarea-{spec.name}"
                )
            case "number":
                return Input(
                    value=str(value) if value else "",
                    placeholder=spec.placeholder or "0",
                    id=f"input-{spec.name}"
                )
            case "boolean":
                return Checkbox(
                    value=bool(value) if value is not None else False,
                    id=f"checkbox-{spec.name}"
                )
            case "select":
                if spec.options:
                    options = [(option, option) for option in spec.options]
                    return Select(
                        options=options,
                        value=str(value) if value else None,
                        id=f"select-{spec.name}"
                    )
                else:
                    # Fallback to text input if no options
                    return Input(
                        value=str(value) if value else "",
                        placeholder=spec.placeholder or f"Enter {spec.label.lower()}...",
                        id=f"input-{spec.name}"
                    )
            case "date":
                return Input(
                    value=str(value) if value else "",
                    placeholder=spec.placeholder or "YYYY-MM-DD",
                    id=f"input-{spec.name}"
                )
            case _:
                # Default fallback
                return Input(
                    value=str(value) if value else "",
                    placeholder=spec.placeholder or f"Enter {spec.label.lower()}...",
                    id=f"input-{spec.name}"
                )

    def get_form_data(self) -> Dict[str, Any]:
        """Get current form data with proper type conversion."""
        data = {}
        for field_name, input_widget in self.inputs.items():
            if isinstance(input_widget, Input):
                value = input_widget.value.strip()
                if value:  # Only include non-empty values
                    data[field_name] = value
            elif isinstance(input_widget, TextArea):
                value = input_widget.text.strip()
                if value:
                    data[field_name] = value
            elif isinstance(input_widget, Checkbox):
                data[field_name] = input_widget.value
            elif isinstance(input_widget, Select):
                if input_widget.value is not None:
                    data[field_name] = input_widget.value
        return data
    
    def _handle_submit(self) -> None:
        """Handle form submission."""
        data = self.get_form_data()
        self.post_message(self.Submit(data))
    
    def _handle_cancel(self) -> None:
        """Handle form cancellation."""
        self.post_message(self.Cancel())