# File: src/vlmx_sh2/models/validation/rule.py
"""
Validation rule model.

Defines the ValidationRule Pydantic model for validation rules across parsing stages.
Supports two-tier validation architecture for comprehensive diagnostics.
"""

from typing import Callable, Any, Literal, Union
from pydantic import BaseModel, Field, validator
from vlmx_sh2.enums import IssueStage


class ValidationRule(BaseModel):
    """
    A single validation rule supporting two-tier validation architecture.
    
    Two Types of Validation:
    
    1. Text-Level Validation (Pre-tokenization):
       - Input: Raw text string
       - Blocking: Always True (fundamental failures that prevent parsing)
       - Examples: empty command, max length exceeded, invalid encoding
       - Philosophy: "Fail fast" - can't proceed if we can't even read the input
    
    2. Token-Level Validation (Post-tokenization):
       - Input: List of tokens
       - Blocking: Default False (collect ALL errors for comprehensive diagnostics)
       - Examples: unclosed quotes, mismatched brackets, unrecognized words
       - Philosophy: "Collect all errors" - show user everything wrong in one go
    
    Position information is resolved lazily only when displaying errors to users.
    The validation_level field determines which validation tier this rule belongs to.
    """
    rule_id: str = Field(..., description="Unique identifier (e.g., 'empty_command')")
    stage: IssueStage = Field(..., description="Which stage this rule applies to")
    validation_level: Literal["text", "token"] = Field(
        default="text", 
        description="Validation tier: 'text' for pre-tokenization, 'token' for post-tokenization"
    )
    check: Callable[..., bool] = Field(..., description="Validation function - returns True if valid")
    error_code: str = Field(..., description="Structured error code (e.g., 'vlmx::tokenizer::empty_command')")
    message: Union[str, Callable[..., str]] = Field(..., description="Human-readable error message or function that generates one")
    suggestion: Union[str, Callable[..., str]] = Field(default="", description="Optional suggestion for fixing or function that generates one")
    blocking: bool = Field(
        default=None, 
        description="If True, stage MUST stop on this error. Auto-set based on validation_level if None"
    )

    @validator('blocking', always=True)
    def set_blocking_default(cls, v, values):
        """Set blocking default based on validation level if not explicitly provided."""
        if v is None:
            # Text-level validation is always blocking (fail fast)
            # Token-level validation is non-blocking by default (collect all errors)
            validation_level = values.get('validation_level', 'text')
            return validation_level == 'text'
        return v

    def get_message(self, **kwargs) -> str:
        """Get the error message, resolving callable if necessary."""
        if callable(self.message):
            return self.message(**kwargs)
        return self.message
    
    def get_suggestion(self, **kwargs) -> str:
        """Get the suggestion, resolving callable if necessary."""
        if callable(self.suggestion):
            return self.suggestion(**kwargs)
        return self.suggestion

    class Config:
        arbitrary_types_allowed = True  # Allows Callable type