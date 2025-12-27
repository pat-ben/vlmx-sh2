"""
Natural language parser for VLMX DSL.

Tokenizes user input, recognizes keywords with fuzzy matching, extracts values
and attributes, matches commands, and validates syntax. Supports both traditional
flag syntax (--key=value) and simplified key=value format.
"""

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .words import get_all_words, get_word, expand_shortcuts
from ..models.words import WordType, Word, ActionWord, EntityWord
from enum import Enum


# ==================== PARSE RESULT MODELS ====================

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


# ==================== TOKENIZATION ====================

class Tokenizer:
    """Simple tokenizer for VLMX DSL input."""
    
    @classmethod
    def tokenize(cls, text: str) -> List[ParsedToken]:
        """
        Tokenize input text into basic tokens.
        
        Enhanced approach supporting:
        1. Attributes in key=value format (entity=SA, currency=EUR)
        2. Traditional command words and values
        3. Backward compatibility with --key=value format
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of ParsedToken objects
        """
        tokens = []
        position = 0
        
        # Split on whitespace and process each token
        for raw_token in text.split():
            raw_token = raw_token.strip()
            if not raw_token:
                continue
            
            # Remove -- prefix if present (for backward compatibility)
            clean_token = raw_token
            if raw_token.startswith('--'):
                clean_token = raw_token[2:]
            
            # Check if this token contains an operator (for attributes)
            if cls._contains_operator(clean_token):
                # Parse attribute: key=value, key>value, etc.
                key, operator, value = cls._parse_attribute_token(clean_token)
                
                # Add the key as a token (this will be recognized as an attribute word)
                if key:
                    tokens.append(ParsedToken(
                        text=key,
                        position=position,
                        token_type=TokenType.UNKNOWN,
                        confidence=0.0
                    ))
                
                # Add the value as a separate token
                if value:
                    tokens.append(ParsedToken(
                        text=value,
                        position=position + len(key) + len(operator),
                        token_type=TokenType.VALUE,
                        confidence=0.0
                    ))
            else:
                # Regular word token (action/modifier/entity/attribute)
                tokens.append(ParsedToken(
                    text=clean_token,
                    position=position,
                    token_type=TokenType.UNKNOWN,
                    confidence=0.0
                ))
            
            position += len(raw_token) + 1  # +1 for whitespace
        
        return tokens
    
    @classmethod
    def _contains_operator(cls, token: str) -> bool:
        """Check if token contains an attribute operator."""
        operators = ['=', '>', '<', '>=', '<=', '!=']
        return any(op in token for op in operators)
    
    @classmethod
    def _parse_attribute_token(cls, token: str) -> Tuple[str, str, str]:
        """Parse attribute token into key, operator, value."""
        operators = ['>=', '<=', '!=', '=', '>', '<']  # Order matters for multi-char operators
        
        for operator in operators:
            if operator in token:
                parts = token.split(operator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip('"\'')  # Remove quotes
                    return key, operator, value
        
        return token, '', ''


# ==================== WORD RECOGNITION ====================

class WordRecognizer:
    """Recognizes keywords using exact matching and aliases."""
    
    def __init__(self):
        """Initialize word recognizer."""
        self.word_registry = get_all_words()
        
        # Build comprehensive alias mapping for faster lookup
        self.alias_to_word = {}
        self.words_by_type = {wt: [] for wt in WordType}
        
        for word_id, word in self.word_registry.items():
            # Add the word ID itself
            self.alias_to_word[word_id.lower()] = word_id
            
            # Add aliases with their original casing and lowercase
            for alias in word.aliases:
                self.alias_to_word[alias.lower()] = word_id
            
            # Group words by type for better command matching
            self.words_by_type[word.word_type].append(word)
    
    def get_words_by_type(self, word_type: WordType) -> List[Word]:
        """Get all words of a specific type."""
        return self.words_by_type.get(word_type, [])
    
    def recognize_word(self, token_text: str) -> Tuple[Optional[Word], float, List[str]]:
        """
        Recognize a word using exact matching and aliases.
        
        Args:
            token_text: Text to recognize
            
        Returns:
            Tuple of (recognized_word, confidence, suggestions)
        """
        token_lower = token_text.lower()
        
        # Try exact match (including aliases)
        if token_lower in self.alias_to_word:
            word_id = self.alias_to_word[token_lower]
            word = get_word(word_id)
            return word, 100.0, []
        
        # No match found - provide basic suggestions based on similar word types
        suggestions = self._get_basic_suggestions(token_text)
        return None, 0.0, suggestions
    
    def _get_basic_suggestions(self, token_text: str) -> List[str]:
        """Get basic suggestions for unrecognized tokens."""
        suggestions = []
        
        # Suggest common action words
        if len(token_text) <= 6 and token_text.lower().startswith(('c', 's', 'u', 'd', 'a')):
            if token_text.lower().startswith('c'):
                suggestions.extend(['create', 'cd'])
            elif token_text.lower().startswith('s'):
                suggestions.extend(['show'])
            elif token_text.lower().startswith('u'):
                suggestions.extend(['update'])
            elif token_text.lower().startswith('d'):
                suggestions.extend(['delete'])
            elif token_text.lower().startswith('a'):
                suggestions.extend(['add'])
        
        # Suggest common entity words
        if len(token_text) >= 3:
            common_entities = ['company', 'brand', 'metadata', 'offering', 'target', 'values']
            for entity in common_entities:
                if entity.startswith(token_text.lower()[:3]):
                    suggestions.append(entity)
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def process_tokens(self, tokens: List[ParsedToken]) -> List[ParsedToken]:
        """
        Process tokens to recognize words and update token types.
        
        Classifies tokens as:
        - WORD: Matches a word in the registry
        - VALUE: Looks like a company name or attribute value
        - UNKNOWN: Doesn't match any known pattern
        
        Args:
            tokens: List of tokens to process
            
        Returns:
            Updated list of tokens
        """
        for token in tokens:
            if token.token_type == TokenType.UNKNOWN:
                # First try to recognize as a word from registry
                word, confidence, suggestions = self.recognize_word(token.text)
                
                if word:
                    token.word = word
                    token.confidence = confidence
                    token.suggestions = suggestions
                    token.token_type = TokenType.WORD
                else:
                    token.suggestions = suggestions
                    # Classify as VALUE if it looks like a company name or attribute value
                    if self._is_value_token(token.text):
                        token.token_type = TokenType.VALUE
                    else:
                        token.token_type = TokenType.UNKNOWN
        
        return tokens
    
    def _is_value_token(self, text: str) -> bool:
        """
        Determine if a token should be classified as a VALUE.
        
        Values are typically:
        - Company names (uppercase, with hyphens/underscores)
        - Attribute values (SA, EUR, etc.)
        - Mixed case identifiers
        
        Args:
            text: Token text to classify
            
        Returns:
            True if the token should be classified as VALUE
        """
        # Company names and entity values are often uppercase
        if text.isupper():
            return True
            
        # Contains hyphens or underscores (common in company names)
        if '_' in text or '-' in text:
            return True
            
        # Mixed case (could be a name)
        if text != text.lower() and text != text.upper():
            return True
            
        # Known attribute values
        known_values = {'SA', 'SARL', 'SAS', 'LLC', 'INC', 'LTD', 'GMBH', 
                       'EUR', 'USD', 'GBP', 'CHF', 'CAD',
                       'THOUSANDS', 'MILLIONS'}
        if text.upper() in known_values:
            return True
            
        return False


# ==================== VALUE EXTRACTION ====================

class ValueExtractor:
    """Extracts entity values and attribute values from tokens."""
    
    @staticmethod
    def extract_attribute_values(tokens: List[ParsedToken]) -> Dict[str, str]:
        """
        Extract attribute key-value pairs from tokens.
        
        Attributes are identified by:
        1. Consecutive tokens where an attribute word is followed by a value
        2. Key=value pattern already parsed during tokenization
        
        Args:
            tokens: List of tokens to process
            
        Returns:
            Dictionary of attribute key-value pairs
        """
        attributes = {}
        
        # Look for consecutive tokens where an attribute word is followed by a value
        for i in range(len(tokens) - 1):
            current_token = tokens[i]
            next_token = tokens[i + 1]
            
            # Check if current token is an attribute word and next is a value
            if (current_token.token_type == TokenType.WORD and 
                current_token.word and 
                current_token.word.word_type == WordType.FIELD and
                next_token.token_type == TokenType.VALUE):
                attributes[current_token.text] = next_token.text
            
            # Also handle cases where the token was not recognized as a word but is followed by a value
            # This catches attribute keys that might not be in our registry
            elif (current_token.token_type == TokenType.UNKNOWN and 
                  next_token.token_type == TokenType.VALUE):
                attributes[current_token.text] = next_token.text
        
        return attributes
    
    @staticmethod
    def extract_entity_values(tokens: List[ParsedToken]) -> Dict[str, Any]:
        """
        Extract entity values (like company names) from tokens.
        
        Entity values are identified when:
        1. They follow an entity word (like 'company')
        2. They are created/referenced in the context
        3. They exist in the database (.ORG level)
        
        Args:
            tokens: List of tokens to process
            
        Returns:
            Dictionary of entity values
        """
        entity_values = {}
        
        # Look for entity values that follow entity words
        for i in range(len(tokens) - 1):
            current_token = tokens[i]
            next_token = tokens[i + 1]
            
            # If current token is an entity word and next is a value
            if (current_token.token_type == TokenType.WORD and 
                current_token.word and 
                current_token.word.word_type == WordType.ENTITY and
                next_token.token_type == TokenType.VALUE):
                
                entity_type = current_token.word.id
                entity_value = next_token.text
                
                # Map entity types to standardized keys
                if entity_type == 'company':
                    entity_values['company_name'] = entity_value
                elif entity_type == 'milestone':
                    entity_values['milestone_name'] = entity_value
                else:
                    # Generic entity value
                    entity_values[f'{entity_type}_name'] = entity_value
        
        # If no entity values found through entity words, look for standalone values
        # that could be entity names (for cases where entity word is implied)
        if not entity_values:
            standalone_values = [t for t in tokens if t.token_type == TokenType.VALUE]
            entity_candidates = []
            
            for token in standalone_values:
                # Entity names typically have specific patterns
                if ValueExtractor._looks_like_entity_name(token.text):
                    entity_candidates.append(token.text)
            
            # Use the first candidate as company name (most common entity)
            if entity_candidates:
                entity_values['company_name'] = entity_candidates[0]
        
        return entity_values
    
    @staticmethod
    def _looks_like_entity_name(text: str) -> bool:
        """
        Determine if a value looks like an entity name.
        
        Entity names typically:
        - Contain underscores or hyphens (MY_COMPANY, ACME-CORP)
        - Are mixed case (MyCompany)
        - Are uppercase abbreviations (ACME)
        - But NOT short attribute values (EUR, SA, etc.)
        
        Args:
            text: Text to evaluate
            
        Returns:
            True if text looks like an entity name
        """
        # Skip short attribute values
        if len(text) <= 3 and text.isupper():
            known_attribute_values = {'SA', 'LLC', 'INC', 'LTD', 'EUR', 'USD', 'GBP', 'CHF', 'CAD'}
            if text in known_attribute_values:
                return False
        
        # Entity name patterns
        has_separators = '_' in text or '-' in text
        is_mixed_case = text != text.lower() and text != text.upper()
        is_long_upper = len(text) > 3 and text.isupper()
        
        return has_separators or is_mixed_case or is_long_upper


# ==================== MAIN PARSER ====================

class VLMXParser:
    """Main parser for VLMX DSL commands."""
    
    def __init__(self):
        """Initialize the parser."""
        self.tokenizer = Tokenizer()
        self.word_recognizer = WordRecognizer()
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
            # Step 1: Expand shortcuts
            expanded_input = expand_shortcuts(input_text)
            
            # Step 2: Tokenize
            tokens = self.tokenizer.tokenize(expanded_input)
            
            # Step 3: Recognize words
            tokens = self.word_recognizer.process_tokens(tokens)
            
            # Step 4: Extract values and attributes
            result.attribute_values = self.value_extractor.extract_attribute_values(tokens)
            result.entity_values = self.value_extractor.extract_entity_values(tokens)
            
            # Step 5: Collect recognized words
            recognized_words = []
            for token in tokens:
                if token.word:
                    recognized_words.append(token.word)
            
            result.tokens = tokens
            result.recognized_words = recognized_words
            
            # Step 6: Extract action handler and entity model
            if recognized_words:
                action_words = [w for w in recognized_words if isinstance(w, ActionWord)]
                entity_words = [w for w in recognized_words if isinstance(w, EntityWord)]
                
                if action_words:
                    # Get the handler from the action word
                    action_word = action_words[0]  # Take the first action word
                    result.action_handler = action_word.handler
                    
                if entity_words:
                    # Get the entity model from the entity word
                    entity_word = entity_words[0]  # Take the first entity word
                    result.entity_model = entity_word.entity_model
                
                # Validate that we have the minimum requirements
                if action_words:
                    result.is_valid = True
            
            # Step 8: Generate suggestions
            result.suggestions = self._generate_suggestions(result)
            
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
        
        return result
    
    def _validate_handler_requirements(self, result: ParseResult) -> bool:
        """
        Validate that the parse result has the minimum requirements for handler execution.
        
        Requirements:
        1. Must have an action word with handler
        2. For most actions, must have an entity word (unless action doesn't require entity)
        """
        if not result.action_handler:
            result.errors.append("No action handler found")
            return False
        
        # Check if action requires entity
        action_words = result.action_words
        if action_words and action_words[0].requires_entity:
            if not result.entity_words:
                result.errors.append("Action requires an entity word")
                return False
        
        return True
    
    def _generate_suggestions(self, result: ParseResult) -> List[str]:
        """Generate helpful suggestions based on parse result and command analysis."""
        suggestions = []
        
        # Suggest corrections for unrecognized words
        for token in result.tokens:
            if token.token_type == TokenType.UNKNOWN and token.suggestions:
                suggestions.append(f"Did you mean '{token.suggestions[0]}' instead of '{token.text}'?")
        
        # Suggest word type completion based on DSL patterns
        word_types_present = set(result.word_types_present)
        
        # If we have ACTION but no ENTITY, suggest adding an entity
        if WordType.ACTION in word_types_present and WordType.ENTITY not in word_types_present:
            action_words = result.action_words
            if action_words and action_words[0].requires_entity:
                suggestions.append("Consider adding an entity word (e.g., 'company', 'brand', 'metadata')")
        
        # If we have ENTITY but no ACTION, suggest adding an action
        if WordType.ENTITY in word_types_present and WordType.ACTION not in word_types_present:
            suggestions.append("Consider adding an action word (e.g., 'create', 'add', 'update', 'show', 'delete')")
        
        # Suggest common attribute patterns
        if result.action_words and result.entity_words and not result.attribute_values:
            action = result.action_words[0].id
            entity = result.entity_words[0].id
            if action == 'create' and entity == 'company':
                suggestions.append("Consider adding attributes like entity=SA currency=EUR")
            elif action in ['add', 'update'] and entity in ['brand', 'metadata', 'offering']:
                suggestions.append("Consider adding attributes like name=value or key=value")
        
        return suggestions

    async def execute_parsed_command(self, parse_result: ParseResult, context) -> Any:
        """
        Execute a parsed command by calling the action handler directly.
        
        Args:
            parse_result: The result from parsing user input
            context: Execution context
            
        Returns:
            Result from handler execution
        """
        if not parse_result.is_valid:
            raise ValueError(f"Cannot execute invalid parse result: {parse_result.errors}")
        
        if not parse_result.action_handler:
            raise ValueError("No action handler available for execution")
        
        # Validate handler requirements
        if not self._validate_handler_requirements(parse_result):
            raise ValueError(f"Handler requirements not met: {parse_result.errors}")
        
        # Call the handler with the parsed data
        # Handler signature: handler(entity_model, entity_value, attributes, context, attribute_words)
        entity_value = None
        if parse_result.entity_values:
            # Get the first entity value
            entity_value = next(iter(parse_result.entity_values.values()))
        
        # For delete operations, we need to pass the list of attribute words to delete
        attribute_words_to_process = [w.id for w in parse_result.attribute_words]
        
        try:
            return await parse_result.action_handler(
                entity_model=parse_result.entity_model,
                entity_value=entity_value,
                attributes=parse_result.attribute_values,
                context=context,
                attribute_words=attribute_words_to_process
            )
        except Exception as e:
            raise RuntimeError(f"Handler execution failed: {str(e)}")



