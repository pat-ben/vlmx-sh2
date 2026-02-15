"""
ValidationIssue model for individual validation problems.

Represents a single error, warning, or info message from any parsing stage
with rich diagnostic information for Nushell-quality error reporting.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from vlmx_sh2.enums import IssueSeverity, IssueStage


class ValidationIssue(BaseModel):
    """
    Single validation issue from parsing pipeline with diagnostic context.
    
    Tracks errors, warnings, and info messages with context about where and why 
    they occurred. Position information is resolved lazily only when displaying 
    errors to users.
    
    Supports rich error reporting with:
    - Token context for position resolution (token_text)
    - Structured error identification (error_code)
    - Documentation links (doc_link)
    - Actionable suggestions (suggestion)
    """
    
    stage: IssueStage = Field(description="Which parsing stage found this issue")
    severity: IssueSeverity = Field(description="Severity level: ERROR, WARNING, or INFO")
    message: str = Field(description="Human-readable description of the issue")
    
    # Token context (for lazy position resolution)
    token_text: Optional[str] = Field(default=None, description="The problematic token text (used for position resolution)")
    
    # Structured diagnostics
    error_code: Optional[str] = Field(default=None, description="Structured error identifier like 'vlmx::tokenizer::empty_command'")
    doc_link: Optional[str] = Field(default=None, description="URL to documentation about this error")
    suggestion: Optional[str] = Field(default=None, description="Optional suggestion for fixing the issue")
    
    class Config:
        frozen = False
    
    @property
    def is_error(self) -> bool:
        """True if this is an error-level issue."""
        return self.severity == IssueSeverity.ERROR
    
    @property
    def is_warning(self) -> bool:
        """True if this is a warning-level issue."""
        return self.severity == IssueSeverity.WARNING
    
    @property
    def is_info(self) -> bool:
        """True if this is an info-level issue."""
        return self.severity == IssueSeverity.INFO