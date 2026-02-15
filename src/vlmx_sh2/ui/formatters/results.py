"""
Command result formatting and display.

Handles formatting command execution results for user display, including
success/error status, entity details, missing values, and operation
confirmations. Provides structured result objects and text formatting.
"""

from typing import Optional, TYPE_CHECKING
from vlmx_sh2.diag.suggestions import SuggestionEngine

if TYPE_CHECKING:
    from vlmx_sh2.core.models.parser import ParseResult


def format_command_result(result, parse_result: Optional["ParseResult"] = None) -> str:
    """
    Format a command result for user display.
    
    Args:
        result: The command result to format (Pydantic CommandResult model)
        parse_result: Optional parse result for additional context
        
    Returns:
        Formatted result string
    """
    
    lines = []
    
    # Status line
    status = "SUCCESS" if result.success else "ERROR"
    lines.append(status)
    
    # Main message
    if result.message:
        lines.append(result.message)
    
    # For errors, generate and display suggestions if parse_result is available
    if not result.success and parse_result:
        suggestion_engine = SuggestionEngine()
        suggestions = suggestion_engine.get_command_suggestions(parse_result)
        
        if suggestions:
            lines.append("")  # Empty line for spacing
            lines.append("Suggestions:")
            for suggestion in suggestions:
                lines.append(f"  • {suggestion}")
    
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
