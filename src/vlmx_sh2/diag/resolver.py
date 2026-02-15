
"""

PLACEHOLDER

Position resolver for lazy error position resolution.

Provides on-demand position resolution for validation errors without
tracking positions during parsing. Resolves token positions in original
user input only when displaying errors to users.
"""

from typing import Optional, Tuple
from ..core.models.validation import ValidationIssue


class PositionResolver:
    """
    Lazy position resolution for error reporting.
    
    Finds token positions in original user input on-demand,
    without tracking positions during parsing.
    
    This addresses the fundamental problem of stale position metadata:
    tokens undergo multiple transformations (macro expansion, alias resolution,
    quote stripping, fuzzy matching) which make position metadata stale and
    incorrect. Positions would reference normalized text, not the original
    user input, making error messages confusing.
    
    Example:
        >>> resolver = PositionResolver("cc ACME")
        >>> position = resolver.find_token_position("create")
        >>> position  # None (token was added by macro expansion)
        
        >>> position = resolver.find_token_position("ACME")
        >>> position  # (3, 7) - found in original input
    """
    
    def __init__(self, original_text: str):
        """
        Initialize with original user input.
        
        Args:
            original_text: The original text typed by the user (never modified)
        """
        self.original_text = original_text
    
    def find_token_position(self, token_text: str) -> Optional[Tuple[int, int]]:
        """
        Find token in original text and return (start, end) positions.
        
        Returns None if token not found (happens when token was added
        by transformations like macro expansion or inference).
        
        Args:
            token_text: The token text to find
            
        Returns:
            (start, end) positions in original_text, or None if not found
            
        Example:
            >>> resolver = PositionResolver("create company ACME")
            >>> resolver.find_token_position("ACME")
            (15, 19)
            >>> resolver.find_token_position("nonexistent")
            None
        """
        if not token_text:
            return None
            
        # Simple implementation: find first occurrence
        start = self.original_text.find(token_text)
        if start == -1:
            return None
            
        return (start, start + len(token_text))
    
    def find_position_for_issue(self, issue: ValidationIssue) -> Optional[Tuple[int, int]]:
        """
        Find position for a validation issue.
        
        Uses issue.token_text to find position in original input.
        Returns None if position cannot be determined.
        
        Args:
            issue: ValidationIssue with optional token_text
            
        Returns:
            (start, end) positions in original_text, or None if cannot resolve
            
        Example:
            >>> resolver = PositionResolver("cc ACME")
            >>> issue = ValidationIssue(token_text="ACME", message="...", ...)
            >>> resolver.find_position_for_issue(issue)
            (3, 7)
        """
        if not issue.token_text:
            return None
            
        return self.find_token_position(issue.token_text)
    
    def find_smart_position(self, token_text: str) -> Optional[Tuple[int, int]]:
        """
        Enhanced position finding with case-insensitive and partial matching.
        
        Tries multiple strategies to find token position:
        1. Exact match (case-sensitive)
        2. Case-insensitive match
        3. Word boundary match (for partial tokens)
        
        Args:
            token_text: The token text to find
            
        Returns:
            (start, end) positions in original_text, or None if not found
            
        Example:
            >>> resolver = PositionResolver("Create Company ACME")
            >>> resolver.find_smart_position("create")  # case-insensitive
            (0, 6)
            >>> resolver.find_smart_position("comp")     # partial match
            (7, 11)  # if word boundary matching enabled
        """
        if not token_text:
            return None
            
        # Strategy 1: Exact match (case-sensitive)
        exact_pos = self.find_token_position(token_text)
        if exact_pos:
            return exact_pos
            
        # Strategy 2: Case-insensitive match
        lower_token = token_text.lower()
        lower_text = self.original_text.lower()
        start = lower_text.find(lower_token)
        if start != -1:
            return (start, start + len(token_text))
            
        # Strategy 3: Could add word boundary matching here if needed
        # For now, return None if not found
        return None
    
    def get_context_around_position(
        self, 
        start: int, 
        end: int, 
        context_chars: int = 20
    ) -> Tuple[str, int]:
        """
        Get text context around a position for error display.
        
        Returns surrounding text with the problematic token highlighted,
        plus the relative position of the token within the context.
        
        Args:
            start: Start position of token in original text
            end: End position of token in original text
            context_chars: Number of characters to show before/after token
            
        Returns:
            Tuple of (context_text, token_start_in_context)
            
        Example:
            >>> resolver = PositionResolver("create company ACME Corp")
            >>> context, rel_pos = resolver.get_context_around_position(15, 19, 10)
            >>> context  # "mpany ACME Corp"
            >>> rel_pos  # 6 (position of "ACME" in context)
        """
        # Calculate context bounds
        context_start = max(0, start - context_chars)
        context_end = min(len(self.original_text), end + context_chars)
        
        # Extract context
        context_text = self.original_text[context_start:context_end]
        
        # Calculate relative position of token within context
        token_start_in_context = start - context_start
        
        return context_text, token_start_in_context