"""
PARSING STAGE 0/7: Normalization

Pre-tokenization text processing.
Prepares raw input for tokenization by expanding macros and validating command.

This stage operates on raw strings and performs text-level transformations
before the input is broken into tokens.
"""

from ...diag.validator import Validator
from ...core.enums import IssueStage
from ...core.models.validation import ValidationContext
from ..words.macros import expand_macros

# =============================================================================
# PUBLIC API
# =============================================================================


def normalize(input_text: str, context: ValidationContext) -> str:
    """
    Normalize raw input text for parsing.

    Expands macros (cc → create company) and validates text.
    Stores both original and normalized text in context.
    Returns empty string if validation fails.
    """

    # Store original input (not already set at this stage)
    context.input_text = input_text

    # Step 1: Expand command macros (only happens at position 0 to cover edge cases)
    normalized_text = expand_macros(input_text)

    # Step 2: Store normalized text in context
    context.normalized_text = normalized_text

    # Step 3: Text validation using diagnostics shell (BLOCKING)
    if not Validator.validate_text(
        IssueStage.NORMALIZER, context, text=normalized_text
    ):
        return ""  # Blocking validation failed - return empty string

    return normalized_text
