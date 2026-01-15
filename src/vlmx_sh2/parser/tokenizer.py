"""
New Tokenizer for 6-stage parser architecture.

Clean tokenizer that extracts raw text blocks with rich position metadata.
Tokenizer stays "dumb" - just extraction + position tracking.
No structural classification (classifier stage's job).
No command/filter splitting (splitter stage's job).

Validation:
- The tokenizer validates ONLY empty command input at this stage
- Additional validation rules (quotes, brackets, etc.) will be added in future stages
- All validation issues are logged to ValidationContext for diagnostic reporting
"""

from typing import List
from ..models.parser import Token
from ..models.validation import ValidationContext
from vlmx_sh2.enums import Operator, IssueStage


class Tokenizer:
    """New tokenizer for 6-stage architecture - extraction with position metadata."""
    
    # Class-level constants (kept from current tokenizer)
    _QUOTE_CHARS = {'"', "'"}
    _BRACKET_VALUES = {'[', ']', '(', ')'}
    
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
        # ==================== VALIDATION ====================
        # 
        # Tokenizer validates ONLY empty command at this stage.
        # Additional syntax validation (quotes, brackets, operators) 
        # will be handled by subsequent parser stages (classifier, recognizer).
        # 
        # All validation issues are logged to ValidationContext for 
        # comprehensive diagnostic reporting (Nushell-quality error messages).

        if not text or not text.strip():
            context.add_error(
                stage=IssueStage.TOKENIZER,
                message="Command cannot be empty",
                position=0,
                error_code="vlmx::tokenizer::empty_command",
                suggestion="Try typing a command like 'create company' or 'show metadata'"
            )
            return []
        
        # Store original input for position tracking
        context.input_text = text
        
        # Extract tokens with position metadata
        return cls._extract_with_positions(text)

    @classmethod
    def _extract_with_positions(cls, text: str) -> List[Token]:
        """
        Extract tokens with complete position metadata.
        
        Single-pass algorithm that tracks:
        - Current scan position in input
        - Token boundaries (start/end)  
        - Quote state
        - Token index counter
        
        Returns list of Token objects with all metadata populated.
        """
        tokens = []
        current_pos = 0
        token_index = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # Skip whitespace
            while current_pos < text_length and text[current_pos].isspace():
                current_pos += 1
            
            if current_pos >= text_length:
                break
                
            # Extract next token
            token_start = current_pos
            token_text, token_end = cls._extract_next_token(text, current_pos)
            
            if token_text:
                # Check for operators and split if needed
                operator_tokens = cls._split_operators(token_text, token_start, token_index)
                tokens.extend(operator_tokens)
                token_index += len(operator_tokens)
            
            current_pos = token_end
        
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
            quote_char = text[current_pos]
            token_end = current_pos + 1
            
            # Find closing quote
            while token_end < text_length:
                if text[token_end] == quote_char:
                    token_end += 1  # Include closing quote
                    break
                token_end += 1
            
            return text[current_pos:token_end], token_end
        
        # Handle regular text (stop at whitespace, brackets, or quotes)
        token_end = current_pos
        while token_end < text_length:
            char = text[token_end]
            if char.isspace() or char in cls._BRACKET_VALUES or char in cls._QUOTE_CHARS:
                break
            token_end += 1
        
        return text[current_pos:token_end], token_end

    @classmethod
    def _create_token(cls, text: str, char_start: int, token_index: int) -> Token:
        """Helper to create Token with position metadata."""
        return Token(
            text=text,
            char_start=char_start,
            char_end=char_start + len(text),
            token_index=token_index
        )

    @classmethod  
    def _split_operators(cls, token_text: str, token_start: int, base_token_index: int) -> List[Token]:
        """Split token on operators if present."""
        # Don't split if quoted
        if (token_text.startswith('"') and token_text.endswith('"')) or \
           (token_text.startswith("'") and token_text.endswith("'")):
            return [cls._create_token(token_text, token_start, base_token_index)]
        
        # Look for operators
        for operator in cls._OPERATORS_BY_LENGTH:
            if operator in token_text:
                parts = token_text.split(operator, 1)
                if len(parts) == 2 and parts[0]:  # Valid split
                    key_part, value_part = parts
                    tokens = []
                    char_pos = token_start
                    token_idx = base_token_index
                    
                    # Add key, operator, value tokens
                    for part in [key_part, operator, value_part]:
                        if part:  # Only add non-empty
                            tokens.append(cls._create_token(part, char_pos, token_idx))
                            char_pos += len(part)
                            token_idx += 1
                    
                    return tokens
        
        # No operators - single token
        return [cls._create_token(token_text, token_start, base_token_index)]