"""
Request models for interactive user workflows.

These models trigger UI interactions that wait for user input before continuing.
They represent requests for the UI to display wizards, forms, or pickers that
require user interaction to complete the workflow.
"""

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel


class FormRequest(BaseModel):
    """Request to display a form wizard."""
    type: Literal['form_wizard'] = 'form_wizard'
    entity_id: str
    entity_name: Optional[str] = None
    fields: List[str]
    pre_filled_values: Dict[str, str] = {}
    title: str
    modal: bool = True


class PickerRequest(BaseModel):
    """Request to display a record picker for multi-record schemas."""
    type: Literal['record_picker'] = 'record_picker'
    entity_id: str
    entity_name: Optional[str] = None
    records: List[Dict[str, Any]]
    display_fields: List[str]
    show_add_new_option: bool = True
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