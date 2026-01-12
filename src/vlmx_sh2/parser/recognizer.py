"""
Word recognizer for parser.

Handles word recognition and value classification. Converts Token objects
from the tokenizer into RecognizedToken objects with full classification.
"""

from typing import List, Optional, Tuple
from ..words import get_all_words, get_word
from ..models.words import WordType, Word
from ..models.parser import Token, RecognizedToken, TokenType, ValueContext
from .suggestions import SuggestionEngine


class WordRecognizer:
    """
    Recognizes words and classifies values from tokenizer output.
    
    Converts List[Token] to List[RecognizedToken] by:
    1. Matching tokens against word registry (WORD tokens)
    2. Classifying non-matching tokens as values (VALUE tokens)
    3. Providing suggestions for unrecognized tokens (UNKNOWN tokens)
    """
    
    def __init__(self):
        """Initialize word recognizer with registry and alias mappings."""
        self.word_registry = get_all_words()
        self.suggestion_engine = SuggestionEngine()
        
        # Build alias mapping for fast lookup
        self.alias_to_word = {}
        self.words_by_type = {wt: [] for wt in WordType}
        
        for word_id, word in self.word_registry.items():
            # Add the word ID itself
            self.alias_to_word[word_id.lower()] = word_id
            
            # Add all aliases (only ActionWord has aliases)
            from ..models.words import ActionWord
            if isinstance(word, ActionWord):
                for alias in word.aliases:
                    self.alias_to_word[alias.lower()] = word_id
            
            # Group words by type
            self.words_by_type[word.word_type].append(word)
    
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
            return word, 100.0, []
        
        # No match - provide suggestions
        suggestions = self.suggestion_engine.get_token_suggestions(token_text)
        return None, 0.0, suggestions
    
    
    def process_tokens(self, tokens: List[Token]) -> List[RecognizedToken]:
        """
        Process tokens to recognize words and classify values.
        
        Converts List[Token] from tokenizer to List[RecognizedToken].
        
        Classification logic:
        1. Try to match against word registry → WORD
        2. If not matched, check if it's a value:
           a. Quoted token after schema word → VALUE (SCHEMA context)
           b. Quoted token after action word → VALUE (SCHEMA context)
           c. Token after operator → VALUE (FIELD context, with or without quotes)
        3. Otherwise → UNKNOWN
        
        Args:
            tokens: List of Token objects from tokenizer
            
        Returns:
            List of RecognizedToken objects with classification
        """
        recognized_tokens = []
        
        for i, token in enumerate(tokens):
            # Step 1: Check if this token should be a VALUE (higher priority than word matching)
            value_context = self._determine_value_context(token, recognized_tokens, i)
            
            if value_context:
                # It's a VALUE!
                recognized_token = RecognizedToken(
                    # Copy Token fields
                    text=token.text,
                    position=token.position,
                    was_quoted=token.was_quoted,
                    operator_after=token.operator_after,
                    
                    # Set recognition fields
                    token_type=TokenType.VALUE,
                    word=None,
                    value_context=value_context,
                    confidence=50.0,  # Medium confidence for values
                    suggestions=[]
                )
            else:
                # Step 2: Try to recognize as a word
                word, confidence, suggestions = self.recognize_word(token.text)
                
                if word:
                    # It's a WORD!
                    recognized_token = RecognizedToken(
                        # Copy Token fields
                        text=token.text,
                        position=token.position,
                        was_quoted=token.was_quoted,
                        operator_after=token.operator_after,
                        
                        # Set recognition fields
                        token_type=TokenType.WORD,
                        word=word,
                        value_context=None,
                        confidence=confidence,
                        suggestions=[]
                    )
                else:
                    # It's UNKNOWN
                    recognized_token = RecognizedToken(
                        # Copy Token fields
                        text=token.text,
                        position=token.position,
                        was_quoted=token.was_quoted,
                        operator_after=token.operator_after,
                        
                        # Set recognition fields
                        token_type=TokenType.UNKNOWN,
                        word=None,
                        value_context=None,
                        confidence=0.0,
                        suggestions=suggestions
                    )
            
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
        1. Schema value (pattern 1): Quoted token immediately after a schema word
           Example: company "ACME" → "ACME" is SCHEMA value
        
        2. Schema value (pattern 2): Quoted token immediately after an action word
           Example: delete "ACME" → "ACME" is SCHEMA value (schema word implied)
        
        3. Field value: Token immediately after any token with operator
           Example: currency=EUR → "EUR" is FIELD value (with or without quotes)
           Example: vision="Our vision" → "Our vision" is FIELD value
        
        Note: EntityWords (organization, metadata, etc.) don't have direct quoted values.
        They're used for table operations: show organization, list news, etc.
        Field words don't take direct values - values only come after operators.
        
        Args:
            token: Current token being classified
            recognized_tokens: Previously recognized tokens
            current_position: Index of current token
            
        Returns:
            ValueContext.SCHEMA, ValueContext.FIELD, or None
        """
        # Need at least one previous token for context
        if current_position == 0:
            return None
        
        prev_token = recognized_tokens[current_position - 1]
        
        # Rule 1: Schema value (quoted token after schema word)
        if (prev_token.is_schema_word and token.was_quoted):
            return ValueContext.SCHEMA
        
        # Rule 2: Schema value (quoted token after action word)
        if (prev_token.is_action_word and token.was_quoted):
            return ValueContext.SCHEMA
        
        # Rule 3: Field value (token after operator, with or without quotes)
        if prev_token.operator_after is not None:
            return ValueContext.FIELD
        
        return None