"""
RecognizedToken model for recognizer stage output.

Contains both structural (from classifier) and semantic (from recognizer) classification.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from vlmx_sh2.enums import TokenType, ValueContext, TokenClass, Operator, Bracket
from ..words import Word, WordType


class RecognizedToken(BaseModel):
    """
    Recognized token with semantic classification.
    
    Position metadata (char_start, char_end) reference the NORMALIZED text
    (after macro expansion), not the original user input.
    
    Contains both structural (from classifier) and semantic (from recognizer) classification.
    Single model that represents all token types (WORD, VALUE, UNKNOWN).
    Fields are populated based on token_type:
    - WORD tokens: word field is set
    - VALUE tokens: value_context field is set
    - UNKNOWN tokens: suggestions may be provided
    
    Fields:
        text: Token text (quotes stripped by classifier)
        char_start: Character position where token starts in NORMALIZED text
        char_end: Character position where token ends in NORMALIZED text (exclusive)
        token_index: Position in token array (0-indexed)
        was_quoted: True if originally in quotes (from classifier)
        token_type: Semantic classification (WORD, VALUE, or UNKNOWN)
        word: Complete Word object from registry (only for WORD tokens)
        value_context: Context for VALUE tokens (SCHEMA, ENTITY, or FIELD)
        confidence: Recognition confidence score (0-100)
        suggestions: Suggestions for unrecognized tokens
    
    Examples:
        Input:      "cc ACME Corp"
        Normalized: "create company ACME Corp"
        
        # WORD token
        >>> RecognizedToken(
        ...     text="create",
        ...     char_start=0, char_end=6, token_index=0,
        ...     token_type=TokenType.WORD,
        ...     word=ActionWord(id="create", ...)
        ... )
        
        # VALUE token (schema)
        >>> RecognizedToken(
        ...     text="ACME",
        ...     char_start=15, char_end=19, token_index=2,
        ...     was_quoted=False,
        ...     token_type=TokenType.VALUE,
        ...     value_context=ValueContext.SCHEMA
        ... )
        
        # UNKNOWN token
        >>> RecognizedToken(
        ...     text="xyz123",
        ...     char_start=20, char_end=26, token_index=3,
        ...     token_type=TokenType.UNKNOWN,
        ...     suggestions=["Corp", "Inc"]
        ... )
    """
    
    # Token data
    text: str = Field(
        description="Token text (quotes stripped by classifier)"
    )
    
    # Position metadata (inherited/preserved from Token)
    char_start: int = Field(
        description="Character position where token starts in NORMALIZED text (0-indexed)"
    )
    char_end: int = Field(
        description="Character position where token ends in NORMALIZED text (exclusive)"
    )
    token_index: int = Field(
        description="Position in token array (0-indexed)"
    )
    
    # Structural classification (inherited from classifier)
    token_class: Optional[TokenClass] = Field(
        default=None,
        description="Structural classification from classifier (TEXT, OPERATOR, BRACKET)"
    )
    was_quoted: bool = Field(
        default=False,
        description="True if originally in quotes (from classifier)"
    )
    operator: Optional[Operator] = Field(
        default=None,
        description="If OPERATOR class, which operator it is"
    )
    bracket: Optional[Bracket] = Field(
        default=None,
        description="If BRACKET class, which bracket it is"
    )
    
    # Semantic classification (added by recognizer)
    token_type: TokenType = Field(
        default=TokenType.UNKNOWN,
        description="Semantic classification: WORD, VALUE, or UNKNOWN"
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
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=False
    )
    
    @property
    def char_length(self) -> int:
        """Return the character length of the token."""
        return self.char_end - self.char_start
    
    @property
    def position(self) -> int:
        """Alias for char_start (backward compatibility)."""
        return self.char_start
    
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
    def is_schema_name(self) -> bool:
        """True if this is a schema name (e.g., company name for database ops)."""
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