"""
Context segmentation rules.

Defines which target types are valid in each context level.
This eliminates naming collisions between entities and views/tools.

Context Segmentation:
- SYS: Schema only (database-level operations)
- ORG: Module, Entity, Field (company data operations)
- APP: View, Tool (analytics and reporting)
"""

from typing import Dict, List
from .core import ContextLevel


# Lazy initialization to avoid circular imports
_CONTEXT_ALLOWED_TARGETS: Dict[ContextLevel, List[str]] = {
    ContextLevel.SYS: ["schema"],
    ContextLevel.ORG: ["module", "entity", "field"],
    ContextLevel.APP: ["app"],
}


def is_target_allowed_in_context(word_type_value: str, context_level: ContextLevel) -> bool:
    """
    Check if a word type is allowed in the given context.
    
    Args:
        word_type_value: The WordType.value string (e.g., "entity", "app")
        context_level: Current context level
        
    Returns:
        True if allowed, False otherwise
    """
    allowed = _CONTEXT_ALLOWED_TARGETS.get(context_level, [])
    return word_type_value in allowed


def get_allowed_target_names_for_context(context_level: ContextLevel) -> List[str]:
    """Get list of allowed target type names for a context."""
    return _CONTEXT_ALLOWED_TARGETS.get(context_level, [])