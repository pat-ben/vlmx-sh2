"""
Result models for handler responses.

These Pydantic models represent the data structures returned by handlers,
completely UI-agnostic and serializable. The UI layer interprets these
models to decide how to render them.
"""

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel


class CommandResult(BaseModel):
    """Result for normal command execution."""
    type: Literal['command_result'] = 'command_result'
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class FormWizardRequest(BaseModel):
    """Request to display a form wizard."""
    type: Literal['form_wizard'] = 'form_wizard'
    entity_id: str
    entity_name: Optional[str] = None
    fields: List[str]
    pre_filled_values: Dict[str, str] = {}
    title: str
    modal: bool = True


class QueryWizardRequest(BaseModel):
    """Request to display a query wizard (future implementation)."""
    type: Literal['query_wizard'] = 'query_wizard'
    entity_id: str
    filters: List[str] = []
    aggregations: List[str] = []
    title: str
    modal: bool = True


class ErrorResult(BaseModel):
    """Error response from handler."""
    type: Literal['error'] = 'error'
    errors: List[str]
    suggestions: List[str] = []