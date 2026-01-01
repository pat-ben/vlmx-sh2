"""
Utility functions for generic command handlers.

Provides common functionality for extracting entities, attributes, and context
information from parse results. Used by generic attribute handlers to work
with any entity-attribute combination dynamically.
"""

from typing import Dict, Any, Optional
from ..models.context import Context
from ..storage.mappings import DEFAULT_ENTITY
from ..models.parser import ParseResult
from ..dsl.words import get_word
from ..models.words import EntityWord, AttributeWord

def extract_entity_from_parse_result(parse_result: ParseResult) -> str:
    """
    Extract the target entity from parse result.
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        Entity word ID (e.g., "brand", "company", "metadata")
    """
    # Use command object if available (single source of truth)
    if parse_result.command:
        return parse_result.command.entity.id
    
    # Fallback: look in recognized words
    for word in parse_result.recognized_words:
        if hasattr(word, 'word_type') and word.word_type.value == 'entity':
            return word.id
    
    # Default
    return DEFAULT_ENTITY

def extract_attributes_from_parse_result(parse_result: ParseResult) -> Dict[str, str]:
    """
    Extract all attribute=value pairs from parse result.
    
    Args:
        parse_result: The parsed command result
        
    Returns:
        Dictionary of attribute names to values
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
    if context.level >= 1 and context.org_name:
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

def validate_field_for_entity(field_id: str, entity_id: str) -> bool:
    """
    Validate if a field exists on an entity using the Words Registry.
    
    Args:
        field_id: ID of the field word
        entity_id: ID of the entity word
        
    Returns:
        True if the field exists on the entity, False otherwise
    """
    
    # Get the field word
    field_word = get_word(field_id)
    if not field_word or not isinstance(field_word, AttributeWord):
        return False
    
    # Get the entity word
    entity_word = get_word(entity_id)
    if not entity_word or not isinstance(entity_word, EntityWord):
        return False
    
    # Check if the entity model is in the field's entity_models list
    return entity_word.entity_model in field_word.entity_models

def validate_entity_field_combination(entity_word_id: str, field_name: str) -> bool:
    """
    Validate if a field can be used with an entity.
    
    Uses the Words Registry to check if the field is valid for the entity.
    
    Args:
        entity_word_id: The entity word ID
        field_name: The field name
        
    Returns:
        True if the combination is valid, False otherwise
    """
    return validate_field_for_entity(field_name, entity_word_id)

def get_entity_model_from_entity_id(entity_id: str):
    """
    Get the entity model class from entity ID.
    
    Args:
        entity_id: The entity word ID
        
    Returns:
        Entity model class or None if not found
    """
    entity_word = get_word(entity_id)
    if entity_word and isinstance(entity_word, EntityWord):
        return entity_word.entity_model
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

def create_updated_entity_data(current_data: Dict[str, Any], 
                             updates: Dict[str, str]) -> Dict[str, Any]:
    """
    Create updated entity data with new attribute values.
    
    Args:
        current_data: Current entity data
        updates: Dictionary of attribute updates
        
    Returns:
        Updated entity data dictionary
    """
    from datetime import datetime
    
    # Create a copy of current data
    updated_data = current_data.copy()
    
    # Apply updates
    for attr_name, attr_value in updates.items():
        updated_data[attr_name] = attr_value
    
    # Update timestamp if it exists
    if 'updated_at' in updated_data:
        updated_data['updated_at'] = datetime.now().isoformat()
    
    return updated_data