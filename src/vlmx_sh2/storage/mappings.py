"""
Entity-to-file mappings.

Dynamic mapping system that generates file mappings from CompanyDatabase.tables.
Naming convention: EntityClass -> entity.json (remove "Entity" suffix and lowercase)
"""

from typing import Dict, Optional




def _generate_entity_mappings() -> Dict[str, str]:
    """
    Generate entity-to-file mappings dynamically from CompanyDatabase.tables.
    
    Returns:
        Dictionary mapping entity names to JSON filenames
    """
    try:
        # Import here to avoid circular imports at module level
        from ..models.entities.company import CompanyDatabase
        
        mappings = {}
        
        for entity_class in CompanyDatabase.tables:
            class_name = entity_class.__name__
            
            # Use the Entity's own get_entity_word_id() method for consistent naming
            entity_name = entity_class.get_entity_word_id()
            json_filename = f"{entity_name}.json"
            
            # Add primary mapping using the Entity's own word ID
            mappings[entity_name] = json_filename
            
            # Generate dynamic aliases based on Entity class if it has an aliases method
            if hasattr(entity_class, 'get_word_aliases'):
                for alias in entity_class.get_word_aliases():
                    mappings[alias] = json_filename
        
        return mappings
        
    except Exception as e:
        # Minimal fallback in case of any import issues during module loading
        print(f"Warning: Could not generate dynamic mappings: {e}")
        return {
            "organization": "organization.json", 
            "brand": "brand.json"
        }


# Initialize with empty dict - will be populated on first access
ENTITY_TO_JSON_FILE: Dict[str, str] = {}


def get_entity_json_filename(entity_word_id: str) -> Optional[str]:
    """
    Get the JSON filename for a given entity word ID.
    
    Args:
        entity_word_id: The entity word ID (e.g., "brand", "organization", "metadata")
        
    Returns:
        The corresponding JSON filename or None if not found
    """
    global ENTITY_TO_JSON_FILE
    # Lazy load mappings to avoid circular import issues
    if not ENTITY_TO_JSON_FILE:
        ENTITY_TO_JSON_FILE = _generate_entity_mappings()
    
    return ENTITY_TO_JSON_FILE.get(entity_word_id.lower())


# Default entity if none specified in command
DEFAULT_ENTITY = "company"


def get_supported_entities() -> Dict[str, str]:
    """
    Get all supported entity-to-file mappings.
    
    Returns:
        Dictionary of entity word IDs to JSON filenames
    """
    global ENTITY_TO_JSON_FILE
    # Ensure mappings are loaded
    if not ENTITY_TO_JSON_FILE:
        ENTITY_TO_JSON_FILE = _generate_entity_mappings()
    return ENTITY_TO_JSON_FILE.copy()


def is_supported_entity(entity_word_id: str) -> bool:
    """
    Check if an entity word ID is supported.
    
    Args:
        entity_word_id: The entity word ID to check
        
    Returns:
        True if the entity is supported, False otherwise
    """
    global ENTITY_TO_JSON_FILE
    # Ensure mappings are loaded
    if not ENTITY_TO_JSON_FILE:
        ENTITY_TO_JSON_FILE = _generate_entity_mappings()
    return entity_word_id.lower() in ENTITY_TO_JSON_FILE