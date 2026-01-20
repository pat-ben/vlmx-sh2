"""
Token model for tokenizer stage output.

Contains only text processing results with rich position metadata.
Tokenizer stays "dumb" - just extracts blocks with position tracking.
"""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """
    Token output from tokenizer stage.
    
    Represents a single token extracted from input text with rich position
    metadata. Contains NO semantic or structural classification - that is
    added by subsequent stages (classifier, recognizer).
    
    Fields:
        text: The actual text of the token (quotes kept as-is from input)
        char_start: Character position where token starts in original input (0-indexed)
        char_end: Character position where token ends (exclusive, like Python slicing)
        token_index: Position in token array (0-indexed)
    
    Examples:
        >>> Token(text="create", char_start=0, char_end=6, token_index=0)
        >>> Token(text='"ACME"', char_start=15, char_end=21, token_index=2)
        >>> Token(text="vision", char_start=22, char_end=28, token_index=3)
    """
    
    text: str = Field(
        description="The actual text of the token (quotes kept as-is from input)"
    )
    char_start: int = Field(
        description="Character position where token starts in tokenizer input (0-indexed)"
    )
    char_end: int = Field(
        description="Character position where token ends (exclusive, like Python slicing)"
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