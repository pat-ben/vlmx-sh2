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


def format_command_result(result, parse_result: Optional["ParseResult"] = None) -> str:
    """
    Format a command result for user display.
    
    Args:
        result: The command result to format (Pydantic CommandResult model)
        parse_result: Optional parse result for additional context
        
    Returns:
        Formatted result string
    """
    from ..models.results import CommandResult
    
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
