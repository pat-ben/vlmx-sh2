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
    Single validation issue from parsing pipeline with rich diagnostic context.
    
    Tracks errors, warnings, and info messages with comprehensive context about
    where and why they occurred, including token-level information for precise
    diagnostics and helpful error messages.
    
    Supports Nushell-quality error reporting with:
    - Character-level positioning (position, end_position)  
    - Token-level context (token_index, related_tokens)
    - Structured error identification (error_code)
    - Documentation links (doc_link)
    - Actionable suggestions (suggestion)
    """
    
    stage: IssueStage = Field(description="Which parsing stage found this issue")
    severity: IssueSeverity = Field(description="Severity level: ERROR, WARNING, or INFO")
    message: str = Field(description="Human-readable description of the issue")
    
    # Character-level positioning
    position: int = Field(default=0, description="Character position in relevant text context (0-indexed)")
    end_position: Optional[int] = Field(default=None, description="Optional end position for multi-character issues")
    
    # Token-level context
    token_index: Optional[int] = Field(default=None, description="Position in token array (0-indexed) for 'error in token X' messaging")
    token_text: Optional[str] = Field(default=None, description="The problematic token text (if applicable)")
    related_tokens: Optional[List[int]] = Field(default=None, description="List of other token indices involved in multi-token errors")
    
    # Structured diagnostics
    error_code: Optional[str] = Field(default=None, description="Structured error identifier like 'vlmx::tokenizer::empty_command'")
    doc_link: Optional[str] = Field(default=None, description="URL to documentation about this error")
    suggestion: Optional[str] = Field(default=None, description="Optional suggestion for fixing the issue")
    
    class Config:
        frozen = False
    
    @property
    def has_token_info(self) -> bool:
        """True if token-level information is available."""
        return self.token_index is not None
    
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