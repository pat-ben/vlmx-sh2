"""
ClassifiedToken model for classifier stage output.

Contains structural classification with quotes stripped and operators identified.
"""

from typing import Optional
from pydantic import BaseModel, Field

from vlmx_sh2.enums.parser import TokenClass, Operator, Bracket


class ClassifiedToken(BaseModel):
    """
    Token with structural classification. Quotes stripped, operators identified.
    
    Represents the output of the classifier stage - tokens that have been
    structurally analyzed and classified, with quotes stripped and operators
    identified. Contains both position metadata (from tokenizer) and structural
    classification (added by classifier).
    
    Fields:
        text: Token text with quotes stripped (classifier's job)
        char_start: Character position where token starts in original input
        char_end: Character position where token ends (exclusive)
        token_index: Position in token array (0-indexed)
        token_class: Structural classification (TEXT, OPERATOR, BRACKET)
        was_quoted: True if originally in quotes (TEXT tokens only), None for OPERATOR/BRACKET
        operator: If OPERATOR class, which operator it is
        bracket: If BRACKET class, which bracket it is
    
    Examples:
        # TEXT token (not quoted)
        >>> ClassifiedToken(text="create", char_start=0, char_end=6, token_index=0, 
        ...                 token_class=TokenClass.TEXT, was_quoted=False)
        
        # TEXT token (was quoted, quotes stripped)
        >>> ClassifiedToken(text="ACME", char_start=15, char_end=21, token_index=2,
        ...                 token_class=TokenClass.TEXT, was_quoted=True)
        
        # OPERATOR token (was_quoted=None by default)
        >>> ClassifiedToken(text="=", char_start=28, char_end=29, token_index=3,
        ...                 token_class=TokenClass.OPERATOR, operator=Operator.EQUAL)
        
        # BRACKET token (was_quoted=None by default)
        >>> ClassifiedToken(text="[", char_start=22, char_end=23, token_index=4,
        ...                 token_class=TokenClass.BRACKET, bracket=Bracket.BRACKET_OPEN)
    """
    
    # Token data
    text: str = Field(
        description="Token text with quotes stripped (classifier's job)"
    )
    
    # Position metadata (inherited/preserved from Token)
    char_start: int = Field(
        description="Character position where token starts in original input (0-indexed)"
    )
    char_end: int = Field(
        description="Character position where token ends (exclusive, like Python slicing)"
    )
    token_index: int = Field(
        description="Position in token array (0-indexed)"
    )
    
    # Structural classification (NEW - added by classifier)
    token_class: TokenClass = Field(
        description="Structural classification (TEXT | OPERATOR | BRACKET)"
    )
    was_quoted: Optional[bool] = Field(
        default=None,
        description="True if originally in quotes (TEXT tokens only, None for non-TEXT tokens)"
    )
    operator: Optional[Operator] = Field(
        default=None,
        description="If OPERATOR class, which operator it is"
    )
    bracket: Optional[Bracket] = Field(
        default=None,
        description="If BRACKET class, which bracket it is"
    )
    
    @property
    def char_length(self) -> int:
        """Return the character length of the token."""
        return self.char_end - self.char_start
    
    @property
    def position(self) -> int:
        """Alias for char_start (backward compatibility)."""
        return self.char_start
    
    class Config:
        frozen = False  # Allow mutation during pipeline