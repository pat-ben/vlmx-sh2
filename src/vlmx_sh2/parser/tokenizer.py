"""
Tokenizer for VLMX DSL parser.

Handles tokenization of user input into basic tokens, supporting both
traditional flag syntax (--key=value) and simplified key=value format.
Provides enhanced attribute parsing and value extraction.
"""

from typing import List, Tuple
from ..models.parser import ParsedToken, TokenType


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