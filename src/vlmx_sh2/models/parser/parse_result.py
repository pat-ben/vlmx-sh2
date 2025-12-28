"""
Parse result model for complete parsing output.

Contains the final result of the parsing pipeline with tokens, words, and values.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .recognized_token import RecognizedToken
from ..words import WordType, Word


class ParseResult(BaseModel):
    """Complete parse result with tokens and validation."""
    
    input_text: str = Field(description="Original input text")
    tokens: List[RecognizedToken] = Field(default_factory=list, description="Recognized tokens with classification")
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