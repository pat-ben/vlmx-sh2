"""
RecognizedToken model for recognizer stage output.

Extends Token with word recognition and value classification results.
"""

from typing import Optional, List
from pydantic import Field

from .token import Token
from vlmx_sh2.enums import TokenType, ValueContext
from ..words import Word, WordType


class RecognizedToken(Token):
    """
    Token output from recognizer stage.
    
    Single model that represents all token types (WORD, VALUE, UNKNOWN).
    Fields are populated based on token_type:
    - WORD tokens: word field is set
    - VALUE tokens: value_context field is set
    - UNKNOWN tokens: suggestions may be provided
    
    Fields:
        token_type: Classification (WORD, VALUE, or UNKNOWN)
        word: Complete Word object from registry (only for WORD tokens)
        value_context: Context for VALUE tokens (SCHEMA, ENTITY, or FIELD)
        confidence: Recognition confidence score (0-100)
        suggestions: Suggestions for unrecognized tokens
    
    Examples:
        # WORD token
        >>> RecognizedToken(
        ...     text="create",
        ...     position=0,
        ...     token_type=TokenType.WORD,
        ...     word=ActionWord(id="create", ...)
        ... )
        
        # VALUE token (schema)
        >>> RecognizedToken(
        ...     text="ACME",
        ...     position=2,
        ...     was_quoted=True,
        ...     token_type=TokenType.VALUE,
        ...     value_context=ValueContext.SCHEMA
        ... )
        
        # VALUE token (entity)
        >>> RecognizedToken(
        ...     text="TechCorp",
        ...     position=2,
        ...     was_quoted=True,
        ...     token_type=TokenType.VALUE,
        ...     value_context=ValueContext.ENTITY
        ... )
        
        # VALUE token (field)
        >>> RecognizedToken(
        ...     text="EUR",
        ...     position=4,
        ...     token_type=TokenType.VALUE,
        ...     value_context=ValueContext.FIELD
        ... )
        
        # UNKNOWN token
        >>> RecognizedToken(
        ...     text="xyz123",
        ...     position=5,
        ...     token_type=TokenType.UNKNOWN,
        ...     suggestions=["create", "update"]
        ... )
    """
    
    token_type: TokenType = Field(
        default=TokenType.UNKNOWN,
        description="Classification: WORD, VALUE, or UNKNOWN"
    )
    
    word: Optional[Word] = Field(
        default=None,
        description="Complete Word object from registry (only for WORD tokens)"
    )
    
    value_context: Optional[ValueContext] = Field(
        default=None,
        description="Context for VALUE tokens: ENTITY or FIELD"
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
    def is_word(self) -> bool:
        """True if this is a recognized word."""
        return self.token_type == TokenType.WORD and self.word is not None
    
    @property
    def is_value(self) -> bool:
        """True if this is a value token."""
        return self.token_type == TokenType.VALUE
    
    @property
    def is_unknown(self) -> bool:
        """True if this is unrecognized."""
        return self.token_type == TokenType.UNKNOWN
    
    @property
    def word_type(self) -> Optional[WordType]:
        """Get WordType if this is a WORD token."""
        return self.word.word_type if self.word else None
    
    @property
    def is_entity_value(self) -> bool:
        """True if this is an entity value (e.g., company name)."""
        return self.token_type == TokenType.VALUE and self.value_context == ValueContext.ENTITY
    
    @property
    def is_field_value(self) -> bool:
        """True if this is a field value (e.g., attribute data)."""
        return self.token_type == TokenType.VALUE and self.value_context == ValueContext.FIELD
    
    @property
    def is_schema_value(self) -> bool:
        """True if this is a schema value (e.g., company name for database ops)."""
        return self.token_type == TokenType.VALUE and self.value_context == ValueContext.SCHEMA
    
    @property
    def is_action_word(self) -> bool:
        """True if this is an ACTION word."""
        return self.is_word and self.word_type == WordType.ACTION
    
    @property
    def is_entity_word(self) -> bool:
        """True if this is an ENTITY word."""
        return self.is_word and self.word_type == WordType.ENTITY
    
    @property
    def is_field_word(self) -> bool:
        """True if this is a FIELD word."""
        return self.is_word and self.word_type == WordType.FIELD
    
    @property
    def is_schema_word(self) -> bool:
        """True if this is a SCHEMA word."""
        return self.is_word and self.word_type == WordType.SCHEMA