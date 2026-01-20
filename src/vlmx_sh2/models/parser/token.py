"""
Token model for tokenizer stage output.

Contains only text processing results with rich position metadata.
Tokenizer stays "dumb" - just extracts blocks with position tracking.
"""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """
    Token output from tokenizer stage.
    
    Represents a single token extracted from normalized text with rich position
    metadata. Position fields reference the NORMALIZED text (after macro expansion),
    not the original user input. Contains NO semantic or structural classification - 
    that is added by subsequent stages (classifier, recognizer).
    
    Fields:
        text: The actual text of the token (quotes kept as-is from input)
        char_start: Character position where token starts in NORMALIZED text (0-indexed)
        char_end: Character position where token ends in NORMALIZED text (exclusive)
        token_index: Position in token array (0-indexed)
    
    Examples:
        Input:      "cc ACME"
        Normalized: "create company ACME"
        
        >>> Token(text="create", char_start=0, char_end=6, token_index=0)
        >>> Token(text="company", char_start=7, char_end=14, token_index=1)
        >>> Token(text="ACME", char_start=15, char_end=19, token_index=2)
    """
    
    text: str = Field(
        description="The actual text of the token (quotes kept as-is from input)"
    )
    char_start: int = Field(
        description="Character position where token starts in NORMALIZED text (0-indexed)"
    )
    char_end: int = Field(
        description="Character position where token ends in NORMALIZED text (exclusive)"
    )
    token_index: int = Field(
        description="Position in token array (0-indexed)"
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