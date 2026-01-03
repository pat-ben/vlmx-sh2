"""
Form wizard widget for VLMX DSL.

Provides interactive form-based data collection for entity attributes.
"""

from typing import Dict, Any, Optional
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Input, Button, Label, Static
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.message import Message
try:
    from ...models.results import FormWizardRequest
except ImportError:
    from vlmx_sh2.models.results import FormWizardRequest


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
    
    result_ready = reactive(False)
    form_data: Dict[str, str] = {}
    
    def __init__(self, wizard_request: FormWizardRequest, **kwargs):
        """
        Initialize the form wizard.
        
        Args:
            wizard_request: The wizard request data containing entity info and fields
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.wizard_request = wizard_request
        self.inputs: Dict[str, Input] = {}
        
    async def wait_for_result(self) -> Dict[str, Any]:
        """
        Wait for user to complete the form wizard.
        
        Returns:
            Dictionary containing the form results or cancellation status
        """
        await self.watch_result_ready(self.result_ready)
        return self.form_data
    
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
        
        # Buttons
        with Horizontal(id="button-container"):
            yield Button("Submit", variant="success", id="submit-btn")
            yield Button("Cancel", variant="error", id="cancel-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-btn":
            self._handle_submit()
        elif event.button.id == "cancel-btn":
            self._handle_cancel()
    
    def _handle_submit(self) -> None:
        """Handle form submission."""
        # Collect data from all input fields
        data = {}
        for field_name, input_widget in self.inputs.items():
            value = input_widget.value.strip()
            if value:  # Only include non-empty values
                data[field_name] = value
        
        self.form_data = {"action": "submit", "fields": data}
        self.result_ready = True
        self.post_message(self.Submit(data))
    
    def _handle_cancel(self) -> None:
        """Handle form cancellation."""
        self.form_data = {"action": "cancel"}
        self.result_ready = True
        self.post_message(self.Cancel())