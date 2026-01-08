"""
Utility functions for generic command handlers.

Provides common functionality for extracting entities, fields, and context
information from parse results. Used by generic field handlers to work
with any entity-field combination dynamically.
"""

from typing import Dict, Any, Optional
from ..models.context import Context, ContextLevel

def get_company_name_from_context(context: Context) -> Optional[str]:
    """
    Get the current company name from context.
    
    Args:
        context: The execution context
        
    Returns:
        Company name if in ORG context, None if in SYS context
    """
    if context.level >= ContextLevel.ORG and context.org_name:
        return context.org_name
    return None

def format_entity_data_for_display(entity_data: Dict[str, Any], 
                                 specific_fields: list[str] | None = None) -> str:
    """
    Format entity data for user display.
    
    Args:
        entity_data: The entity data dictionary
        specific_fields: Specific fields to show, or None for all
        
    Returns:
        Formatted string for display
    """
    if not entity_data:
        return "No data found"
    
    lines = []
    
    # Filter to specific fields if requested
    if specific_fields:
        data_to_show = {field: entity_data.get(field) for field in specific_fields}
    else:
        data_to_show = entity_data
    
    # Format each field
    for key, value in data_to_show.items():
        if value is not None:
            if isinstance(value, str) and len(value) > 50:
                # Truncate long values
                formatted_value = value[:50] + "..."
            else:
                formatted_value = str(value)
            lines.append(f"{key}: {formatted_value}")
        else:
            lines.append(f"{key}: (not set)")
    
    return "\n".join(lines) if lines else "No fields to display"

