"""
Result models for completed operations.

These Pydantic models represent final responses that complete execution flow.
Results are UI-agnostic and serializable, with the UI layer interpreting them
to decide how to render the final outcome.
"""

from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel


class CommandResult(BaseModel):
    """Result for normal command execution."""
    type: Literal['command_result'] = 'command_result'
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResult(BaseModel):
    """Error response from handler."""
    type: Literal['error'] = 'error'
    errors: List[str]
    suggestions: List[str] = []


class StorageResult(BaseModel):
    """Standardized result for all storage operations."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None