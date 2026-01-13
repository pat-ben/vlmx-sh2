"""
Word recognizer for parser.

Handles word recognition and value classification. Converts Token objects
from the tokenizer into RecognizedToken objects with full classification.
"""

from typing import Dict, List, Optional, Tuple
from ..words import get_all_words, get_word
from ..models.words import WordType, Word, ActionWord
from ..models.parser import Token, RecognizedToken, TokenType, ValueContext
from ..support.suggestions import SuggestionEngine


class WordRecognizer:
    """
    Recognizes words and classifies values from tokenizer output.
    
    Converts List[Token] to List[RecognizedToken] by:
    1. Matching tokens against word registry (WORD tokens)
    2. Classifying non-matching tokens as values (VALUE tokens)
    3. Providing suggestions for unrecognized tokens (UNKNOWN tokens)
    """
    
    # this may be used for future enhancements (fuzzy matching and suggestions)
    _CONFIDENCE_EXACT_MATCH = 100.0
    _CONFIDENCE_VALUE = 50.0
    _CONFIDENCE_UNKNOWN = 0.0
    
    def __init__(self):
        """Initialize word recognizer with registry and alias mappings."""
        self.word_registry = get_all_words()
        self.suggestion_engine = SuggestionEngine()
        self.alias_to_word = self._build_alias_map()
        self.words_by_type = self._group_words_by_type()
    
    def _build_alias_map(self) -> Dict[str, str]:
        """Build mapping from lowercase aliases to word IDs."""
        alias_map = {}
        for word_id, word in self.word_registry.items():
            alias_map[word_id.lower()] = word_id
            
            if isinstance(word, ActionWord):
                for alias in word.aliases:
                    alias_map[alias.lower()] = word_id
        
        return alias_map
    
    def _group_words_by_type(self) -> Dict[WordType, List[Word]]:
        """Group words by their type for quick access."""
        groups = {wt: [] for wt in WordType}
        for word in self.word_registry.values():
            groups[word.word_type].append(word)
        return groups
    
    @staticmethod
    def _create_recognized_token(
        token: Token,
        token_type: TokenType,
        word: Optional[Word] = None,
        value_context: Optional[ValueContext] = None,
        confidence: float = 0.0,
        suggestions: Optional[List[str]] = None
    ) -> RecognizedToken:
        """Create RecognizedToken from Token with recognition data."""
        return RecognizedToken(
            text=token.text,
            position=token.position,
            was_quoted=token.was_quoted,
            operator_after=token.operator_after,
            token_type=token_type,
            word=word,
            value_context=value_context,
            confidence=confidence,
            suggestions=suggestions or []
        )
    
    def get_words_by_type(self, word_type: WordType) -> List[Word]:
        """Get all words of a specific type."""
        return self.words_by_type.get(word_type, [])
    
    def recognize_word(self, token_text: str) -> Tuple[Optional[Word], float, List[str]]:
        """
        Try to recognize a token as a word from the registry.
        
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
    
    
    def _classify_token(
        self, 
        token: Token, 
        recognized_tokens: List[RecognizedToken], 
        position: int
    ) -> RecognizedToken:
        """
        Classify a single token into WORD, VALUE, or UNKNOWN.

        Returns:
            RecognizedToken with appropriate classification
        """
        value_context = self._determine_value_context(token, recognized_tokens, position)
        
        if value_context:
            return self._create_recognized_token(
                token, TokenType.VALUE, value_context=value_context, 
                confidence=self._CONFIDENCE_VALUE
            )
        else:
            word, confidence, suggestions = self.recognize_word(token.text)
            if word:
                return self._create_recognized_token(
                    token, TokenType.WORD, word=word, confidence=confidence
                )
            else:
                return self._create_recognized_token(
                    token, TokenType.UNKNOWN, confidence=confidence, suggestions=suggestions
                )
    
    def process_tokens(self, tokens: List[Token]) -> List[RecognizedToken]:
        """
        Process tokens to recognize words and classify values.
        
        Classification logic:
        1. Try to match against word registry → WORD
        2. If not matched, check if it's a value:
           a. Quoted token after schema/action word → VALUE (SCHEMA context)
           b. Token after operator → VALUE (FIELD context)
        3. Otherwise → UNKNOWN
        """
        recognized_tokens = []
        
        for i, token in enumerate(tokens):
            recognized_token = self._classify_token(token, recognized_tokens, i)
            recognized_tokens.append(recognized_token)
        
        return recognized_tokens
    
    def _determine_value_context(
        self,
        token: Token,
        recognized_tokens: List[RecognizedToken],
        current_position: int
    ) -> Optional[ValueContext]:
        """
        Determine if a token is a value and what context it has.
        
        Rules:
        1. Schema value: Quoted token after schema/action word
           Examples: company "ACME", delete "ACME"
        2. Field value: Token after operator (quoted or not)
           Examples: currency=EUR, vision="Our vision"
        """
        if current_position == 0:
            return None
        
        prev_token = recognized_tokens[current_position - 1]
        
        # Schema value: Quoted token after schema or action word
        if token.was_quoted and (prev_token.is_schema_word or prev_token.is_action_word):
            return ValueContext.SCHEMA
        
        # Field value: Token after operator
        if prev_token.operator_after is not None:
            return ValueContext.FIELD
        
        return None