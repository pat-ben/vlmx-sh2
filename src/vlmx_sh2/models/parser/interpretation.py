"""
InterpretedToken model for interpreter stage output.

Extends RecognizedToken with interpretation metadata to track
what modifications the Interpreter made (corrections, injections).
"""

from typing import Optional
from pydantic import Field

from .recognition import RecognizedToken


class InterpretedToken(RecognizedToken):
    """
    Token after interpretation stage.
    
    Extends RecognizedToken with metadata about interpreter modifications.
    Tracks whether the token was corrected (typo fix) or inferred (injected).
    
    Additional Fields:
        was_inferred: True if this token was injected by expression inference
        was_corrected: True if this token was corrected via fuzzy matching
        original_text: Original text before correction (only if was_corrected)
    
    Examples:
        # Corrected token (typo fixed)
        >>> InterpretedToken(
        ...     text="company",
        ...     token_type=TokenType.WORD,
        ...     word=company_word,
        ...     was_corrected=True,
        ...     original_text="compny"
        ... )
        
        # Inferred token (injected)
        >>> InterpretedToken(
        ...     text="add",
        ...     token_type=TokenType.WORD,
        ...     word=add_word,
        ...     was_inferred=True
        ... )
        
        # Unchanged token (passed through)
        >>> InterpretedToken(
        ...     text="currency",
        ...     token_type=TokenType.WORD,
        ...     word=currency_word
        ...     # was_inferred=False, was_corrected=False by default
        ... )
    """
    
    # Interpretation metadata
    was_inferred: bool = Field(
        default=False,
        description="True if this token was injected by expression inference"
    )
    
    was_corrected: bool = Field(
        default=False,
        description="True if this token was corrected via fuzzy matching"
    )
    
    original_text: Optional[str] = Field(
        default=None,
        description="Original text before correction (only if was_corrected)"
    )