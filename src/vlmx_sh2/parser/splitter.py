"""
PARSING STAGE 4/6: Command/Filter Splitting

Splits recognized tokens into command and filter portions based on bracket positions.
Operates on semantically classified tokens from the Recognizer stage.

Command tokens: Everything outside brackets [...]
Filter tokens: Everything inside brackets [...] (excluding brackets themselves)

Does NOT parse filter expressions (that's FilterParser's job in Stage 5).
"""

from typing import List, Optional
from ..models.parser import RecognizedToken, SplitResult
from ..models.validation import ValidationContext
from vlmx_sh2.enums import IssueStage, Bracket
from ..diagnostics import Validator


class Splitter:
    """
    PARSING STAGE 4/6: Command/Filter Splitting
    
    Splits recognized tokens into command and filter portions based on
    bracket positions. Operates on semantically classified tokens.
    """
    
    @classmethod
    def split(
        cls, 
        recognized_tokens: List[RecognizedToken], 
        context: ValidationContext
    ) -> SplitResult:
        """
        Split recognized tokens into command and filter portions.
        
        Processing:
        1. Find bracket positions ([ and ])
        2. Validate bracket structure (no nesting, only one filter section)
        3. Slice tokens into command and filter lists
        4. Return SplitResult with metadata
        
        Args:
            recognized_tokens: Fully recognized tokens (semantic + structural)
            context: ValidationContext for error reporting
            
        Returns:
            SplitResult with command_tokens, filter_tokens, and metadata
            
        Examples:
            >>> # Input: show company [currency=EUR]
            >>> tokens = [
            ...     RecognizedToken(text="show", ...),
            ...     RecognizedToken(text="company", ...),
            ...     RecognizedToken(text="[", bracket=BRACKET_OPEN, ...),
            ...     RecognizedToken(text="currency", ...),
            ...     RecognizedToken(text="=", ...),
            ...     RecognizedToken(text="EUR", ...),
            ...     RecognizedToken(text="]", bracket=BRACKET_CLOSE, ...),
            ... ]
            >>> result = Splitter.split(tokens, context)
            >>> result.command_tokens  # [show, company]
            >>> result.filter_tokens   # [currency, =, EUR]
            >>> result.has_filter      # True
        """
        # Step 1: Find bracket positions
        bracket_open_index, bracket_close_index = cls._find_bracket_positions(
            recognized_tokens, 
            context
        )
        
        # Step 2: Validate bracket structure (splitter-specific validations)
        # Note: General bracket balance already validated by Classifier
        cls._validate_bracket_structure(
            recognized_tokens, 
            bracket_open_index, 
            bracket_close_index, 
            context
        )
        
        # Step 3: Slice tokens based on bracket positions
        if bracket_open_index is not None and bracket_close_index is not None:
            # Has filter: split into command and filter
            command_tokens = (
                recognized_tokens[:bracket_open_index] +      # Before [
                recognized_tokens[bracket_close_index + 1:]   # After ]
            )
            filter_tokens = recognized_tokens[bracket_open_index + 1:bracket_close_index]
            has_filter = True
        else:
            # No filter: everything is command
            command_tokens = recognized_tokens[:]
            filter_tokens = []
            has_filter = False
        
        # Step 4: Validate the split result
        Validator.validate_tokens(IssueStage.SPLITTER, context, tokens=recognized_tokens)
        
        return SplitResult(
            command_tokens=command_tokens,
            filter_tokens=filter_tokens,
            has_filter=has_filter,
            bracket_open_index=bracket_open_index,
            bracket_close_index=bracket_close_index
        )
    
    @classmethod
    def _find_bracket_positions(
        cls,
        tokens: List[RecognizedToken],
        context: ValidationContext
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Find positions of opening and closing filter brackets.
        
        Looks for BRACKET tokens with bracket field set to BRACKET_OPEN or BRACKET_CLOSE.
        Only finds the first pair - multiple filter sections are not supported.
        
        Args:
            tokens: List of recognized tokens
            context: ValidationContext for error reporting
            
        Returns:
            Tuple of (bracket_open_index, bracket_close_index)
            Both are None if no brackets found
            
        Note:
            This method only FINDS brackets, it doesn't validate them.
            Validation happens in _validate_bracket_structure.
        """
        bracket_open_index = None
        bracket_close_index = None
        
        for i, token in enumerate(tokens):
            # Check if this token is a bracket
            if hasattr(token, 'bracket') and token.bracket:
                if token.bracket == Bracket.BRACKET_OPEN:
                    bracket_open_index = i
                elif token.bracket == Bracket.BRACKET_CLOSE:
                    bracket_close_index = i
                    break  # Stop at first closing bracket
        
        return bracket_open_index, bracket_close_index
    
    @classmethod
    def _validate_bracket_structure(
        cls,
        tokens: List[RecognizedToken],
        bracket_open_index: Optional[int],
        bracket_close_index: Optional[int],
        context: ValidationContext
    ) -> None:
        """
        Validate splitter-specific bracket rules.
        
        Checks for:
        1. Nested brackets: [[...]] is not allowed
        2. Multiple filter sections: [...] [...] is not allowed
        
        Note: General bracket balance (mismatched brackets) already validated
        by Classifier stage. This only checks splitter-specific rules.
        
        Args:
            tokens: List of recognized tokens
            bracket_open_index: Position of opening bracket (or None)
            bracket_close_index: Position of closing bracket (or None)
            context: ValidationContext for error reporting
        """
        # If we have brackets, check for nested brackets
        if bracket_open_index is not None and bracket_close_index is not None:
            # Check for nested opening brackets between the pair
            for i in range(bracket_open_index + 1, bracket_close_index):
                token = tokens[i]
                if hasattr(token, 'bracket') and token.bracket == Bracket.BRACKET_OPEN:
                    # Found nested opening bracket
                    context.add_error(
                        stage=IssueStage.SPLITTER,
                        error_code="vlmx::splitter::nested_brackets",
                        message="Nested filter brackets are not supported",
                        suggestion="Use only one filter section with logical operators (and/or) instead of nesting",
                        position=token.char_start,
                        token_index=token.token_index
                    )
                    return
            
            # Check for multiple filter sections (another [ after ])
            for i in range(bracket_close_index + 1, len(tokens)):
                token = tokens[i]
                if hasattr(token, 'bracket') and token.bracket == Bracket.BRACKET_OPEN:
                    # Found second opening bracket
                    context.add_error(
                        stage=IssueStage.SPLITTER,
                        error_code="vlmx::splitter::multiple_filters",
                        message="Multiple filter sections are not supported",
                        suggestion="Combine filters into one section using logical operators (and/or)",
                        position=token.char_start,
                        token_index=token.token_index
                    )
                    return