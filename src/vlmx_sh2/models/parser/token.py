"""
Token model for tokenizer stage output.

Contains only text content without position metadata for simplified parsing.
Tokenizer stays "dumb" - just extracts text blocks without position tracking.
"""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """
    Token output from tokenizer stage.
    
    Represents a single token extracted from normalized text. Contains NO position
    metadata - that is resolved lazily only when displaying errors. Contains NO 
    semantic or structural classification - that is added by subsequent stages 
    (classifier, recognizer).
    
    Fields:
        text: The actual text of the token (quotes kept as-is from input)
    
    Examples:
        Input:      "cc ACME"
        Normalized: "create company ACME"
        
        >>> Token(text="create")
        >>> Token(text="company")
        >>> Token(text="ACME")
    """
    
    text: str = Field(
        description="The actual text of the token (quotes kept as-is from input)"
    )
    
    class Config:
        frozen = False  # Allow mutation during pipeline