"""
Command result formatting and display.

Handles formatting command execution results for user display, including
success/error status, entity details, missing values, and operation
confirmations. Provides structured result objects and text formatting.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.parser import ParseResult
    from ..models.context import Context


class CommandResult:
    """
    DEPRECATED: Legacy command result class. 
    Use models.results.CommandResult (Pydantic model) for new code.
    
    Represents the result of a command execution.
    """
    
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


def format_command_result(result, parse_result: Optional["ParseResult"] = None) -> str:
    """
    Format a command result for user display.
    
    Args:
        result: The command result to format (Pydantic CommandResult model)
        parse_result: Optional parse result for additional context
        
    Returns:
        Formatted result string
    """
    # Import the new CommandResult type for type checking
    from ..models.results import CommandResult as NewCommandResult
    
    # Handle new Pydantic CommandResult model
    if isinstance(result, NewCommandResult):
        lines = []
        
        # Status line
        status = "SUCCESS" if result.success else "ERROR"
        lines.append(status)
        
        # Main message
        if result.message:
            lines.append(result.message)
        
        # Display data if available
        if result.data:
            lines.append("")  # Empty line for spacing
            for key, value in result.data.items():
                # Skip context_switch data as it's handled elsewhere
                if key != "context_switch":
                    if isinstance(value, dict):
                        lines.append(f"  {key}:")
                        for sub_key, sub_value in value.items():
                            lines.append(f"    {sub_key}: {sub_value}")
                    elif isinstance(value, list):
                        lines.append(f"  {key}: {', '.join(str(v) for v in value)}")
                    else:
                        lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
    
    # Fallback for old CommandResult format (legacy support)
    else:
        lines = []
        
        # First line: success/error status and missing optional words count
        status = "SUCCESS" if result.success else "ERROR"
        missing_count = len(getattr(result, 'missing_optional_words', []))
        
        if missing_count > 0:
            lines.append(f"{status} (missing {missing_count} optional values)")
        else:
            lines.append(status)
        
        # Success case
        if result.success:
            # Confirmation message
            entity_name = getattr(result, 'entity_name', '')
            operation = getattr(result, 'operation', '')
            if entity_name and operation:
                lines.append(f"{entity_name} {operation}")
            
            # Display attributes (vertical list)
            attributes = getattr(result, 'attributes', {})
            if attributes:
                lines.append("")  # Empty line for spacing
                for key, value in attributes.items():
                    lines.append(f"  {key}: {value}")
        
        # Error case
        else:
            # Explain unrecognized words
            errors = getattr(result, 'errors', [])
            if errors:
                lines.append("")
                for error in errors:
                    lines.append(f"  {error}")
            
            # Show parse errors if available
            if parse_result and parse_result.errors:
                lines.append("")
                for error in parse_result.errors:
                    lines.append(f"  {error}")
        
        # Show missing optional words
        missing_optional_words = getattr(result, 'missing_optional_words', [])
        if missing_optional_words:
            lines.append("")
            lines.append("Missing optional values:")
            for word in missing_optional_words:
                lines.append(f"  {word}")
        
        return "\n".join(lines)


def create_success_result(operation: str, entity_name: str, attributes: Optional[Dict[str, Any]] = None) -> CommandResult:
    """
    DEPRECATED: Use models.results.CommandResult directly instead.
    Create a successful command result.
    """
    result = CommandResult(success=True, operation=operation, entity_name=entity_name)
    
    if attributes:
        for key, value in attributes.items():
            result.add_attribute(key, value)
    
    return result


def create_error_result(errors: List[str], parse_result: Optional["ParseResult"] = None) -> CommandResult:
    """
    DEPRECATED: Use models.results.ErrorResult directly instead.
    Create an error command result.
    """
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
    """
    DEPRECATED: Use models.results.ErrorResult directly instead.
    Create an error result from parse result errors.
    """
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