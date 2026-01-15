"""
ValidationIssue model for individual validation problems.

Represents a single error, warning, or info message from any parsing stage.
"""

from typing import Optional
from pydantic import BaseModel, Field

from vlmx_sh2.enums import IssueSeverity, IssueStage


class ValidationIssue(BaseModel):
    """
    Single validation issue from parsing pipeline.
    
    Tracks errors, warnings, and info messages with context about
    where and why they occurred.
    
    """
    
    stage: IssueStage = Field(description="Which parsing stage found this issue")
    severity: IssueSeverity = Field(description="Severity level: ERROR, WARNING, or INFO")
    message: str = Field(description="Human-readable description of the issue")
    position: int = Field(default=0, description="Character position in original input (0-indexed)")
    end_position: Optional[int] = Field(default=None, description="Optional end position for multi-character issues")
    token_text: Optional[str] = Field(default=None, description="The problematic token text (if applicable)")
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