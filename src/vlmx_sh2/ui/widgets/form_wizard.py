"""
Form wizard widget.

Provides interactive form-based data collection for entity attributes.
"""

from typing import Dict
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Input, Button, Label, Static
from textual.containers import Vertical, Horizontal
from textual.message import Message
from ...models.responses import FormRequest


class FormWizard(Widget):
    """
    Form wizard widget for interactive data collection.
    """
    
    class Submit(Message):
        """Message sent when form is submitted."""
        def __init__(self, data: Dict[str, str]) -> None:
            super().__init__()
            self.data = data
    
    class Cancel(Message):
        """Message sent when form is cancelled."""
        pass
    
    def __init__(self, wizard_request: FormRequest, show_buttons: bool = True, **kwargs):
        """
        Initialize the form wizard.
        
        Args:
            wizard_request: The wizard request data containing entity info and fields
            show_buttons: Whether to show the form's built-in buttons (default True)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.wizard_request = wizard_request
        self.show_buttons = show_buttons
        self.inputs: Dict[str, Input] = {}
    
    def compose(self) -> ComposeResult:
        """Compose the form wizard interface."""
        yield Static(f"✨ {self.wizard_request.title}")
        yield Static("")
        
        with Vertical(id="form-container"):
            for field_name in self.wizard_request.fields:
                field_label = field_name.replace("_", " ").title()
                yield Label(f"{field_label}:")
                
                # Get pre-filled value if available
                prefilled_value = self.wizard_request.pre_filled_values.get(field_name, "")
                
                # Create input field
                input_widget = Input(
                    value=prefilled_value,
                    placeholder=f"Enter {field_label.lower()}...",
                    id=f"input-{field_name}"
                )
                self.inputs[field_name] = input_widget
                yield input_widget
                yield Static("")  # Spacing
        
        # Buttons (only if show_buttons is True)
        if self.show_buttons:
            with Horizontal(id="button-container"):
                yield Button("Submit", variant="success", id="submit-btn")
                yield Button("Cancel", variant="error", id="cancel-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-btn":
            self._handle_submit()
        elif event.button.id == "cancel-btn":
            self._handle_cancel()
    
    def get_form_data(self) -> Dict[str, str]:
        """Get current form data."""
        data = {}
        for field_name, input_widget in self.inputs.items():
            value = input_widget.value.strip()
            if value:  # Only include non-empty values
                data[field_name] = value
        return data
    
    def _handle_submit(self) -> None:
        """Handle form submission."""
        data = self.get_form_data()
        self.post_message(self.Submit(data))
    
    def _handle_cancel(self) -> None:
        """Handle form cancellation."""
        self.post_message(self.Cancel())