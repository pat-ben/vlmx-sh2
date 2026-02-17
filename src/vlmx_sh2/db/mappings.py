"""Entity-to-file mappings, delegating to the core registry."""

from typing import Dict, Optional

from ..core.registry import (
    get_all_storage_mappings,
    get_storage_mapping,
    resolve_entity_alias,
)

def get_entity_json_filename(entity_word_id: str) -> Optional[str]:
    """Get JSON filename for entity word ID (or alias)."""
    key = entity_word_id.lower()

    # Direct lookup
    mapping = get_storage_mapping(key)
    if mapping is not None:
        return mapping.json_filename

    # Try alias resolution
    canonical = resolve_entity_alias(key)
    if canonical is not None:
        mapping = get_storage_mapping(canonical)
        if mapping is not None:
            return mapping.json_filename

    return None


def get_supported_entities() -> Dict[str, str]:
    """Get all supported entity-to-file mappings (includes aliases)."""
    result: Dict[str, str] = {}
    for entity_id, mapping in get_all_storage_mappings().items():
        result[entity_id] = mapping.json_filename
        for alias in mapping.aliases:
            result[alias] = mapping.json_filename
    return result


def is_supported_entity(entity_word_id: str) -> bool:
    """Check if entity word ID is supported."""
    key = entity_word_id.lower()
    if get_storage_mapping(key) is not None:
        return True
    canonical = resolve_entity_alias(key)
    return canonical is not None and get_storage_mapping(canonical) is not None
