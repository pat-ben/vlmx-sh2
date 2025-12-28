"""
RecognizedToken model for recognizer stage output.

Extends Token with word recognition and classification results.
"""

from typing import Optional, List
from pydantic import Field

from .token import Token
from .enums import TokenType
from ..words import Word, WordType


class RecognizedToken(Token):
    """
    Token output from recognizer stage.
    
    Extends Token with word recognition and classification results.
    Inherits all Token fields (text, position, was_quoted, operator_after)
    and adds semantic classification.
    
    Additional Fields:
        token_type: Classification of token (WORD, VALUE, or UNKNOWN)
        word: Recognized word object from registry (if matched)
        confidence: Recognition confidence score (0-100)
        suggestions: Suggestions for unrecognized tokens
    
    Examples:
        >>> RecognizedToken(
        ...     text="create",
        ...     position=0,
        ...     token_type=TokenType.WORD,
        ...     word=ActionWord(id="create", ...),
        ...     confidence=100.0
        ... )
    """
    
    token_type: TokenType = Field(
        default=TokenType.UNKNOWN,
        description="Classification of token (set by recognizer)"
    )
    word: Optional[Word] = Field(
        default=None,
        description="Recognized word object from registry"
    )
    confidence: float = Field(
        default=0.0,
        description="Recognition confidence score (0-100)"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for unrecognized tokens"
    )
    
    class Config:
        arbitrary_types_allowed = True
        frozen = False
    
    @property
    def is_recognized(self) -> bool:
        """True if token was recognized as a word from registry."""
        return self.word is not None
    
    @property
    def word_type(self) -> Optional[WordType]:
        """Get the word type if this token was recognized."""
        return self.word.word_type if self.word else None