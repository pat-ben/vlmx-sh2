"""
Command result formatting and display.

Handles formatting command execution results for user display, including
success/error status, entity details, missing values, and operation
confirmations. Provides structured result objects and text formatting.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..dsl.parser import ParseResult
    from ..models.context import Context


class CommandResult:
    """Represents the result of a command execution."""
    
    def __init__(self, success: bool, operation: str = "", entity_name: str = ""):
        self.success = success
        self.operation = operation  # e.g., "created", "deleted", "updated"
        self.entity_name = entity_name  # e.g., "ACME", "company ACME"
        self.attributes: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.missing_optional_words: List[str] = []
        self.new_context: Optional["Context"] = None  # Context to switch to after command execution
    
    def add_attribute(self, key: str, value: Any) -> None:
        """Add an attribute to display."""
        self.attributes[key] = value
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
    
    def add_missing_optional_word(self, word: str) -> None:
        """Add a missing optional word."""
        self.missing_optional_words.append(word)
    
    def set_context_switch(self, new_context: "Context") -> None:
        """Set a new context to switch to after command execution."""
        self.new_context = new_context


def format_command_result(result: CommandResult, parse_result: Optional["ParseResult"] = None) -> str:
    """
    Format a command result for user display.
    
    Args:
        result: The command result to format
        parse_result: Optional parse result for additional context
        
    Returns:
        Formatted result string
    """
    lines = []
    
    # First line: success/error status and missing optional words count
    status = "SUCCESS" if result.success else "ERROR"
    missing_count = len(result.missing_optional_words)
    
    if missing_count > 0:
        lines.append(f"{status} (missing {missing_count} optional values)")
    else:
        lines.append(status)
    
    # Success case
    if result.success:
        # Confirmation message
        if result.entity_name and result.operation:
            lines.append(f"{result.entity_name} {result.operation}")
        
        # Display attributes (vertical list)
        if result.attributes:
            lines.append("")  # Empty line for spacing
            for key, value in result.attributes.items():
                lines.append(f"  {key}: {value}")
    
    # Error case
    else:
        # Explain unrecognized words
        if result.errors:
            lines.append("")
            for error in result.errors:
                lines.append(f"  {error}")
        
        # Show parse errors if available
        if parse_result and parse_result.errors:
            lines.append("")
            for error in parse_result.errors:
                lines.append(f"  {error}")
    
    # Show missing optional words
    if result.missing_optional_words:
        lines.append("")
        lines.append("Missing optional values:")
        for word in result.missing_optional_words:
            lines.append(f"  {word}")
    
    return "\n".join(lines)


def create_success_result(operation: str, entity_name: str, attributes: Optional[Dict[str, Any]] = None) -> CommandResult:
    """Create a successful command result."""
    result = CommandResult(success=True, operation=operation, entity_name=entity_name)
    
    if attributes:
        for key, value in attributes.items():
            result.add_attribute(key, value)
    
    return result


def create_error_result(errors: List[str], parse_result: Optional["ParseResult"] = None) -> CommandResult:
    """Create an error command result."""
    result = CommandResult(success=False)
    
    for error in errors:
        result.add_error(error)
    
    # Add parse-specific errors
    if parse_result:
        # Add unrecognized words
        for token in parse_result.tokens:
            if token.token_type.name == "UNKNOWN" and token.suggestions:
                result.add_error(f"Word '{token.text}' not understood. Did you mean: {', '.join(token.suggestions[:3])}?")
            elif token.token_type.name == "UNKNOWN":
                result.add_error(f"Word '{token.text}' not understood")
    
    return result


def create_result_from_parse_errors(parse_result: "ParseResult") -> CommandResult:
    """Create an error result from parse result errors."""
    result = CommandResult(success=False)
    
    # Add unrecognized words
    for token in parse_result.tokens:
        if token.token_type.name == "UNKNOWN":
            if token.suggestions:
                result.add_error(f"Word '{token.text}' not understood. Did you mean: {', '.join(token.suggestions[:3])}?")
            else:
                result.add_error(f"Word '{token.text}' not understood")
    
    # Add general parse errors
    for error in parse_result.errors:
        result.add_error(error)
    
    return result