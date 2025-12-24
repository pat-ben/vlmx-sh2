# File: D:\Code\vlmx-sh2\src\vlmx_sh2\parser.py

"""
Minimal parser for VLMX DSL commands.

This module provides basic parsing functionality that integrates with:
- words.py for keyword recognition
- commands.py for command matching and validation
- syntax.py for automatic composition rules
- RapidFuzz for fuzzy matching and suggestions

Architecture:
1. Tokenize input text
2. Recognize keywords with fuzzy matching
3. Extract values (company names, attributes)
4. Match against registered commands
5. Validate using automatic composition rules
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process
from pydantic import BaseModel, Field, field_validator

from .commands import find_commands, Command
from .syntax import is_valid_command, get_composition_error
from .words import get_all_words, get_word, Word
from .enums import WordType, TokenType


# ==================== PARSE RESULT MODELS ====================

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
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate that confidence is between 0 and 100."""
        if not 0.0 <= v <= 100.0:
            raise ValueError(f"confidence must be between 0 and 100, got: {v}")
        return v
    
    @property
    def is_recognized_word(self) -> bool:
        """True if this token represents a recognized word."""
        return self.word is not None and self.token_type == TokenType.WORD
    
    @property
    def word_type(self) -> Optional[WordType]:
        """Get the word type if this is a recognized word."""
        return self.word.word_type if self.word else None


class ParseResult(BaseModel):
    """Complete parse result with tokens, commands, and validation."""
    
    input_text: str = Field(description="Original input text")
    tokens: List[ParsedToken] = Field(default_factory=list, description="Parsed tokens")
    recognized_words: List[Word] = Field(default_factory=list, description="Successfully recognized words")
    values: Dict[str, Any] = Field(default_factory=dict, description="Extracted values (company names, etc.)")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Extracted attribute values")
    matching_commands: List[Command] = Field(default_factory=list, description="Commands that could match")
    best_command: Optional[Command] = Field(default=None, description="Best matching command")
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
        return [word for word in self.recognized_words if word.word_type == WordType.ATTRIBUTE]
    
    @property
    def has_complete_command(self) -> bool:
        """True if we have a valid command with all required words."""
        return self.is_valid and self.best_command is not None
    
    @property
    def word_types_present(self) -> List[WordType]:
        """Get list of word types present in the recognized words."""
        return list(set(word.word_type for word in self.recognized_words))
    
    @property
    def missing_required_words(self) -> List[str]:
        """Get list of required words missing for the best command."""
        if not self.best_command:
            return []
        
        present_word_ids = {word.id for word in self.recognized_words}
        return list(self.best_command.words.required_words - present_word_ids)


# ==================== TOKENIZATION ====================

class Tokenizer:
    """Basic tokenizer for VLMX DSL input."""
    
    # Regex patterns for different token types
    ATTRIBUTE_PATTERN = re.compile(r'--(\w+)=([^"\s]+|"[^"]*")')
    WORD_PATTERN = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_-]*\b')
    VALUE_PATTERN = re.compile(r'[A-Z0-9_-]+')  # Company names, etc.
    
    @classmethod
    def tokenize(cls, text: str) -> List[ParsedToken]:
        """
        Tokenize input text into basic tokens.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of ParsedToken objects
        """
        tokens = []
        
        # First, extract attributes (--key=value)
        for match in cls.ATTRIBUTE_PATTERN.finditer(text):
            tokens.append(ParsedToken(
                text=match.group(0),
                position=match.start(),
                token_type=TokenType.FLAG,
                confidence=1.0
            ))
        
        # Remove attributes from text for word processing
        text_without_attrs = cls.ATTRIBUTE_PATTERN.sub('', text)
        
        # Extract words
        for match in cls.WORD_PATTERN.finditer(text_without_attrs):
            word_text = match.group(0).lower()
            
            tokens.append(ParsedToken(
                text=word_text,
                position=match.start(),
                token_type=TokenType.UNKNOWN,  # Will be determined later
                confidence=0.0
            ))
        
        # Sort by position
        tokens.sort(key=lambda t: t.position)
        
        return tokens


# ==================== WORD RECOGNITION ====================

class WordRecognizer:
    """Recognizes keywords using exact and fuzzy matching, leveraging Word objects."""
    
    def __init__(self, fuzzy_threshold: float = 80.0):
        """
        Initialize word recognizer.
        
        Args:
            fuzzy_threshold: Minimum confidence score for fuzzy matches (0-100)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.word_registry = get_all_words()
        self.word_list = list(self.word_registry.keys())
        
        # Build comprehensive alias mapping for faster lookup
        self.alias_to_word = {}
        self.words_by_type = {wt: [] for wt in WordType}
        
        for word_id, word in self.word_registry.items():
            # Add the word ID itself
            self.alias_to_word[word_id.lower()] = word_id
            
            # Add aliases with their original casing and lowercase
            for alias in word.aliases:
                self.alias_to_word[alias.lower()] = word_id
            
            # Add abbreviations with their original casing and lowercase
            for abbrev in word.abbreviations:
                self.alias_to_word[abbrev.lower()] = word_id
            
            # Group words by type for better command matching
            self.words_by_type[word.word_type].append(word)
    
    def get_words_by_type(self, word_type: WordType) -> List[Word]:
        """Get all words of a specific type."""
        return self.words_by_type.get(word_type, [])
    
    def recognize_word(self, token_text: str) -> Tuple[Optional[Word], float, List[str]]:
        """
        Recognize a word using exact and fuzzy matching.
        
        Args:
            token_text: Text to recognize
            
        Returns:
            Tuple of (recognized_word, confidence, suggestions)
        """
        token_lower = token_text.lower()
        
        # Try exact match first (including aliases)
        if token_lower in self.alias_to_word:
            word_id = self.alias_to_word[token_lower]
            word = get_word(word_id)
            return word, 100.0, []
        
        # Try fuzzy matching
        matches = process.extract(
            token_lower,
            self.word_list,
            scorer=fuzz.WRatio,
            limit=5
        )
        
        if matches and matches[0][1] >= self.fuzzy_threshold:
            # Best match is above threshold
            best_word_id = matches[0][0]
            confidence = matches[0][1]
            word = get_word(best_word_id)
            
            # Get suggestions from other high-scoring matches
            suggestions = [match[0] for match in matches[1:4] if match[1] >= self.fuzzy_threshold * 0.7]
            
            return word, confidence, suggestions
        
        # No good match found
        suggestions = [match[0] for match in matches[:3] if match[1] >= 50.0]
        return None, 0.0, suggestions
    
    def process_tokens(self, tokens: List[ParsedToken]) -> List[ParsedToken]:
        """
        Process tokens to recognize words and update token types.
        
        Args:
            tokens: List of tokens to process
            
        Returns:
            Updated list of tokens
        """
        for token in tokens:
            if token.token_type == TokenType.UNKNOWN:
                word, confidence, suggestions = self.recognize_word(token.text)
                
                if word:
                    token.word = word
                    token.confidence = confidence
                    token.suggestions = suggestions
                    token.token_type = TokenType.WORD
                else:
                    token.suggestions = suggestions
                    # Could be a value (company name, etc.)
                    if token.text.isupper() or '_' in token.text or '-' in token.text:
                        token.token_type = TokenType.VALUE
                    else:
                        token.token_type = TokenType.UNKNOWN
        
        return tokens


# ==================== VALUE EXTRACTION ====================

class ValueExtractor:
    """Extracts values and attributes from tokens."""
    
    @staticmethod
    def extract_attributes(tokens: List[ParsedToken]) -> Dict[str, str]:
        """
        Extract attribute key-value pairs from tokens.
        
        Args:
            tokens: List of tokens to process
            
        Returns:
            Dictionary of attribute key-value pairs
        """
        attributes = {}
        
        for token in tokens:
            if token.token_type == TokenType.FLAG:
                # Parse --key=value format
                if '=' in token.text:
                    parts = token.text[2:].split('=', 1)  # Remove -- prefix
                    if len(parts) == 2:
                        key, value = parts
                        attributes[key] = value.strip('"')
        
        return attributes
    
    @staticmethod
    def extract_values(tokens: List[ParsedToken]) -> Dict[str, Any]:
        """
        Extract values like company names from tokens.
        
        Args:
            tokens: List of tokens to process
            
        Returns:
            Dictionary of extracted values
        """
        values = {}
        
        # Look for value tokens (potential company names)
        value_tokens = [t for t in tokens if t.token_type == TokenType.VALUE]
        
        if value_tokens:
            # For now, assume first value is company name
            values['company_name'] = value_tokens[0].text
        
        return values


# ==================== MAIN PARSER ====================

class VLMXParser:
    """Main parser for VLMX DSL commands."""
    
    def __init__(self, fuzzy_threshold: float = 80.0):
        """
        Initialize the parser.
        
        Args:
            fuzzy_threshold: Minimum confidence for fuzzy word matching
        """
        self.tokenizer = Tokenizer()
        self.word_recognizer = WordRecognizer(fuzzy_threshold)
        self.value_extractor = ValueExtractor()
    
    def parse(self, input_text: str) -> ParseResult:
        """
        Parse input text into a structured result.
        
        Args:
            input_text: User input to parse
            
        Returns:
            ParseResult with all extracted information
        """
        result = ParseResult(input_text=input_text)
        
        try:
            # Step 1: Tokenize
            tokens = self.tokenizer.tokenize(input_text)
            
            # Step 2: Recognize words
            tokens = self.word_recognizer.process_tokens(tokens)
            
            # Step 3: Extract values and attributes
            result.attributes = self.value_extractor.extract_attributes(tokens)
            result.values = self.value_extractor.extract_values(tokens)
            
            # Step 4: Collect recognized words
            recognized_words = []
            for token in tokens:
                if token.word:
                    recognized_words.append(token.word)
            
            result.tokens = tokens
            result.recognized_words = recognized_words
            
            # Step 5: Validate composition
            if recognized_words:
                composition_error = get_composition_error(recognized_words)
                if composition_error:
                    result.errors.append(f"Composition error: {composition_error}")
                else:
                    result.is_valid = is_valid_command(recognized_words)
            
            # Step 6: Find and rank matching commands
            if recognized_words:
                word_ids = [w.id for w in recognized_words]
                matching_commands = find_commands(word_ids)
                result.matching_commands = matching_commands
                
                if matching_commands:
                    # Pick the best command using smart ranking
                    result.best_command = self._select_best_command(matching_commands, recognized_words)
            
            # Step 7: Generate suggestions
            result.suggestions = self._generate_suggestions(result)
            
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
        
        return result
    
    def _select_best_command(self, commands: List[Command], recognized_words: List[Word]) -> Optional[Command]:
        """
        Select the best matching command from a list of candidates.
        
        Ranking criteria:
        1. Commands with more satisfied required words
        2. Commands with fewer total required words (more specific)
        3. Commands that match the word types present
        """
        if not commands:
            return None
        
        if len(commands) == 1:
            return commands[0]
        
        word_ids = {w.id for w in recognized_words}
        word_types = {w.word_type for w in recognized_words}
        
        def score_command(cmd: Command) -> tuple:
            # Count satisfied required words (higher is better)
            satisfied_required = len(cmd.words.required_words & word_ids)
            
            # Count total required words (lower is better for specificity)
            total_required = len(cmd.words.required_words)
            
            # Check if command uses the word types we have
            cmd_word_types = set()
            for word_id in cmd.words.get_all_words():
                word_obj = get_word(word_id)
                if word_obj:
                    cmd_word_types.add(word_obj.word_type)
            
            type_match = len(word_types & cmd_word_types)
            
            # Return tuple for sorting (higher satisfied, lower total, higher type match)
            return (satisfied_required, -total_required, type_match)
        
        # Sort commands by score (descending)
        sorted_commands = sorted(commands, key=score_command, reverse=True)
        return sorted_commands[0]
    
    def _generate_suggestions(self, result: ParseResult) -> List[str]:
        """Generate helpful suggestions based on parse result and command analysis."""
        suggestions = []
        
        # Suggest corrections for unrecognized words
        for token in result.tokens:
            if token.token_type == TokenType.UNKNOWN and token.suggestions:
                suggestions.append(f"Did you mean '{token.suggestions[0]}' instead of '{token.text}'?")
        
        # Suggest missing required words for best command
        if result.best_command and result.missing_required_words:
            missing_words = result.missing_required_words
            suggestions.append(f"Missing required words: {', '.join(missing_words)}")
        
        # Suggest word type completion based on DSL patterns
        word_types_present = set(result.word_types_present)
        
        # If we have ACTION but no ENTITY, suggest adding an entity
        if WordType.ACTION in word_types_present and WordType.ENTITY not in word_types_present:
            suggestions.append("Consider adding an entity word (e.g., 'company', 'milestone')")
        
        # If we have ENTITY but no ACTION, suggest adding an action
        if WordType.ENTITY in word_types_present and WordType.ACTION not in word_types_present:
            suggestions.append("Consider adding an action word (e.g., 'create', 'delete', 'show')")
        
        # Suggest common attribute patterns
        if result.action_words and result.entity_words and not result.attributes:
            action = result.action_words[0].id
            entity = result.entity_words[0].id
            if action == 'create' and entity == 'company':
                suggestions.append("Consider adding attributes like --entity=SA --currency=EUR")
        
        return suggestions


# ==================== CONVENIENCE FUNCTIONS ====================

def parse_command(input_text: str, fuzzy_threshold: float = 80.0) -> ParseResult:
    """
    Convenience function to parse a command string.
    
    Args:
        input_text: User input to parse
        fuzzy_threshold: Minimum confidence for fuzzy matching
        
    Returns:
        ParseResult with all extracted information
    """
    parser = VLMXParser(fuzzy_threshold)
    return parser.parse(input_text)


def quick_parse(input_text: str) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Quick parse that returns simple result.
    
    Args:
        input_text: User input to parse
        
    Returns:
        Tuple of (is_valid, errors, extracted_data)
    """
    result = parse_command(input_text)
    
    extracted_data = {
        'words': [w.id for w in result.recognized_words],
        'values': result.values,
        'attributes': result.attributes,
        'best_command': result.best_command.command_id if result.best_command else None
    }
    
    return result.is_valid, result.errors, extracted_data


# ==================== DATA EXTRACTION UTILITIES ====================

def extract_company_name_from_parse_result(parse_result: ParseResult) -> str:
    """
    Extract company name from parse result.
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        Company name extracted from values or generates a default name
    """
    # Try to get company name from parsed values
    company_name = parse_result.values.get('company_name')
    
    if company_name:
        return company_name
    
    # Fallback: generate timestamp-based name for demo purposes
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Company_{timestamp}"


def extract_attributes_from_parse_result(parse_result: ParseResult) -> Dict[str, Any]:
    """
    Extract attribute values from parse result.
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        Dictionary with entity, currency, and unit attributes
    """
    from .enums import Currency, Entity, Unit
    
    attributes = {}
    
    # Extract entity from attributes (--entity=SA)
    entity_str = parse_result.attributes.get('entity', 'SA')
    try:
        attributes['entity'] = Entity(entity_str.upper())
    except ValueError:
        attributes['entity'] = Entity.SA  # Default fallback
    
    # Extract currency from attributes (--currency=EUR)  
    currency_str = parse_result.attributes.get('currency', 'EUR')
    try:
        attributes['currency'] = Currency(currency_str.upper())
    except ValueError:
        attributes['currency'] = Currency.EUR  # Default fallback
    
    # Set default unit
    attributes['unit'] = Unit.THOUSANDS
    
    return attributes