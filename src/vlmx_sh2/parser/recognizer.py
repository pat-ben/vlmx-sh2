"""
PARSING STAGE 3/8: Semantic Recognition

Performs semantic classification of structurally classified tokens.
Converts ClassifiedToken objects to RecognizedToken objects by:
- Recognizing words from registry (actions, entities, fields, schemas)
- Handling aliases (del → delete, rm → delete, etc.)
- Classifying values based on context (schema names, field values)
- Copying structural information (operators, brackets) from Classifier

Does NOT handle command/filter splitting (that's Splitter's job).
"""

from typing import Dict, List, Optional, Tuple
from ..models.parser import ClassifiedToken, RecognizedToken
from ..models.validation import ValidationContext
from ..models.words import Word, WordType, ActionWord
from ..words import get_all_words, get_word
from ..diagnostics import Validator
from vlmx_sh2.enums import TokenClass, TokenType, ValueContext, IssueStage


class Recognizer:
    """
    PARSING STAGE 3/8: Semantic Recognition
    
    Recognizes words and classifies values from classifier output.
    Converts ClassifiedToken objects to RecognizedToken objects with
    full semantic classification.
    """
    
    # Confidence scores for recognition
    _CONFIDENCE_EXACT_MATCH = 100.0
    _CONFIDENCE_VALUE = 50.0
    _CONFIDENCE_UNKNOWN = 0.0
    
    def __init__(self):
        """Initialize recognizer with registry and alias mappings."""
        self.word_registry = get_all_words()
        self.alias_to_word = self._build_alias_map()
        self.words_by_type = self._group_words_by_type()
    
    # =============================================================================
    # Initialization & Setup
    # =============================================================================
    
    def _build_alias_map(self) -> Dict[str, str]:
        """
        Build mapping from lowercase aliases to canonical word IDs.
        
        Now handles aliases from ALL word types (ACTION, SCHEMA, ENTITY, FIELD).
        
        Example: {
            "delete": "delete", "del": "delete", "rm": "delete",  # ActionWord
            "org": "organization",                                  # EntityWord
            "co": "company",                                        # SchemaWord
            "curr": "currency"                                      # FieldWord
        }
        """
        alias_map = {}
        for word_id, word in self.word_registry.items():
            # Add word ID itself
            alias_map[word_id.lower()] = word_id
            
            # Add aliases from any word type that has them
            if hasattr(word, 'aliases') and word.aliases:
                for alias in word.aliases:
                    alias_map[alias.lower()] = word_id
        
        return alias_map
    
    def _group_words_by_type(self) -> Dict[WordType, List[Word]]:
        """
        Group words by their type for quick access.
        
        Returns:
            Dictionary mapping WordType → List of Words
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
        Recognize a single token from classifier output.
        
        For TEXT tokens: attempts value classification, then word recognition.
        For OPERATOR/BRACKET tokens: passes through structural classification.
        
        Args:
            classified_token: Token from classifier
            recognized_tokens: Previous tokens for context
            current_position: Index in token array
            
        Returns:
            RecognizedToken with semantic classification
        """
        # OPERATORS and BRACKETS: Pass through structural info
        if classified_token.token_class in (TokenClass.OPERATOR, TokenClass.BRACKET):
            return self._pass_through_structural_token(classified_token)
        
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
        word, confidence = self.recognize_word(classified_token.text)
        
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
                confidence=confidence
                # No suggestions passed - will be added by validator
            )
    
    def recognize_word(self, token_text: str) -> Tuple[Optional[Word], float]:
        """
        Recognize token as word from registry, handling aliases automatically.
        
        Args:
            token_text: Text to recognize
            
        Returns:
            (word, confidence): Word object and score (100.0 if matched, 0.0 otherwise)
        """
        token_lower = token_text.lower()
        
        # Try exact match (including aliases)
        if token_lower in self.alias_to_word:
            word_id = self.alias_to_word[token_lower]
            word = get_word(word_id)
            return word, self._CONFIDENCE_EXACT_MATCH
        
        # No match
        return None, self._CONFIDENCE_UNKNOWN
    
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
        if (classified_token.was_quoted and 
            prev_token.is_word and 
            (prev_token.is_schema_word or prev_token.is_action_word)):
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
    
    def _base_fields_from_classified(self, classified_token: ClassifiedToken) -> dict:
        """
        Extract common fields from ClassifiedToken for RecognizedToken creation.
        
        Returns base dictionary with structural fields that are common to all token types.
        """
        return {
            "text": classified_token.text,
            "char_start": classified_token.char_start,
            "char_end": classified_token.char_end,
            "token_index": classified_token.token_index,
            "token_class": classified_token.token_class,
            "was_quoted": classified_token.was_quoted,
            "operator": classified_token.operator,
            "bracket": classified_token.bracket,
        }
    
    def _create_recognized_token(
        self,
        classified_token: ClassifiedToken,
        token_type: TokenType,
        word: Optional[Word] = None,
        value_context: Optional[ValueContext] = None,
        confidence: float = 0.0
    ) -> RecognizedToken:
        """
        Create RecognizedToken from ClassifiedToken with semantic classification.
        
        Combines structural fields from classifier with semantic classification.
        """
        return RecognizedToken(
            **self._base_fields_from_classified(classified_token),
            token_type=token_type,
            word=word,
            value_context=value_context,
            confidence=confidence
        )
    
    def _pass_through_structural_token(
        self,
        classified_token: ClassifiedToken
    ) -> RecognizedToken:
        """
        Pass through structural tokens (OPERATOR/BRACKET) without semantic classification.
        
        These tokens are already fully classified by the Classifier stage.
        Sets token_type to STRUCTURAL as these tokens have structural meaning only.
        """
        return RecognizedToken(
            **self._base_fields_from_classified(classified_token),
            token_type=TokenType.STRUCTURAL,  # Structural tokens have no semantic word/value meaning
            confidence=100.0
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