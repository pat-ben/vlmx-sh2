"""
Entity-to-file mappings for VLMX DSL.

Maps entity word IDs to their corresponding JSON file names in the folder structure.
Used by generic command handlers to determine which file to load/save based on
the entity type extracted from user commands.
"""

from typing import Dict, Optional

# Entity word IDs to JSON file mappings
ENTITY_TO_JSON_FILE: Dict[str, str] = {
    "company": "organization.json",
    "organization": "organization.json",
    "org": "organization.json",  # Abbreviation alias
    
    "brand": "brand.json",
    "branding": "brand.json",  # Alias
    "identity": "brand.json",  # Alias
    
    "metadata": "metadata.json",
    "meta": "metadata.json",  # Alias
    "info": "metadata.json",  # Alias
    
    "offering": "brand.json",  # Offerings are stored in brand.json as part of brand data
    "product": "brand.json",   # Alias
    "service": "brand.json",   # Alias
    
    "target": "brand.json",    # Targets are stored in brand.json as part of brand data
    "audience": "brand.json",  # Alias
    "segment": "brand.json",   # Alias
    
    "value": "brand.json",     # Values are stored in brand.json as part of brand data
    "values": "brand.json",    # Alias
    "principles": "brand.json", # Alias
}

# Default entity if none specified in command
DEFAULT_ENTITY = "organization"

def get_entity_json_filename(entity_word_id: str) -> Optional[str]:
    """
    Get the JSON filename for a given entity word ID.
    
    Args:
        entity_word_id: The entity word ID (e.g., "brand", "organization", "metadata")
        
    Returns:
        The corresponding JSON filename or None if not found
    """
    return ENTITY_TO_JSON_FILE.get(entity_word_id.lower())

def get_supported_entities() -> Dict[str, str]:
    """
    Get all supported entity-to-file mappings.
    
    Returns:
        Dictionary of entity word IDs to JSON filenames
    """
    return ENTITY_TO_JSON_FILE.copy()

def is_supported_entity(entity_word_id: str) -> bool:
    """
    Check if an entity word ID is supported.
    
    Args:
        entity_word_id: The entity word ID to check
        
    Returns:
        True if the entity is supported, False otherwise
    """
    return entity_word_id.lower() in ENTITY_TO_JSON_FILE