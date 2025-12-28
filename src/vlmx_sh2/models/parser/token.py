"""
Token model for tokenizer stage output.

Contains only text processing results with no semantic classification.
"""

from typing import Optional
from pydantic import BaseModel, Field

from .enums import Operator


class Token(BaseModel):
    """
    Token output from tokenizer stage.
    
    Represents a single token extracted from input text with metadata
    about quoting and operators. Contains NO semantic classification -
    that is added by the recognizer stage.
    
    Fields:
        text: The actual text of the token (quotes stripped)
        position: Position in short-listed array (0-indexed)
        was_quoted: Whether this token was originally in quotes
        operator_after: Operator that appeared after this token in original input
    
    Examples:
        >>> Token(text="create", position=0)
        >>> Token(text="ACME", position=2, was_quoted=True)
        >>> Token(text="vision", position=3, operator_after=Operator.EQUAL)
    """
    
    text: str = Field(
        description="The actual text of the token (quotes stripped)"
    )
    position: int = Field(
        description="Position in short-listed array (0-indexed)"
    )
    was_quoted: bool = Field(
        default=False,
        description="Whether this token was originally in quotes"
    )
    operator_after: Optional[Operator] = Field(
        default=None,
        description="Operator that appeared after this token in original input"
    )
    
    class Config:
        frozen = False  # Allow mutation during pipeline