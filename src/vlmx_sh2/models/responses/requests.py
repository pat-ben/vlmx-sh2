"""
Request models for interactive user workflows.

These models trigger UI interactions that wait for user input before continuing.
They represent requests for the UI to display wizards, forms, or pickers that
require user interaction to complete the workflow.
"""

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel


class FieldSpec(BaseModel):
    """Specification for a single form field with UI rendering metadata."""
    name: str
    label: str
    field_type: Literal['text', 'number', 'date', 'select', 'boolean', 'textarea']
    required: bool = False
    default_value: Optional[Any] = None
    placeholder: Optional[str] = None
    options: Optional[List[str]] = None  # For select fields
    help_text: Optional[str] = None
    validation_pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None


class ColumnSpec(BaseModel):
    """Specification for a table/picker column with display metadata."""
    name: str
    label: str
    width: Optional[int] = None
    sortable: bool = True


class FormRequest(BaseModel):
    """Request to display a form wizard."""
    type: Literal['form_wizard'] = 'form_wizard'
    entity_id: str
    entity_name: Optional[str] = None
    fields: List[FieldSpec]
    pre_filled_values: Dict[str, Any] = {}
    title: str
    submit_label: str = "Submit"
    cancel_label: str = "Cancel"
    modal: bool = True


class PickerRequest(BaseModel):
    """Request to display a record picker for multi-record schemas."""
    type: Literal['record_picker'] = 'record_picker'
    entity_id: str
    entity_name: Optional[str] = None
    records: List[Dict[str, Any]]
    columns: List[ColumnSpec]
    show_add_new_option: bool = True
    multi_select: bool = False
    title: str
    modal: bool = True


class QueryRequest(BaseModel):
    """Request to display a query wizard (future implementation)."""
    type: Literal['query_wizard'] = 'query_wizard'
    entity_id: str
    filters: List[str] = []
    aggregations: List[str] = []
    title: str
    modal: bool = True