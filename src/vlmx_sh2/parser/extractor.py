"""
Value extractor for VLMX DSL parser.

Handles extraction of entity values (like company names) and attribute values
from parsed token streams. Provides pattern matching for entity names and
intelligent attribute-value pairing.
"""

from typing import Any, Dict, List
from ..models.parser import ParsedToken, TokenType
from ..models.words import WordType


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