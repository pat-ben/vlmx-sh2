"""
Tokenizer for VLMX DSL parser.

Handles tokenization of user input into basic tokens, supporting
key=value format with quoted string values and traditional command words.
Provides enhanced attribute parsing and value extraction.
"""

from typing import List, Tuple
from ..models.parser import ParsedToken, TokenType


class Tokenizer:
    """Advanced tokenizer for VLMX DSL input with quoted string support."""
    
    @classmethod
    def tokenize(cls, text: str) -> List[ParsedToken]:
        """
        Tokenize input text into basic tokens.
        
        Enhanced approach supporting:
        1. Attributes in key=value format (entity=SA, currency=EUR)
        2. Quoted values spanning multiple tokens (vision="Build the future")
        3. Traditional command words and values
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of ParsedToken objects
            
        Examples:
            >>> tokenize("create company ACME")
            [ParsedToken(text="create", position=0), ...]
            
            >>> tokenize('vision="Build the future"')
            [ParsedToken(text="vision", position=0), ParsedToken(text="Build the future", position=8, token_type=VALUE)]
        """
        tokens = []
        tokens_list = text.split()
        i = 0
        current_position = 0
        
        while i < len(tokens_list):
            raw_token = tokens_list[i].strip()
            if not raw_token:
                i += 1
                current_position = cls._calculate_next_position(text, current_position, raw_token)
                continue
            
            clean_token = raw_token.strip()
            
            # Check if this token contains an operator (for attributes)
            if cls._contains_operator(clean_token):
                # Parse attribute: key=value, key>value, etc.
                key, operator, value_start = cls._parse_attribute_token(clean_token)
                
                # Add the key as a token
                if key:
                    tokens.append(ParsedToken(
                        text=key,
                        position=current_position,
                        token_type=TokenType.UNKNOWN,
                        confidence=0.0
                    ))
                
                # Check if value starts with a quote - indicating multi-token quoted value
                if value_start and (value_start.startswith('"') or value_start.startswith("'")):
                    # Extract complete quoted value
                    complete_value, tokens_consumed = cls._extract_quoted_value(tokens_list, i)
                    
                    if complete_value:
                        value_position = current_position + len(key) + len(operator)
                        tokens.append(ParsedToken(
                            text=complete_value,
                            position=value_position,
                            token_type=TokenType.VALUE,
                            confidence=0.0
                        ))
                    
                    # Skip consumed tokens
                    for j in range(tokens_consumed):
                        if i + j < len(tokens_list):
                            current_position = cls._calculate_next_position(text, current_position, tokens_list[i + j])
                    i += tokens_consumed
                    continue
                elif value_start is not None and value_start != '':
                    # Regular unquoted value (non-empty)
                    value_position = current_position + len(key) + len(operator)
                    tokens.append(ParsedToken(
                        text=value_start,
                        position=value_position,
                        token_type=TokenType.VALUE,
                        confidence=0.0
                    ))
                elif value_start == '':
                    # Empty value (from empty quotes or no value)
                    value_position = current_position + len(key) + len(operator)
                    tokens.append(ParsedToken(
                        text='',
                        position=value_position,
                        token_type=TokenType.VALUE,
                        confidence=0.0
                    ))
            else:
                # Regular word token (action/modifier/entity/attribute)
                tokens.append(ParsedToken(
                    text=clean_token,
                    position=current_position,
                    token_type=TokenType.UNKNOWN,
                    confidence=0.0
                ))
            
            current_position = cls._calculate_next_position(text, current_position, raw_token)
            i += 1
        
        return tokens
    
    @classmethod
    def _extract_quoted_value(cls, tokens_list: List[str], start_idx: int) -> Tuple[str, int]:
        """
        Extract a quoted value that may span multiple tokens.
        
        Args:
            tokens_list: List of raw tokens from text.split()
            start_idx: Index where the quoted value starts
        
        Returns:
            Tuple of (complete_value_without_quotes, number_of_tokens_consumed)
        
        Example:
            Input: ['vision="This', 'is', 'my', 'vision"']
            Returns: ("This is my vision", 4)
        """
        if start_idx >= len(tokens_list):
            return "", 0
        
        current_token = tokens_list[start_idx]
        
        # Find the operator and extract the initial value part
        key, operator, initial_value = cls._parse_attribute_token(current_token)
        if not initial_value:
            return "", 1
        
        # Determine quote type
        quote_char = initial_value[0] if initial_value and initial_value[0] in '"\'' else None
        if not quote_char:
            return initial_value, 1
        
        # Check if quote is already closed in the same token
        if len(initial_value) > 1 and initial_value.endswith(quote_char):
            # Complete quoted value in single token: key="value"
            return initial_value[1:-1], 1
        
        # Multi-token quoted value: key="start of value continues in next tokens"
        value_parts = [initial_value[1:]]  # Remove opening quote
        tokens_consumed = 1
        
        # Continue gathering tokens until closing quote is found
        for i in range(start_idx + 1, len(tokens_list)):
            token = tokens_list[i]
            tokens_consumed += 1
            
            if token.endswith(quote_char):
                # Found closing quote
                value_parts.append(token[:-1])  # Remove closing quote
                break
            else:
                # Intermediate token - add as-is
                value_parts.append(token)
        
        # Join all parts with spaces to reconstruct the original quoted content
        complete_value = ' '.join(value_parts)
        return complete_value, tokens_consumed
    
    @classmethod
    def _calculate_next_position(cls, original_text: str, current_pos: int, token: str) -> int:
        """
        Calculate the next position in the original text after processing a token.
        
        Args:
            original_text: The original input text
            current_pos: Current position in text
            token: Token that was just processed
            
        Returns:
            Next position in the original text
        """
        # Find the actual token in the text starting from current_pos
        remaining_text = original_text[current_pos:]
        token_start = remaining_text.find(token.strip())
        
        if token_start == -1:
            # Fallback: advance by token length + 1 for space
            return current_pos + len(token) + 1
        
        # Move to position after this token
        next_pos = current_pos + token_start + len(token)
        
        # Skip any following whitespace to get to next token position
        while next_pos < len(original_text) and original_text[next_pos].isspace():
            next_pos += 1
        
        return next_pos
    
    @classmethod
    def _contains_operator(cls, token: str) -> bool:
        """Check if token contains an attribute operator."""
        operators = ['=', '>', '<', '>=', '<=', '!=']
        return any(op in token for op in operators)
    
    @classmethod
    def _parse_attribute_token(cls, token: str) -> Tuple[str, str, str]:
        """
        Parse attribute token into key, operator, value.
        
        Enhanced to handle quoted values properly by preserving quotes
        for subsequent processing by _extract_quoted_value.
        
        Args:
            token: Token containing key=value syntax
            
        Returns:
            Tuple of (key, operator, value)
            
        Note:
            Value retains quotes if present for multi-token processing.
            Use _extract_quoted_value for complete quote handling.
        """
        operators = ['>=', '<=', '!=', '=', '>', '<']  # Order matters for multi-char operators
        
        for operator in operators:
            if operator in token:
                parts = token.split(operator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Only strip quotes if it's a complete quoted value in one token
                    if (value.startswith('"') and value.endswith('"') and len(value) >= 2) or \
                       (value.startswith("'") and value.endswith("'") and len(value) >= 2):
                        value = value[1:-1]  # Remove surrounding quotes
                    
                    return key, operator, value
        
        return token, '', ''