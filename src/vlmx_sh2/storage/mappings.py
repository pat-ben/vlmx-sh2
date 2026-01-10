"""
Entity-to-file mappings.

Dynamic mapping system that generates file mappings from CompanyDatabase.tables.
Naming convention: EntityClass -> entity.json (remove "Entity" suffix and lowercase)
"""

from typing import Dict, Optional


def _entity_class_to_json_filename(entity_class_name: str) -> str:
    """
    Convert entity class name to JSON filename without circular imports.
    
    Args:
        entity_class_name: Name of the entity class (e.g., "CompanyEntity")
        
    Returns:
        JSON filename (e.g., "company.json")
    """
    # Remove "Entity" suffix and convert to lowercase
    entity_name = entity_class_name.replace("Entity", "").lower()
    return f"{entity_name}.json"


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
            entity_name = class_name.replace("Entity", "").lower()
            
            # Use standard naming convention for all entities including CompanyEntity
            json_filename = _entity_class_to_json_filename(class_name)
            
            # Add primary mapping
            mappings[entity_name] = json_filename
            
            # Add common aliases
            if entity_name == "company":
                mappings.update({
                    "organization": json_filename,
                    "org": json_filename
                })
            elif entity_name == "brand":
                mappings.update({
                    "branding": json_filename,
                    "identity": json_filename
                })
            elif entity_name == "metadata":
                mappings.update({
                    "meta": json_filename,
                    "info": json_filename
                })
            elif entity_name == "offering":
                mappings.update({
                    "product": json_filename,
                    "service": json_filename
                })
            elif entity_name == "target":
                mappings.update({
                    "audience": json_filename,
                    "segment": json_filename
                })
            elif entity_name == "values":
                mappings.update({
                    "value": json_filename,
                    "principles": json_filename
                })
            elif entity_name == "address":
                mappings.update({
                    "addresses": json_filename,
                    "location": json_filename
                })
            elif entity_name == "news":
                mappings.update({
                    "article": json_filename,
                    "articles": json_filename
                })
            elif entity_name == "competitors":
                mappings.update({
                    "competitor": json_filename
                })
        
        return mappings
        
    except Exception as e:
        # Fallback in case of any import issues during module loading
        print(f"Warning: Could not generate dynamic mappings: {e}")
        return {
            "company": "company.json",
            "organization": "company.json", 
            "org": "company.json",
            "brand": "brand.json",
            "branding": "brand.json",
            "identity": "brand.json"
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