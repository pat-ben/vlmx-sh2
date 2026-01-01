"""
Word recognizer for VLMX DSL parser.

Handles word recognition and value classification. Converts Token objects
from the tokenizer into RecognizedToken objects with full classification.
"""

from typing import List, Optional, Tuple
from ..dsl.words import get_all_words, get_word
from ..models.words import WordType, Word
from ..models.parser import Token, RecognizedToken, TokenType, ValueContext


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
        suggestions = self._get_suggestions(token_text)
        return None, 0.0, suggestions
    
    def _get_suggestions(self, token_text: str) -> List[str]:
        """
        Get suggestions for unrecognized tokens.
        
        Args:
            token_text: The unrecognized token
            
        Returns:
            List of up to 3 suggestions
        """
        suggestions = []
        token_lower = token_text.lower()
        
        # Suggest common action words based on first letter
        if len(token_text) <= 6:
            first_char = token_lower[0] if token_lower else ''
            action_suggestions = {
                'c': ['create', 'cd'],
                's': ['show'],
                'u': ['update'],
                'd': ['delete'],
                'a': ['add']
            }
            if first_char in action_suggestions:
                suggestions.extend(action_suggestions[first_char])
        
        # Suggest common entity words if prefix matches
        if len(token_text) >= 3:
            common_entities = ['company', 'brand', 'metadata', 'offering', 'target', 'values']
            prefix = token_lower[:3]
            for entity in common_entities:
                if entity.startswith(prefix):
                    suggestions.append(entity)
        
        return suggestions[:3]  # Limit to top 3
    
    def process_tokens(self, tokens: List[Token]) -> List[RecognizedToken]:
        """
        Process tokens to recognize words and classify values.
        
        Converts List[Token] from tokenizer to List[RecognizedToken].
        
        Classification logic:
        1. Try to match against word registry → WORD
        2. If not matched, check if it's a value:
           a. Quoted token after entity word → VALUE (ENTITY context)
           b. Token after field word → VALUE (FIELD context)
           c. Token after operator → VALUE (FIELD context)
        3. Otherwise → UNKNOWN
        
        Args:
            tokens: List of Token objects from tokenizer
            
        Returns:
            List of RecognizedToken objects with classification
        """
        recognized_tokens = []
        
        for i, token in enumerate(tokens):
            # Step 1: Try to recognize as a word
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
                # Step 2: Not a word - is it a VALUE?
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
        1. Entity value: Quoted token immediately after an entity word
           Example: company "ACME" → "ACME" is ENTITY value
        
        2. Field value (pattern 1): Token immediately after a field word
           Example: vision "Our vision" → "Our vision" is FIELD value
        
        3. Field value (pattern 2): Token immediately after any token with operator
           Example: currency=EUR → "EUR" is FIELD value
        
        Args:
            token: Current token being classified
            recognized_tokens: Previously recognized tokens
            current_position: Index of current token
            
        Returns:
            ValueContext.ENTITY, ValueContext.FIELD, or None
        """
        # Need at least one previous token for context
        if current_position == 0:
            return None
        
        prev_token = recognized_tokens[current_position - 1]
        
        # Rule 1: Entity value (quoted token after entity word)
        if (prev_token.is_entity_word and token.was_quoted):
            return ValueContext.ENTITY
        
        # Rule 2: Field value (token after field word)
        if prev_token.is_field_word:
            return ValueContext.FIELD
        
        # Rule 3: Field value (token after operator)
        if prev_token.operator_after is not None:
            return ValueContext.FIELD
        
        return None