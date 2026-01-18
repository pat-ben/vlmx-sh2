# File: src/vlmx_sh2/models/validation/rule.py
"""
Validation rule model.

Defines the ValidationRule Pydantic model for validation rules across parsing stages.
"""

from typing import Callable, Any
from pydantic import BaseModel, Field
from vlmx_sh2.enums import IssueStage


class ValidationRule(BaseModel):
    """
    A single validation rule.
    
    Defines validation logic and error reporting for a specific check.
    Rules are organized by parsing stage (IssueStage enum).
    """
    rule_id: str = Field(..., description="Unique identifier (e.g., 'empty_command')")
    stage: IssueStage = Field(..., description="Which stage this rule applies to")
    check: Callable[..., bool] = Field(..., description="Validation function - returns True if valid")
    error_code: str = Field(..., description="Structured error code (e.g., 'vlmx::tokenizer::empty_command')")
    message: str = Field(..., description="Human-readable error message")
    suggestion: str = Field(default="", description="Optional suggestion for fixing")
    position: int = Field(default=0, description="Default character position for error")
    blocking: bool = Field(default=False, description="If True, stage MUST stop on this error")

    class Config:
        arbitrary_types_allowed = True  # Allows Callable type