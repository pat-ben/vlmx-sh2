"""
PARSING STAGE 1/6: Tokenization

Extracts raw text blocks without position metadata. Delegates validation to Validator.
"""

from typing import List
from ..models.parser import Token
from ..models.validation import ValidationContext
from vlmx_sh2.enums import Operator, IssueStage, Bracket
from ..diagnostics import Validator



class Tokenizer:
    """Simple token extraction without position tracking."""
 
     # =============================================================================
     # CLASS CONSTANTS
     # =============================================================================   

    _QUOTE_CHARS = {'"', "'"}
    _BRACKET_VALUES = {bracket.value for bracket in Bracket}    
    _OPERATORS_BY_LENGTH = sorted([op.value for op in Operator], key=len, reverse=True)

    # =============================================================================
    # PUBLIC API
    # =============================================================================
    
    @classmethod
    def tokenize(cls, normalized_text: str, context: ValidationContext) -> List[Token]:
        """Tokenize normalized input with validation. Returns list of Token objects."""
        # Extract tokens without position metadata
        tokens = cls._extract_tokens(normalized_text)

        # Validate tokens (non-blocking, collect all errors)
        Validator.validate_tokens(IssueStage.TOKENIZER, context, tokens=tokens)
        
        return tokens


    # =============================================================================
    # MAIN EXTRACTION LOGIC
    # =============================================================================

    @classmethod
    def _extract_tokens(cls, text: str) -> List[Token]:
        """Extract tokens without position tracking."""
        tokens = []
        cursor = 0  # Parsing cursor position in text
        text_length = len(text)
        
        while cursor < text_length:
            # Skip whitespace
            while cursor < text_length and text[cursor].isspace():
                cursor += 1
            
            # Edge case: whitespace skip reached end
            if cursor >= text_length:
                break
                
            # Extract next token (returns token text and new cursor position)
            token_text, cursor = cls._extract_next_token(text, cursor)
            
            if token_text:
                # Check for operators and split if needed
                split_tokens = cls._split_operators(token_text)
                tokens.extend(split_tokens)
        
        return tokens


    # =============================================================================
    # TOKEN EXTRACTION HELPERS
    # =============================================================================

    @classmethod
    def _extract_next_token(cls, text: str, start: int) -> tuple[str, int]:
        """
        Extract single token from current cursor position.
        
        Args:
            text: Input text to tokenize
            start: Current cursor position (where to start reading)
            
        Returns:
            (token_text, end): Extracted token text and cursor position after the token
        """
        text_length = len(text)
        
        # Handle brackets as individual tokens
        if text[start] in cls._BRACKET_VALUES:
            return text[start], start + 1
        
        # Handle quoted strings
        if text[start] in cls._QUOTE_CHARS:
            return cls._extract_quoted_token(text, start, text_length)
        
        # Handle regular text (stop at whitespace, brackets, or quotes)
        end = start
        while end < text_length:
            char = text[end]
            if char.isspace() or char in cls._BRACKET_VALUES or char in cls._QUOTE_CHARS:
                break
            end += 1
        
        return text[start:end], end

    @classmethod
    def _extract_quoted_token(cls, text: str, start: int, text_length: int) -> tuple[str, int]:
        """
        Extract quoted string including quotes, supporting escaped quotes.
        
        Args:
            text: Input text to tokenize
            start: Current cursor position (should be at opening quote)
            text_length: Length of input text
            
        Returns:
            (quoted_text, end): Extracted quoted string and cursor position after closing quote
        """
        quote_char = text[start]
        end = start + 1
        
        # Find closing quote, handling escaped quotes
        while end < text_length:
            if text[end] == '\\' and end + 1 < text_length:
                # Skip escaped character (including escaped quotes)
                end += 2
                continue
            
            if text[end] == quote_char:
                end += 1  # Include closing quote
                break
            
            end += 1
        
        return text[start:end], end


    # =============================================================================
    # OPERATOR HANDLING
    # =============================================================================

    @classmethod
    def _find_operator(cls, token_text: str) -> tuple[str, str, str] | None:
        """Find operator in token. Returns (key, operator, value) or None."""
        for operator in cls._OPERATORS_BY_LENGTH:
            if operator in token_text:
                parts = token_text.split(operator, 1)
                if len(parts) == 2 and parts[0]:  # Valid split with non-empty key
                    return parts[0], operator, parts[1]
        return None

    @classmethod  
    def _split_operators(cls, token_text: str) -> List[Token]:
        """Split token on operators if present."""
        # Don't split if quoted
        has_quotes, _ = cls._has_quotes(token_text)
        if has_quotes:
            return [cls._create_token(token_text)]
        
        # Look for operators using helper method
        operator_match = cls._find_operator(token_text)
        if operator_match:
            key, operator, value = operator_match
            tokens = []
            
            # Create tokens without position calculations
            if key:
                tokens.append(cls._create_token(key))
            
            tokens.append(cls._create_token(operator))
            
            if value:
                tokens.append(cls._create_token(value))
            
            return tokens
        
        # No operators - single token
        return [cls._create_token(token_text)]


    # =============================================================================
    # TOKEN CREATION HELPERS
    # =============================================================================

    @classmethod
    def _has_quotes(cls, text: str) -> tuple[bool, str | None]:
        """
        Check if text has matching quotes and return quote character.
        
        Returns:
            (has_quotes, quote_char) where quote_char is the detected quote character or None            

        """
        # Check minimum length
        if len(text) < 2:
            return False, None
        
        # Check if starts and ends with same quote character
        first_char = text[0]
        if first_char in cls._QUOTE_CHARS and text[-1] == first_char:
            return True, first_char
        
        return False, None

    @classmethod
    def _create_token(cls, text: str) -> Token:
        """Create Token without position metadata."""
        return Token(text=text)