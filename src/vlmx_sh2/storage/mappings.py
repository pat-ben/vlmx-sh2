"""Dynamic entity-to-file mappings from CompanyDatabase.tables."""

from typing import Dict, Optional


DEFAULT_ENTITY = "company"
_mappings_cache: Optional[Dict[str, str]] = None


def _get_mappings() -> Dict[str, str]:
    """Get entity mappings with lazy loading."""
    global _mappings_cache
    if _mappings_cache is None:
        _mappings_cache = _generate_mappings()
    return _mappings_cache


def _generate_mappings() -> Dict[str, str]:
    """Generate entity-to-file mappings from CompanyDatabase.tables."""
    try:
        from ..models.schemas.company import CompanyDatabase
        
        mappings = {}
        for entity_class in CompanyDatabase.tables:
            entity_name = entity_class.get_entity_word_id()
            json_filename = f"{entity_name}.json"
            
            # Primary mapping
            mappings[entity_name] = json_filename
            
            # Add aliases if available
            if hasattr(entity_class, 'get_entity_aliases'):
                for alias in entity_class.get_entity_aliases():
                    mappings[alias] = json_filename
        
        return mappings
        
    except Exception as e:
        print(f"Warning: Could not generate dynamic mappings: {e}")
        return {"organization": "organization.json", "brand": "brand.json"}


def get_entity_json_filename(entity_word_id: str) -> Optional[str]:
    """Get JSON filename for entity word ID."""
    return _get_mappings().get(entity_word_id.lower())


def get_supported_entities() -> Dict[str, str]:
    """Get all supported entity-to-file mappings."""
    return _get_mappings().copy()


def is_supported_entity(entity_word_id: str) -> bool:
    """Check if entity word ID is supported."""
    return entity_word_id.lower() in _get_mappings()