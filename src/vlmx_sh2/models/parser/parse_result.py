"""
Parse result model for complete parsing output.

Contains the final result of the parsing pipeline with tokens and structured command.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .recognized_token import RecognizedToken
from .parsed_command import ParsedCommand
from ..words import WordType, Word


class ParseResult(BaseModel):
    """
    Complete parse result - clean, no redundancy.
    
    Contains only essential data from parsing. All command-specific data
    (action, entity, field_values, etc.) is accessed through the command object.
    
    Fields:
        input_text: Original user input
        tokens: All recognized tokens from parsing
        command: Structured command object (None if parse failed)
        is_valid: Whether parsing succeeded
        errors: List of error messages
        suggestions: Helpful suggestions for user
    """
    
    # Core parsing data
    input_text: str = Field(
        description="Original user input text"
    )
    
    tokens: List[RecognizedToken] = Field(
        default_factory=list,
        description="All recognized tokens from parsing (command tokens for backward compatibility)"
    )
    
    # New separate token lists
    command_tokens: List[RecognizedToken] = Field(
        default_factory=list,
        description="Recognized tokens from command parsing (outside [ ])"
    )
    
    filter_tokens: List[RecognizedToken] = Field(
        default_factory=list,
        description="Recognized tokens from filter parsing (inside [ ])"
    )
    
    # Structured command (single source of truth)
    command: Optional[ParsedCommand] = Field(
        default=None,
        description="Structured command object (None if parsing failed)"
    )
    
    # Validation and feedback
    is_valid: bool = Field(
        default=False,
        description="True if parsing succeeded and command is ready for execution"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages from parsing"
    )
    
    suggestions: List[str] = Field(
        default_factory=list,
        description="Helpful suggestions for fixing parse errors"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    # ==================== CONVENIENCE PROPERTIES ====================
    # These provide easy access to command data without direct field access
    
    @property
    def recognized_words(self) -> List[Word]:
        """Get all successfully recognized words from tokens."""
        return [t.word for t in self.tokens if t.word]
    
    @property
    def action_words(self) -> List[Word]:
        """Get all ACTION type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.ACTION]
    
    @property
    def entity_words(self) -> List[Word]:
        """Get all ENTITY type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.ENTITY]
    
    @property
    def field_words(self) -> List[Word]:
        """Get all FIELD type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.FIELD]
    
    @property
    def schema_words(self) -> List[Word]:
        """Get all SCHEMA type words from recognized words."""
        return [word for word in self.recognized_words if word.word_type == WordType.SCHEMA]
    
    @property
    def modifier_words(self) -> List[Word]:
        """Get all MODIFIER type words from recognized words (currently unused)."""
        # Note: MODIFIER word type doesn't exist yet in WordType enum
        return []
    
    # Command-related properties (for backward compatibility)
    
    @property
    def action_handler(self):
        """Get handler function from command."""
        return self.command.action_handler if self.command else None
    
    @property
    def entity_model(self):
        """Get entity model class from command."""
        return self.command.entity_model if self.command else None
    
    @property
    def attributes(self):
        """Deprecated: Get field_values dictionary from command."""
        return self.command.field_values if self.command else {}
    
    
    @property
    def entity_name(self) -> Optional[str]:
        """Get entity name from command."""
        return self.command.entity_name if self.command else None
    
    @property
    def has_complete_action(self) -> bool:
        """True if we have a valid command with action handler."""
        return self.is_valid and self.command is not None and self.command.action_handler is not None
    
    @property
    def word_types_present(self) -> List[WordType]:
        """Get list of word types present in recognized words."""
        return list(set(word.word_type for word in self.recognized_words))
    
    @property
    def has_action_and_entity(self) -> bool:
        """True if we have both an action and entity word."""
        word_types = set(self.word_types_present)
        return WordType.ACTION in word_types and WordType.ENTITY in word_types
    
