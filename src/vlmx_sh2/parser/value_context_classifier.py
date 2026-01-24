"""
Value Context Classifier

Handles classification of tokens as values with their appropriate context.
Extracted from Recognizer to improve code organization and testability.
"""

from typing import List, Optional
from ..models.parser import ClassifiedToken, RecognizedToken
from vlmx_sh2.enums import ValueContext, TokenClass


class ValueContextClassifier:
    """
    Determines if a token should be classified as a value and what context it has.
    
    Handles the logic for distinguishing between different value types:
    - Schema name values (quoted tokens after schema/action words)
    - Field values (tokens after operators)
    """
    
    @classmethod
    def determine_value_context(
        cls,
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
           
        Examples of token sequences:
            Input: "currency=EUR"
            Tokens: ["currency", "=", "EUR"]
            Classifications:
                - "currency": WORD (FieldWord)
                - "=": STRUCTURAL (OPERATOR)
                - "EUR": VALUE (FIELD context) ← detected by this rule
        
        Args:
            classified_token: Current token being classified
            recognized_tokens: Previously recognized tokens
            current_position: Position in token array
            
        Returns:
            ValueContext if token is a value, None otherwise
        """
        # Guard clause: First token cannot be a value
        if current_position == 0:
            return None
        
        prev_token = recognized_tokens[current_position - 1]
        
        # Rule 1: Schema name detection
        # Must be quoted and follow a schema or action word
        if cls._is_schema_name_value(classified_token, prev_token):
            return ValueContext.SCHEMA
        
        # Rule 2: Field value detection  
        # Any token following an operator
        if cls._is_field_value(prev_token):
            return ValueContext.FIELD
        
        return None
    
    @classmethod
    def _is_schema_name_value(cls, token: ClassifiedToken, prev_token: RecognizedToken) -> bool:
        """Check if token is a schema name value (quoted token after schema/action word)."""
        return (bool(token.was_quoted) and 
                bool(prev_token.is_word) and 
                bool(prev_token.is_schema_word or prev_token.is_action_word))
    
    @classmethod
    def _is_field_value(cls, prev_token: RecognizedToken) -> bool:
        """Check if previous token indicates current token should be a field value."""
        return prev_token.token_class == TokenClass.OPERATOR