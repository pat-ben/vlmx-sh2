"""
Utility functions for generic command handlers.

Provides common functionality for extracting entities, fields, and context
information from parse results. Used by generic field handlers to work
with any entity-field combination dynamically.
"""

from typing import Dict, Any, Optional
from ..models.context import Context, ContextLevel
from ..storage.mappings import DEFAULT_ENTITY
from ..models.parser import ParseResult
from ..models.words import EntityWord, FieldWord

def extract_entity_from_parse_result(parse_result: ParseResult) -> str:
    """
    Extract the target entity from parse result.
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        Entity word ID (e.g., "brand", "company", "metadata")
    """
    # Use command object if available (single source of truth)
    if parse_result.command and parse_result.command.entity:
        return parse_result.command.entity.id
    
    # Fallback: look in recognized words
    for word in parse_result.recognized_words:
        if hasattr(word, 'word_type') and word.word_type.value == 'entity':
            return word.id
    
    # Default
    return DEFAULT_ENTITY

def extract_fields_from_parse_result(parse_result: ParseResult) -> Dict[str, str]:
    """
    Extract all field=value pairs from parse result.
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        Dictionary of field names to values
    """
    # Use command object (single source of truth)
    if parse_result.command:
        return parse_result.command.attributes.copy()
    
    return {}

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

def extract_target_entity_name_from_parse_result(parse_result: ParseResult) -> Optional[str]:
    """
    Extract target entity name from parse result.
    
    For commands like "show brand ACME" or "update company TechCorp",
    this extracts the target entity name (ACME, TechCorp).
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        Target entity name or None if not found
    """
    # Use command object (single source of truth)
    if parse_result.command:
        return parse_result.command.entity_name
    
    return None


def extract_specific_fields_from_tokens(parse_result: ParseResult) -> list[str]:
    """
    Extract specific field names mentioned in the command.
    
    For commands like "show brand vision mission", this extracts ["vision", "mission"].
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        List of specific field names requested
    """
    specific_fields = []
    
    # Look for field words in recognized words (FIELD type)
    for word in parse_result.recognized_words:
        if hasattr(word, 'word_type') and word.word_type.value == 'field':
            specific_fields.append(word.id)
    
    return specific_fields

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

