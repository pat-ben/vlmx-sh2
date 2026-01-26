"""
ClassifiedToken model for classifier stage output.

Contains structural classification with quotes stripped and operators identified.
"""

from typing import Optional
from pydantic import BaseModel, Field

from vlmx_sh2.enums.parser import TokenClass, Operator, Bracket


class ClassifiedToken(BaseModel):
    """
    Token with structural classification. Quotes stripped, operators identified.
    
    Represents the output of the classifier stage - tokens that have been
    structurally analyzed and classified, with quotes stripped and operators
    identified. Contains NO position metadata - that is resolved lazily only 
    when displaying errors.
    
    Fields:
        text: Token text with quotes stripped (classifier's job)
        token_class: Structural classification (TEXT, OPERATOR, BRACKET)
        was_quoted: True if originally in quotes (TEXT tokens only), None for OPERATOR/BRACKET
        operator: If OPERATOR class, which operator it is
        bracket: If BRACKET class, which bracket it is
    
    Examples:
        # TEXT token (not quoted)
        >>> ClassifiedToken(text="create", token_class=TokenClass.TEXT, was_quoted=False)
        
        # TEXT token (was quoted, quotes stripped)
        >>> ClassifiedToken(text="ACME", token_class=TokenClass.TEXT, was_quoted=True)
        
        # OPERATOR token (was_quoted=None by default)
        >>> ClassifiedToken(text="=", token_class=TokenClass.OPERATOR, operator=Operator.EQUAL)
        
        # BRACKET token (was_quoted=None by default)
        >>> ClassifiedToken(text="[", token_class=TokenClass.BRACKET, bracket=Bracket.BRACKET_OPEN)
    """
    
    text: str = Field(description="Token text with quotes stripped (classifier's job)")
    token_class: TokenClass = Field(description="Structural classification (TEXT | OPERATOR | BRACKET)")
    was_quoted: Optional[bool] = Field(
        default=None,
        description="True if originally in quotes (TEXT tokens only, None for non-TEXT tokens)"
    )
    operator: Optional[Operator] = Field(
        default=None,
        description="If OPERATOR class, which operator it is"
    )
    bracket: Optional[Bracket] = Field(
        default=None,
        description="If BRACKET class, which bracket it is"
    )
    
    class Config:
        frozen = False  # Allow mutation during pipeline