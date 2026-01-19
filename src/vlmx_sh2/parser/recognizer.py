"""
PARSING STAGE 3/6: Semantic Recognition

Performs semantic classification of structurally classified tokens.
Converts ClassifiedToken objects to RecognizedToken objects by:
- Recognizing words from registry (actions, entities, fields, schemas)
- Handling aliases (del � delete, rm � delete, etc.)
- Classifying values based on context (schema names, field values)
- Providing suggestions for unrecognized tokens
- Copying structural information (operators, brackets) from Classifier

Does NOT handle command/filter splitting (that's Splitter's job).
"""

from typing import Dict, List, Optional, Tuple
from ..models.parser import ClassifiedToken, RecognizedToken
from ..models.validation import ValidationContext
from ..models.words import Word, WordType, ActionWord
from ..words import get_all_words, get_word
from ..diagnostics import Validator, SuggestionEngine
from vlmx_sh2.enums import TokenClass, TokenType, ValueContext, IssueStage


class Recognizer:
    """
    PARSING STAGE 3/6: Semantic Recognition
    
    Recognizes words and classifies values from classifier output.
    Converts ClassifiedToken objects to RecognizedToken objects with
    full semantic classification.
    """
    
    # Confidence scores for recognition
    _CONFIDENCE_EXACT_MATCH = 100.0
    _CONFIDENCE_VALUE = 50.0
    _CONFIDENCE_UNKNOWN = 0.0
    
    def __init__(self):
        """Initialize recognizer with registry and suggestion engine."""
        self.word_registry = get_all_words()
        self.suggestion_engine = SuggestionEngine()
        self.alias_to_word = self._build_alias_map()
        self.words_by_type = self._group_words_by_type()
    
    # =============================================================================
    # Initialization & Setup
    # =============================================================================
    
    def _build_alias_map(self) -> Dict[str, str]:
        """
        Build mapping from lowercase aliases to word IDs.
        
        Maps both word IDs and their aliases to the canonical word ID.
        Example: {"delete": "delete", "del": "delete", "rm": "delete"}
        
        Returns:
            Dictionary mapping lowercase alias � word ID
        """
        alias_map = {}
        for word_id, word in self.word_registry.items():
            # Add word ID itself
            alias_map[word_id.lower()] = word_id
            
            # Add aliases for ActionWords
            if isinstance(word, ActionWord):
                for alias in word.aliases:
                    alias_map[alias.lower()] = word_id
        
        return alias_map
    
    def _group_words_by_type(self) -> Dict[WordType, List[Word]]:
        """
        Group words by their type for quick access.
        
        Returns:
            Dictionary mapping WordType � List of Words
        """
        groups = {wt: [] for wt in WordType}
        for word in self.word_registry.values():
            groups[word.word_type].append(word)
        return groups
    
    # =============================================================================
    # Public API
    # =============================================================================
    
    def recognize(
        self, 
        classified_tokens: List[ClassifiedToken], 
        context: ValidationContext
    ) -> List[RecognizedToken]:
        """
        Recognize words and classify values from classified tokens.
        
        Processing:
        1. For TEXT tokens: Try word recognition, then value classification
        2. For OPERATOR/BRACKET tokens: Copy structural info as-is
        3. Provide suggestions for UNKNOWN tokens
        
        Args:
            classified_tokens: List of ClassifiedToken from classifier
            context: ValidationContext for error reporting
            
        Returns:
            List of RecognizedToken objects with semantic classification
        """
        recognized_tokens = []
        
        for i, classified_token in enumerate(classified_tokens):
            recognized_token = self._recognize_single_token(
                classified_token, 
                recognized_tokens, 
                i
            )
            recognized_tokens.append(recognized_token)
        
        # Token-level validation
        # - Validates semantic issues (unknown words, invalid values)
        # - Non-blocking by default (collect ALL errors)
        Validator.validate_tokens(IssueStage.RECOGNIZER, context, tokens=recognized_tokens)
        
        return recognized_tokens
    
    # =============================================================================
    # Core Recognition
    # =============================================================================
    
    def _recognize_single_token(
        self,
        classified_token: ClassifiedToken,
        recognized_tokens: List[RecognizedToken],
        current_position: int
    ) -> RecognizedToken:
        """
        Recognize a single classified token.
        
        Logic:
        1. OPERATOR/BRACKET tokens: Copy as-is (already classified structurally)
        2. TEXT tokens: Try value classification first, then word recognition
        3. Unknown: Provide suggestions
        
        Args:
            classified_token: Token to recognize
            recognized_tokens: Previously recognized tokens (for context)
            current_position: Position in token array
            
        Returns:
            RecognizedToken with semantic classification
        """
        # OPERATORS and BRACKETS: Just copy structural info
        if classified_token.token_class in (TokenClass.OPERATOR, TokenClass.BRACKET):
            return self._copy_structural_token(classified_token)
        
        # TEXT tokens: Perform semantic classification
        # Try VALUE classification first (context-dependent)
        value_context = self._determine_value_context(
            classified_token, 
            recognized_tokens, 
            current_position
        )
        
        if value_context:
            return self._create_recognized_token(
                classified_token,
                token_type=TokenType.VALUE,
                value_context=value_context,
                confidence=self._CONFIDENCE_VALUE
            )
        
        # Not a value, try WORD recognition
        word, confidence, suggestions = self.recognize_word(classified_token.text)
        
        if word:
            return self._create_recognized_token(
                classified_token,
                token_type=TokenType.WORD,
                word=word,
                confidence=confidence
            )
        else:
            return self._create_recognized_token(
                classified_token,
                token_type=TokenType.UNKNOWN,
                confidence=confidence,
                suggestions=suggestions
            )
    
    def recognize_word(self, token_text: str) -> Tuple[Optional[Word], float, List[str]]:
        """
        Try to recognize a token as a word from the registry.
        
        Handles aliases automatically (del � delete, rm � delete, etc.)
        
        Args:
            token_text: Text to recognize
            
        Returns:
            Tuple of (word, confidence, suggestions)
            - word: Word object if matched, None otherwise
            - confidence: 100.0 if matched, 0.0 otherwise
            - suggestions: List of similar words if not matched
        """
        token_lower = token_text.lower()
        
        # Try exact match (including aliases)
        if token_lower in self.alias_to_word:
            word_id = self.alias_to_word[token_lower]
            word = get_word(word_id)
            return word, self._CONFIDENCE_EXACT_MATCH, []
        
        # No match - provide suggestions
        suggestions = self.suggestion_engine.get_token_suggestions(token_text)
        return None, self._CONFIDENCE_UNKNOWN, suggestions
    
    # =============================================================================
    # Value Context Classification
    # =============================================================================
    
    def _determine_value_context(
        self,
        classified_token: ClassifiedToken,
        recognized_tokens: List[RecognizedToken],
        current_position: int
    ) -> Optional[ValueContext]:
        """
        Determine if a token is a value and what context it has.
        
        Rules:
        1. Schema name: Quoted token after schema/action word
           Examples: company "ACME", delete "ACME"
        2. Field value: Token after operator (quoted or not)
           Examples: currency=EUR, vision="Our vision"
        
        Args:
            classified_token: Current token being classified
            recognized_tokens: Previously recognized tokens
            current_position: Position in token array
            
        Returns:
            ValueContext if token is a value, None otherwise
        """
        if current_position == 0:
            return None
        
        prev_token = recognized_tokens[current_position - 1]
        
        # Rule 1: Schema name (quoted token after schema/action word)
        if classified_token.was_quoted and prev_token.is_word:
            if prev_token.is_schema_word or prev_token.is_action_word:
                return ValueContext.SCHEMA
        
        # Rule 2: Field value (token after operator)
        # NEW: Check if previous token's token_class is OPERATOR
        # (operators are separate tokens now, not a field on the token)
        if hasattr(prev_token, 'token_class') and prev_token.token_class == TokenClass.OPERATOR:
            return ValueContext.FIELD
        
        return None
    
    # =============================================================================
    # Token Creation Helpers
    # =============================================================================
    
    def _create_recognized_token(
        self,
        classified_token: ClassifiedToken,
        token_type: TokenType,
        word: Optional[Word] = None,
        value_context: Optional[ValueContext] = None,
        confidence: float = 0.0,
        suggestions: Optional[List[str]] = None
    ) -> RecognizedToken:
        """
        Create RecognizedToken from ClassifiedToken with semantic classification.
        
        Copies all structural information from ClassifiedToken and adds
        semantic classification fields.
        
        Args:
            classified_token: Source token with structural info
            token_type: Semantic type (WORD, VALUE, UNKNOWN)
            word: Word object if WORD type
            value_context: Context if VALUE type
            confidence: Recognition confidence (0-100)
            suggestions: Suggestions if UNKNOWN type
            
        Returns:
            RecognizedToken with complete classification
        """
        return RecognizedToken(
            # Token data
            text=classified_token.text,
            
            # Position metadata (from Token � Classifier)
            char_start=classified_token.char_start,
            char_end=classified_token.char_end,
            token_index=classified_token.token_index,
            
            # Structural classification (from Classifier)
            token_class=classified_token.token_class,
            was_quoted=classified_token.was_quoted,
            operator=classified_token.operator,
            bracket=classified_token.bracket,
            
            # Semantic classification (NEW - added by Recognizer)
            token_type=token_type,
            word=word,
            value_context=value_context,
            confidence=confidence,
            suggestions=suggestions or []
        )
    
    def _copy_structural_token(
        self,
        classified_token: ClassifiedToken
    ) -> RecognizedToken:
        """
        Copy structural token (OPERATOR/BRACKET) without semantic classification.
        
        These tokens are already fully classified by the Classifier stage.
        No semantic work needed - just copy the information.
        
        Args:
            classified_token: Operator or bracket token
            
        Returns:
            RecognizedToken with structural info only
        """
        return RecognizedToken(
            # Token data
            text=classified_token.text,
            
            # Position metadata
            char_start=classified_token.char_start,
            char_end=classified_token.char_end,
            token_index=classified_token.token_index,
            
            # Structural classification (from Classifier)
            token_class=classified_token.token_class,
            was_quoted=classified_token.was_quoted,
            operator=classified_token.operator,
            bracket=classified_token.bracket,
            
            # Semantic classification: Not applicable for structural tokens
            token_type=TokenType.UNKNOWN,  # Not WORD or VALUE
            confidence=100.0  # Fully confident in structural classification
        )
    
    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    def get_words_by_type(self, word_type: WordType) -> List[Word]:
        """
        Get all words of a specific type.
        
        Args:
            word_type: Type of words to retrieve
            
        Returns:
            List of words of the specified type
        """
        return self.words_by_type.get(word_type, [])