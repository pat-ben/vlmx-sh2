"""
PARSING STAGE 7/7: Command Building

Assembles ParsedCommand from interpreted tokens.
Extracts action, target, field values from tokens and assembles a ParsedCommand.

This stage operates on interpreted tokens to extract command components:
- Action words (create, add, delete, etc.)
- Target schemas/entities (company, brand, etc.)  
- Target names (quoted strings or unknown tokens)
- Field-value pairs (currency=EUR, vision="Our vision")
- Standalone field words (for field selection/deletion)
"""

from typing import Optional, List
from ..models.parser import ParsedCommand
from ..models.parser.filter import FilterExpression
from ..models.validation import ValidationContext


class Builder:
    """
    Thin wrapper for ParsedCommand.from_tokens().
    
    Maintains consistency with other parsing stages while delegating
    the actual command building logic to ParsedCommand itself.
    """
    
    # =============================================================================
    # Public API - Main Entry Point
    # =============================================================================
    
    @classmethod
    def build(
        cls,
        command_tokens: List,
        filter_expression: Optional[FilterExpression],
        raw_input: str,
        context: ValidationContext
    ) -> Optional[ParsedCommand]:
        """
        Build ParsedCommand from command tokens and filter AST.
        
        Delegates to ParsedCommand.from_tokens() for the actual building logic.
        
        Args:
            command_tokens: Interpreted tokens from splitter (command portion)
            filter_expression: Parsed filter AST (or None)
            raw_input: Original user input
            context: ValidationContext for error reporting
            
        Returns:
            ParsedCommand if successful, None if building failed
        """
        return ParsedCommand.from_tokens(
            tokens=command_tokens,
            filter_expression=filter_expression,
            raw_input=raw_input,
            context=context
        )