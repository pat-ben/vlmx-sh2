"""
PARSING STAGE 5/8: Command/Filter Splitting

Splits interpreted tokens into command and filter portions based on bracket positions.
Operates on interpreted tokens from the Interpreter stage.

Command tokens: Everything outside brackets [...]
Filter tokens: Everything inside brackets [...] (excluding brackets themselves)

Does NOT parse filter expressions (that's FilterParser's job in Stage 6).
"""

from typing import List, Optional
from ..models.parser import InterpretedToken, SplitResult
from ..models.validation import ValidationContext
from vlmx_sh2.enums import IssueStage, Bracket
from ..diagnostics import Validator


class Splitter:
    """
    PARSING STAGE 5/8: Command/Filter Splitting
    
    Splits interpreted tokens into command and filter portions based on
    bracket positions. Operates on interpreted tokens from Interpreter stage.
    
    Operates on InterpretedToken objects from the Interpreter stage.
    """
    
    # =============================================================================
    # Public API - Main Entry Point
    # =============================================================================
    
    @classmethod
    def split(
        cls, 
        interpreted_tokens: List[InterpretedToken], 
        context: ValidationContext
    ) -> SplitResult:
        """
        Split interpreted tokens into command and filter portions.
        
        Processing:
        1. Find bracket positions ([ and ])
        2. Slice tokens into command and filter lists
        3. Validate using diagnostic rules (nested brackets, multiple sections, empty filters)
        4. Return SplitResult with metadata
        
        Args:
            interpreted_tokens: Interpreted tokens from Interpreter stage
            context: ValidationContext for error reporting
            
        Returns:
            SplitResult with command_tokens, filter_tokens, and metadata
            
        Examples:
            >>> # Input: show company [currency=EUR]
            >>> tokens = [
            ...     InterpretedToken(text="show", ...),
            ...     InterpretedToken(text="company", ...),
            ...     InterpretedToken(text="[", bracket=BRACKET_OPEN, ...),
            ...     InterpretedToken(text="currency", ...),
            ...     InterpretedToken(text="=", ...),
            ...     InterpretedToken(text="EUR", ...),
            ...     InterpretedToken(text="]", bracket=BRACKET_CLOSE, ...),
            ... ]
            >>> result = Splitter.split(tokens, context)
            >>> result.command_tokens  # [show, company]
            >>> result.filter_tokens   # [currency, =, EUR]
            >>> result.has_filter      # True
        """
        # Step 1: Find bracket positions
        bracket_open_index, bracket_close_index = cls._find_bracket_positions(
            interpreted_tokens, 
            context
        )
        
        # Step 2: Slice tokens based on bracket positions
        if bracket_open_index is not None and bracket_close_index is not None:
            # Has filter: split into command and filter
            command_tokens = (
                interpreted_tokens[:bracket_open_index] +      # Before [
                interpreted_tokens[bracket_close_index + 1:]   # After ]
            )
            filter_tokens = interpreted_tokens[bracket_open_index + 1:bracket_close_index]
            has_filter = True
        else:
            # No filter: everything is command
            command_tokens = interpreted_tokens[:]
            filter_tokens = []
            has_filter = False
        
        # Step 3: Validate the split result
        # Runs all SPLITTER stage validation rules from diagnostics module:
        # - nested_brackets: Checks for [[...]]
        # - multiple_filter_sections: Checks for [...] [...]
        # - empty_filter: Checks for []
        Validator.validate_tokens(IssueStage.SPLITTER, context, tokens=interpreted_tokens)
        
        return SplitResult(
            command_tokens=command_tokens,
            filter_tokens=filter_tokens,
            has_filter=has_filter,
            bracket_open_index=bracket_open_index,
            bracket_close_index=bracket_close_index
        )
    
    # =============================================================================
    # Bracket Detection Methods
    # =============================================================================
    
    @classmethod
    def _find_bracket_positions(
        cls,
        tokens: List[InterpretedToken],
        context: ValidationContext
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Find positions of opening and closing filter brackets.
        
        Looks for BRACKET tokens with bracket field set to BRACKET_OPEN or BRACKET_CLOSE.
        Only finds the first pair - multiple filter sections are not supported.
        
        Args:
            tokens: List of interpreted tokens
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
    
