"""
Utility functions for VLMX DSL handlers.

Contains shared business logic utilities used by the dynamic handlers.
The actual handlers are now implemented in words.py as dynamic functions.
"""

from ..core.context import Context
from ..dsl.words import get_word, EntityWord


# ==================== BUSINESS LOGIC UTILITIES ====================

def validate_attribute_for_entity(attribute_id: str, entity_id: str) -> bool:
    """
    Validate if an attribute exists on an entity using the Words Registry.
    
    Args:
        attribute_id: ID of the attribute word
        entity_id: ID of the entity word
        
    Returns:
        True if the attribute exists on the entity, False otherwise
    """
    from ..dsl.words import AttributeWord
    
    # Get the attribute word
    attribute_word = get_word(attribute_id)
    if not attribute_word or not isinstance(attribute_word, AttributeWord):
        return False
    
    # Get the entity word
    entity_word = get_word(entity_id)
    if not entity_word or not isinstance(entity_word, EntityWord):
        return False
    
    # Check if the entity model is in the attribute's entity_models list
    return entity_word.entity_model in attribute_word.entity_models


def get_entity_model_from_registry(entity_id: str):
    """
    Get entity model from Words Registry with validation.
    
    Args:
        entity_id: ID of the entity word
        
    Returns:
        Entity model class or None if not found
    """
    entity_word = get_word(entity_id)
    if entity_word and isinstance(entity_word, EntityWord):
        return entity_word.entity_model
    return None


# ==================== LEGACY COMPATIBILITY ====================

def register_all_commands():
    """
    Legacy function for backward compatibility.
    In the new system, no command registration is needed.
    """
    # In the new dynamic system, we don't register commands
    # All functionality is handled through direct handler invocation
    return 0  # Return 0 to indicate no commands were registered