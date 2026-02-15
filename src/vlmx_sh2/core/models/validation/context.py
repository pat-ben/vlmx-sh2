"""
ValidationContext model for accumulating validation issues.

Container for all validation issues found during parsing, with utilities
for checking error states and organizing issues by stage/severity.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ...enums import IssueSeverity, IssueStage
from .issue import ValidationIssue


class ValidationContext(BaseModel):
    """
    Container for all validation issues across parsing stages.

    Accumulates errors, warnings, and info messages as parsing progresses.
    Provides utilities for checking validation state and organizing issues.
    """

    issues: List[ValidationIssue] = Field(
        default_factory=list, description="List of all validation issues found"
    )
    input_text: str = Field(
        default="",
        description="Original raw input typed by user (never modified, used for user-facing error messages)",
    )
    normalized_text: str = Field(
        default="",
        description="Normalized text after macro expansion (what was tokenized, token positions reference this)",
    )

    class Config:
        frozen = False

    # ==================== ADD ISSUE METHODS ====================

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue to the context."""
        self.issues.append(issue)

    def add_error(
        self,
        stage: IssueStage,
        message: str,
        token_text: Optional[str] = None,
        error_code: Optional[str] = None,
        doc_link: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """
        Add an error-level issue with diagnostic information.

        Position information is resolved lazily when displaying errors.
        Use token_text to provide context for position resolution.
        """
        self.issues.append(
            ValidationIssue(
                stage=stage,
                severity=IssueSeverity.ERROR,
                message=message,
                token_text=token_text,
                error_code=error_code,
                doc_link=doc_link,
                suggestion=suggestion,
            )
        )

    def add_warning(
        self,
        stage: IssueStage,
        message: str,
        token_text: Optional[str] = None,
        error_code: Optional[str] = None,
        doc_link: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """
        Add a warning-level issue with diagnostic information.

        Position information is resolved lazily when displaying errors.
        Use token_text to provide context for position resolution.
        """
        self.issues.append(
            ValidationIssue(
                stage=stage,
                severity=IssueSeverity.WARNING,
                message=message,
                token_text=token_text,
                error_code=error_code,
                doc_link=doc_link,
                suggestion=suggestion,
            )
        )

    def add_info(
        self,
        stage: IssueStage,
        message: str,
        token_text: Optional[str] = None,
        error_code: Optional[str] = None,
        doc_link: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """
        Add an info-level issue with diagnostic information.

        Position information is resolved lazily when displaying errors.
        Use token_text to provide context for position resolution.
        """
        self.issues.append(
            ValidationIssue(
                stage=stage,
                severity=IssueSeverity.INFO,
                message=message,
                token_text=token_text,
                error_code=error_code,
                doc_link=doc_link,
                suggestion=suggestion,
            )
        )

    def add_error_from_token(
        self,
        stage: IssueStage,
        message: str,
        token,  # Can be Token, ClassifiedToken, or RecognizedToken
        error_code: Optional[str] = None,
        suggestion: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Add error using token's text for position resolution.

        Convenience method that extracts token text for lazy position resolution.
        Position is resolved only when displaying errors to users.
        """
        self.add_error(
            stage=stage,
            message=message,
            token_text=token.text,
            error_code=error_code,
            suggestion=suggestion,
            **kwargs,
        )

    def add_warning_from_token(
        self,
        stage: IssueStage,
        message: str,
        token,  # Can be Token, ClassifiedToken, or RecognizedToken
        error_code: Optional[str] = None,
        suggestion: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Add warning using token's text for position resolution.

        Convenience method that extracts token text for lazy position resolution.
        Position is resolved only when displaying errors to users.
        """
        self.add_warning(
            stage=stage,
            message=message,
            token_text=token.text,
            error_code=error_code,
            suggestion=suggestion,
            **kwargs,
        )

    def add_info_from_token(
        self,
        stage: IssueStage,
        message: str,
        token,  # Can be Token, ClassifiedToken, or RecognizedToken
        error_code: Optional[str] = None,
        suggestion: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Add info using token's text for position resolution.

        Convenience method that extracts token text for lazy position resolution.
        Position is resolved only when displaying errors to users.
        """
        self.add_info(
            stage=stage,
            message=message,
            token_text=token.text,
            error_code=error_code,
            suggestion=suggestion,
            **kwargs,
        )

    # ==================== QUERY METHODS ====================

    def has_issues(self) -> bool:
        """True if any issues (error, warning, or info) exist."""
        return len(self.issues) > 0

    def has_errors(self) -> bool:
        """True if any error-level issues exist."""
        return any(issue.is_error for issue in self.issues)

    def has_warnings(self) -> bool:
        """True if any warning-level issues exist."""
        return any(issue.is_warning for issue in self.issues)

    def is_valid(self) -> bool:
        """True if no errors exist (warnings are allowed)."""
        return not self.has_errors()

    # ==================== FILTERING PROPERTIES ====================

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all error-level issues."""
        return [issue for issue in self.issues if issue.is_error]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues."""
        return [issue for issue in self.issues if issue.is_warning]

    @property
    def infos(self) -> List[ValidationIssue]:
        """Get all info-level issues."""
        return [issue for issue in self.issues if issue.is_info]

    # ==================== GROUPING METHODS ====================

    def issues_by_stage(self) -> Dict[IssueStage, List[ValidationIssue]]:
        """Group issues by stage."""
        grouped: Dict[IssueStage, List[ValidationIssue]] = {
            stage: [] for stage in IssueStage
        }
        for issue in self.issues:
            grouped[issue.stage].append(issue)
        return grouped

    def issues_by_severity(self) -> Dict[IssueSeverity, List[ValidationIssue]]:
        """Group issues by severity."""
        grouped: Dict[IssueSeverity, List[ValidationIssue]] = {
            severity: [] for severity in IssueSeverity
        }
        for issue in self.issues:
            grouped[issue.severity].append(issue)
        return grouped

    # ==================== STATISTICS ====================

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len(self.warnings)

    @property
    def info_count(self) -> int:
        """Count of info-level issues."""
        return len(self.infos)

    @property
    def total_count(self) -> int:
        """Total count of all issues."""
        return len(self.issues)
