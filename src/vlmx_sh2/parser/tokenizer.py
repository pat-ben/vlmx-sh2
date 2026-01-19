"""
PARSING STAGE 1/8: Tokenization

Extracts raw text blocks with position metadata. Delegates validation to Validator.
"""

from typing import List
from ..models.parser import Token
from ..models.validation import ValidationContext
from vlmx_sh2.enums import Operator, IssueStage, Bracket
from ..diagnostics import Validator



class Tokenizer:
    """Token extraction with position metadata."""
 
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
    def tokenize(cls, text: str, context: ValidationContext) -> List[Token]:
        """Tokenize input with validation. Returns list of Token objects."""
        # Validate raw text (blocking)
        if not Validator.validate_text(IssueStage.TOKENIZER, context, text=text):
            return []
            
        # Extract tokens with position metadata
        context.input_text = text
        tokens = cls._extract_tokens(text)

        # Validate tokens (non-blocking, collect all errors)
        Validator.validate_tokens(IssueStage.TOKENIZER, context, tokens=tokens)
        
        return tokens


    # =============================================================================
    # MAIN EXTRACTION LOGIC
    # =============================================================================

    @classmethod
    def _extract_tokens(cls, text: str) -> List[Token]:
        """Extract tokens with position metadata."""
        tokens = []
        current_pos = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # Skip whitespace
            while current_pos < text_length and text[current_pos].isspace():
                current_pos += 1
            
            # Edge case: whitespace skip reached end
            if current_pos >= text_length:
                break
                
            # Extract next token
            char_pos = current_pos
            token_text, char_end = cls._extract_next_token(text, current_pos)
            
            if token_text:
                # Check for operators and split if needed
                split_tokens = cls._split_operators(token_text, char_pos)
                tokens.extend(split_tokens)
            
            current_pos = char_end
        
        # Post-processing: assign token indices
        for token_index, token in enumerate(tokens):
            token.token_index = token_index
        
        return tokens


    # =============================================================================
    # TOKEN EXTRACTION HELPERS
    # =============================================================================

    @classmethod
    def _extract_next_token(cls, text: str, char_pos: int) -> tuple[str, int]:
        """Extract single token from current position."""
        current_pos = char_pos
        text_length = len(text)
        
        # Handle brackets as individual tokens
        if text[current_pos] in cls._BRACKET_VALUES:
            return text[current_pos], current_pos + 1
        
        # Handle quoted strings
        if text[current_pos] in cls._QUOTE_CHARS:
            return cls._extract_quoted_token(text, current_pos, text_length)
        
        # Handle regular text (stop at whitespace, brackets, or quotes)
        char_end = current_pos
        while char_end < text_length:
            char = text[char_end]
            if char.isspace() or char in cls._BRACKET_VALUES or char in cls._QUOTE_CHARS:
                break
            char_end += 1
        
        return text[current_pos:char_end], char_end

    @classmethod
    def _extract_quoted_token(cls, text: str, char_pos: int, text_length: int) -> tuple[str, int]:
        """Extract quoted string including quotes."""
        quote_char = text[char_pos]
        char_end = char_pos + 1
        
        # Find closing quote
        while char_end < text_length:
            if text[char_end] == quote_char:
                char_end += 1  # Include closing quote
                break
            char_end += 1
        
        return text[char_pos:char_end], char_end


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
    def _split_operators(cls, token_text: str, char_pos: int) -> List[Token]:
        """Split token on operators if present."""
        # Don't split if quoted
        if (token_text.startswith('"') and token_text.endswith('"')) or \
           (token_text.startswith("'") and token_text.endswith("'")):
            return [cls._create_token(token_text, char_pos)]
        
        # Look for operators using helper method
        operator_match = cls._find_operator(token_text)
        if operator_match:
            key, operator, value = operator_match
            tokens = []
            write_pos = char_pos
            
            # Add key, operator, value tokens
            for part in [key, operator, value]:
                if part:  # Only add non-empty
                    tokens.append(cls._create_token(part, write_pos))
                    write_pos += len(part)
            
            return tokens
        
        # No operators - single token
        return [cls._create_token(token_text, char_pos)]


    # =============================================================================
    # TOKEN CREATION HELPERS
    # =============================================================================

    @classmethod
    def _create_token(cls, text: str, char_pos: int) -> Token:
        """Create Token with position metadata."""
        return Token(
            text=text,
            char_start=char_pos,
            char_end=char_pos + len(text),
            token_index=0  # Placeholder, will be set in post-processing
        )