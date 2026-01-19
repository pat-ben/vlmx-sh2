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
        Tokenize input text into flat list of tokens with rich position metadata.
        
        Args:
            text: Raw user input
            context: ValidationContext for error reporting
            
        Returns:
            List of Token objects with complete position metadata
            
        Examples:
            >>> tokenize('create company "ACME"', context)
            [
                Token(text='create', char_start=0, char_end=6, token_index=0),
                Token(text='company', char_start=7, char_end=14, token_index=1),
                Token(text='"ACME"', char_start=15, char_end=21, token_index=2),
            ]
        """
        # ==================== TWO-TIER VALIDATION ====================
        # 
        # Step 1: Text-level validation (pre-tokenization)
        # - Validates raw input before any parsing begins
        # - Always blocking (fail fast on fundamental issues)
        # - Position always 0 (no tokens exist yet)
        # - Examples: empty command, max length, encoding issues
        
        if not Validator.validate_text(IssueStage.TOKENIZER, context, text=text):
            return []  # Stop immediately for text-level errors
        
        # Step 2: Extract tokens with position metadata
        context.input_text = text
        tokens = cls._extract_with_positions(text)
        
        # Step 3: Token-level validation (post-tokenization)
        # - Validates individual tokens with position metadata
        # - Non-blocking by default (collect ALL errors)
        # - Position extracted from token metadata
        # - Examples: unclosed quotes, mismatched brackets, unknown words
        # Note: We don't check return value unless there's a rare blocking token error
        
        Validator.validate_tokens(IssueStage.TOKENIZER, context, tokens=tokens)
        
        return tokens

    @classmethod
    def _extract_with_positions(cls, text: str) -> List[Token]:
        """
        Extract tokens with complete position metadata.
        
        Single-pass algorithm that tracks:
        - Current scan position in input
        - Token boundaries (start/end)  
        - Quote state
        
        Token indices are assigned in post-processing for simplicity.
        Returns list of Token objects with all metadata populated.
        """
        tokens = []
        current_pos = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # Skip whitespace
            while current_pos < text_length and text[current_pos].isspace():
                current_pos += 1
            
            # Defensive check for edge cases where whitespace skipping reaches end
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

    @classmethod
    def _extract_next_token(cls, text: str, start_pos: int) -> tuple[str, int]:
        """
        Extract a single token starting at start_pos.
        
        Returns:
            (token_text, end_position)
        """
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
        """
        Extract a complete quoted string starting at start_pos.
        
        Args:
            text: Input text containing the quoted string
            start_pos: Position of the opening quote character
            text_length: Length of the input text
            
        Returns:
            tuple[str, int]: (token_text, end_position)
                - token_text: Complete quoted string including opening and closing quotes
                - end_position: Position after the closing quote
                
        Note:
            The result includes both opening and closing quotes in the token text.
            If no closing quote is found, extracts until end of text.
        """
        quote_char = text[start_pos]
        token_end = start_pos + 1
        
        # Find closing quote
        while token_end < text_length:
            if text[token_end] == quote_char:
                token_end += 1  # Include closing quote
                break
            token_end += 1
        
        return text[start_pos:token_end], token_end

    @classmethod
    def _find_operator_split(cls, token_text: str) -> tuple[str, str, str] | None:
        """
        Detect operator in token and return split parts.
        
        Args:
            token_text: Text to search for operators
            
        Returns:
            (key, operator, value) if operator found, None otherwise
            
        Uses longest-first matching for operator precedence.
        """
        for operator in cls._OPERATORS_BY_LENGTH:
            if operator in token_text:
                parts = token_text.split(operator, 1)
                if len(parts) == 2 and parts[0]:  # Valid split with non-empty key
                    return parts[0], operator, parts[1]
        return None

    @classmethod
    def _create_token(cls, text: str, char_start: int) -> Token:
        """Helper to create Token with position metadata. Token index set in post-processing."""
        return Token(
            text=text,
            char_start=char_start,
            char_end=char_start + len(text),
            token_index=0  # Placeholder, will be set in post-processing
        )

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