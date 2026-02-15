"""
TokensResult - Intermediate result for parser stages 0-6.

Represents the output of text analysis stages (0-6) before command building (stage 7).
This separates parsing concerns (text → tokens + AST) from building concerns (tokens → command).
"""

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field

from ..validation import ValidationContext
from .filtering import FilterExpression

if TYPE_CHECKING:
    from .interpretation import InterpretedToken
    from .recognition import RecognizedToken


class TokensResult(BaseModel):
    """
    Result from parser stages 0-6: text analysis → tokens + filter AST.

    This is the output of the Parser.parse() method after it has analyzed
    the input text but before building a ParsedCommand. The CommandBuilder
    uses this to construct the final ParsedCommand.

    Fields:
        input_text: Original user input
        command_tokens: Interpreted tokens for command portion (outside [ ])
        filter_tokens: Recognized tokens for filter portion (inside [ ])
        filter_expression: Parsed filter AST (or None if no filters)
        validation_context: Context with errors/warnings from parsing stages
        is_valid: Whether parsing stages succeeded (no blocking errors)
    """

    # Core parsing data
    input_text: str = Field(description="Original user input text")

    # Token lists (split by command vs filter)
    command_tokens: List = Field(
        default_factory=list,
        description="Interpreted tokens from command parsing (outside [ ])",
    )

    filter_tokens: List = Field(
        default_factory=list,
        description="Recognized tokens from filter parsing (inside [ ])",
    )

    # Parsed filter expression
    filter_expression: Optional[FilterExpression] = Field(
        default=None,
        description="Parsed filter AST (None if no filters or parse failed)",
    )

    # Validation context
    validation_context: ValidationContext = Field(
        description="Context with errors, warnings, and metadata from parsing"
    )

    # Validation result
    is_valid: bool = Field(
        default=False,
        description="True if parsing stages succeeded (no blocking errors)",
    )

    class Config:
        arbitrary_types_allowed = True

    # =============================================================================
    # Convenience Properties
    # =============================================================================

    @property
    def errors(self) -> List[str]:
        """Get formatted error messages from validation context."""
        from ....diag import DiagnosticFormatter

        formatter = DiagnosticFormatter()

        formatted_errors = []
        if self.validation_context.has_errors():
            for error in self.validation_context.errors:
                formatted_error = formatter.format_issue(error, self.input_text)
                formatted_errors.append(formatted_error)

        return formatted_errors

    @property
    def suggestions(self) -> List[str]:
        """Get formatted suggestions from validation context."""
        from ....diag import DiagnosticFormatter

        formatter = DiagnosticFormatter()
        return formatter.get_formatted_suggestions(self.validation_context)

    @property
    def has_command_tokens(self) -> bool:
        """True if we have command tokens to build from."""
        return len(self.command_tokens) > 0

    @property
    def has_filter_tokens(self) -> bool:
        """True if we have filter tokens."""
        return len(self.filter_tokens) > 0
