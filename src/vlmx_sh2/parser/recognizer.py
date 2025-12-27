"""
Word recognizer for VLMX DSL parser.

Handles word recognition using exact matching and aliases, providing suggestions
for unrecognized tokens and processing token streams to classify them as
words, values, or unknown tokens.
"""

from typing import List, Optional, Tuple
from ..dsl.words import get_all_words, get_word
from ..models.words import WordType, Word
from ..models.parser import ParsedToken, TokenType


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