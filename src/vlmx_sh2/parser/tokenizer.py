"""

PARSING STAGE 1/6: Tokenization

Tokenizer that extracts raw text blocks with rich position metadata.
Tokenizer stays "dumb" - just extraction + position tracking.

Validation:
- Tokenizer delegates validation to Validator (diagnostics/validator.py)
- Validation rules defined in diagnostics/rules.py
- Current validation: empty command check

"""

from typing import List
from ..models.parser import Token
from ..models.validation import ValidationContext
from vlmx_sh2.enums import Operator, IssueStage, Bracket
from ..diagnostics import Validator


# =============================================================================
# PUBLIC API
# =============================================================================

class Tokenizer:
    """Individual and quote token extraction with position metadata."""
    
    # Class-level constants (kept from current tokenizer)
    _QUOTE_CHARS = {'"', "'"}
    _BRACKET_VALUES = {bracket.value for bracket in Bracket}
    
    # Pre-sorted operators by length (longest first) for efficient detection
    _OPERATORS_BY_LENGTH = sorted([op.value for op in Operator], key=len, reverse=True)

    @classmethod
    def tokenize(cls, text: str, context: ValidationContext) -> List[Token]:
        """
        Tokenize input with validation. Returns list of Token objects.
        
        Examples:
            >>> tokenize('create company "ACME"', context)
            [
                Token(text='create', char_start=0, char_end=6, token_index=0),
                Token(text='company', char_start=7, char_end=14, token_index=1),
                Token(text='"ACME"', char_start=15, char_end=21, token_index=2),
            ]
        """
        # Validate raw text (blocking)
        if not Validator.validate_text(IssueStage.TOKENIZER, context, text=text):
            return []
            
        # Extract tokens with position metadata
        context.input_text = text
        tokens = cls._extract_with_positions(text)

        # Validate tokens (non-blocking, collect all errors)
        Validator.validate_tokens(IssueStage.TOKENIZER, context, tokens=tokens)
        
        return tokens


# =============================================================================
# MAIN EXTRACTION LOGIC
# =============================================================================

    @classmethod
    def _extract_with_positions(cls, text: str) -> List[Token]:
        """Extract tokens with position metadata. Token indices assigned in post-processing."""
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
            token_start = current_pos
            token_text, token_end = cls._extract_next_token(text, current_pos)
            
            if token_text:
                # Check for operators and split if needed
                operator_tokens = cls._split_operators(token_text, token_start)
                tokens.extend(operator_tokens)
            
            current_pos = token_end
        
        # Post-processing: assign token indices
        for token_index, token in enumerate(tokens):
            token.token_index = token_index
        
        return tokens


# =============================================================================
# TOKEN EXTRACTION HELPERS
# =============================================================================

    @classmethod
    def _extract_next_token(cls, text: str, start_pos: int) -> tuple[str, int]:
        """Extract single token starting at start_pos. Returns (token_text, end_position)."""
        current_pos = start_pos
        text_length = len(text)
        
        # Handle brackets as individual tokens
        if text[current_pos] in cls._BRACKET_VALUES:
            return text[current_pos], current_pos + 1
        
        # Handle quoted strings
        if text[current_pos] in cls._QUOTE_CHARS:
            return cls._extract_quoted_token(text, current_pos, text_length)
        
        # Handle regular text (stop at whitespace, brackets, or quotes)
        token_end = current_pos
        while token_end < text_length:
            char = text[token_end]
            if char.isspace() or char in cls._BRACKET_VALUES or char in cls._QUOTE_CHARS:
                break
            token_end += 1
        
        return text[current_pos:token_end], token_end

    @classmethod
    def _extract_quoted_token(cls, text: str, start_pos: int, text_length: int) -> tuple[str, int]:
        """Extract quoted string from start_pos. Returns (token_text, end_pos)."""
        quote_char = text[start_pos]
        token_end = start_pos + 1
        
        # Find closing quote
        while token_end < text_length:
            if text[token_end] == quote_char:
                token_end += 1  # Include closing quote
                break
            token_end += 1
        
        return text[start_pos:token_end], token_end


# =============================================================================
# OPERATOR HANDLING
# =============================================================================

    @classmethod
    def _find_operator_split(cls, token_text: str) -> tuple[str, str, str] | None:
        """Find operator in token. Returns (key, operator, value) or None. Longest-first matching."""
        for operator in cls._OPERATORS_BY_LENGTH:
            if operator in token_text:
                parts = token_text.split(operator, 1)
                if len(parts) == 2 and parts[0]:  # Valid split with non-empty key
                    return parts[0], operator, parts[1]
        return None

    @classmethod  
    def _split_operators(cls, token_text: str, token_start: int) -> List[Token]:
        """Split token on operators if present."""
        # Don't split if quoted
        if (token_text.startswith('"') and token_text.endswith('"')) or \
           (token_text.startswith("'") and token_text.endswith("'")):
            return [cls._create_token(token_text, token_start)]
        
        # Look for operators using helper method
        operator_split = cls._find_operator_split(token_text)
        if operator_split:
            key_part, operator, value_part = operator_split
            tokens = []
            char_pos = token_start
            
            # Add key, operator, value tokens
            for part in [key_part, operator, value_part]:
                if part:  # Only add non-empty
                    tokens.append(cls._create_token(part, char_pos))
                    char_pos += len(part)
            
            return tokens
        
        # No operators - single token
        return [cls._create_token(token_text, token_start)]


# =============================================================================
# TOKEN CREATION HELPERS
# =============================================================================

    @classmethod
    def _create_token(cls, text: str, char_start: int) -> Token:
        """Create Token with position metadata. Token index set in post-processing."""
        return Token(
            text=text,
            char_start=char_start,
            char_end=char_start + len(text),
            token_index=0  # Placeholder, will be set in post-processing
        )