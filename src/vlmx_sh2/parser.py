"""
Natural language parser for VLMX DSL.

Tokenizes user input, recognizes keywords with fuzzy matching, extracts values
and attributes, matches commands, and validates syntax. Supports both traditional
flag syntax (--key=value) and simplified key=value format.
"""

from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process
from pydantic import BaseModel, Field

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
    entity_values: Dict[str, Any] = Field(default_factory=dict, description="Extracted entity values (company names, etc.)")
    attribute_values: Dict[str, str] = Field(default_factory=dict, description="Extracted attribute values")
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
                current_token.word.word_type == WordType.ATTRIBUTE and
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
            result.attribute_values = self.value_extractor.extract_attribute_values(tokens)
            result.entity_values = self.value_extractor.extract_entity_values(tokens)
            
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
        if result.action_words and result.entity_words and not result.attribute_values:
            action = result.action_words[0].id
            entity = result.entity_words[0].id
            if action == 'create' and entity == 'company':
                suggestions.append("Consider adding attributes like --entity=SA --currency=EUR")
        
        return suggestions



