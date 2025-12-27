"""
Pydantic models for VLMX DSL parser.

Contains core models used throughout the parsing process including token types,
parsed tokens, and complete parse results. These models provide structured
data representation and validation for the natural language parser.
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from .words import WordType, Word


# ==================== TOKEN MODELS ====================

class TokenType(str, Enum):
    """Type classification for parsed tokens"""
    WORD = "word"        # Token that matches a Word in the registry
    VALUE = "value"      # Token representing a value (company name, etc.)
    UNKNOWN = "unknown"  # Token that doesn't match any known pattern


class ParsedToken(BaseModel):
    """Represents a single parsed token from the input."""
    
    text: str = Field(description="The actual text of the token")
    position: int = Field(description="Position in the original input")
    token_type: TokenType = Field(description="Type of token using TokenType enum")
    word: Optional[Word] = Field(default=None, description="Recognized word object if this is a keyword")
    confidence: float = Field(default=0.0, description="Confidence score for recognition (0-100)")
    suggestions: List[str] = Field(default_factory=list, description="Alternative suggestions for this token")
    
    class Config:
        arbitrary_types_allowed = True 
    
    @property
    def is_recognized_word(self) -> bool:
        """True if this token represents a recognized word."""
        return self.word is not None and self.token_type == TokenType.WORD
    
    @property
    def word_type(self) -> Optional[WordType]:
        """Get the word type if this is a recognized word."""
        return self.word.word_type if self.word else None


# ==================== PARSE RESULT MODEL ====================

class ParseResult(BaseModel):
    """Complete parse result with tokens and validation."""
    
    input_text: str = Field(description="Original input text")
    tokens: List[ParsedToken] = Field(default_factory=list, description="Parsed tokens")
    recognized_words: List[Word] = Field(default_factory=list, description="Successfully recognized words")
    entity_values: Dict[str, Any] = Field(default_factory=dict, description="Extracted entity values (company names, etc.)")
    attribute_values: Dict[str, str] = Field(default_factory=dict, description="Extracted attribute values")
    action_handler: Optional[Any] = Field(default=None, description="Handler function for the action")
    entity_model: Optional[Any] = Field(default=None, description="Entity model class for the target entity")
    is_valid: bool = Field(default=False, description="Whether the parse is valid")
    errors: List[str] = Field(default_factory=list, description="Parse errors")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def action_words(self) -> List[Word]:
        """Get all ACTION type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.ACTION]
    
    @property
    def entity_words(self) -> List[Word]:
        """Get all ENTITY type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.ENTITY]
    
    @property
    def modifier_words(self) -> List[Word]:
        """Get all MODIFIER type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.MODIFIER]
    
    @property
    def attribute_words(self) -> List[Word]:
        """Get all ATTRIBUTE type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.FIELD]
    
    @property
    def has_complete_action(self) -> bool:
        """True if we have a valid action and handler."""
        return self.is_valid and self.action_handler is not None
    
    @property
    def word_types_present(self) -> List[WordType]:
        """Get list of word types present in the recognized words."""
        return list(set(word.word_type for word in self.recognized_words))
    
    @property
    def has_action_and_entity(self) -> bool:
        """True if we have both an action and entity word."""
        word_types = set(self.word_types_present)
        return WordType.ACTION in word_types and WordType.ENTITY in word_types