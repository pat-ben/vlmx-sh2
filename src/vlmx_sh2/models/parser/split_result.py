"""
SplitResult model for splitter stage output.

Contains command and filter token lists with split metadata.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .recognized_token import RecognizedToken
from .interpreted_token import InterpretedToken


class SplitResult(BaseModel):
    """
    Result from splitting tokens into command and filter portions.
    
    Contains the separated token lists plus metadata about the split operation.
    Used to pass data from Splitter to subsequent stages (FilterParser, Parser).
    
    Fields:
        command_tokens: Tokens outside brackets (the main command)
        filter_tokens: Tokens inside brackets (the filter expression)
        has_filter: Quick boolean check if filter exists
        bracket_open_index: Position of opening bracket in original list (None if no filter)
        bracket_close_index: Position of closing bracket in original list (None if no filter)
    
    Examples:
        # With filter
        >>> SplitResult(
        ...     command_tokens=[token1, token2],
        ...     filter_tokens=[token3, token4, token5],
        ...     has_filter=True,
        ...     bracket_open_index=2,
        ...     bracket_close_index=6
        ... )
        
        # Without filter
        >>> SplitResult(
        ...     command_tokens=[token1, token2, token3],
        ...     filter_tokens=[],
        ...     has_filter=False,
        ...     bracket_open_index=None,
        ...     bracket_close_index=None
        ... )
    """
    
    command_tokens: List[InterpretedToken] = Field(
        description="Tokens outside brackets (the main command)"
    )
    filter_tokens: List[InterpretedToken] = Field(
        description="Tokens inside brackets (the filter expression)"
    )
    has_filter: bool = Field(
        description="Quick boolean check if filter exists"
    )
    bracket_open_index: Optional[int] = Field(
        default=None,
        description="Position of opening bracket in original list (None if no filter)"
    )
    bracket_close_index: Optional[int] = Field(
        default=None,
        description="Position of closing bracket in original list (None if no filter)"
    )
    
    class Config:
        frozen = False  # Allow mutation if needed