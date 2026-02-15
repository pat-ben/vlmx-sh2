"""
Context rules - Cumulative model.

Each higher level inherits all targets from lower levels:
- SYS: Schema only
- ORG: SYS + Module, Entity, Field  
- APP: ORG + View, Tool (everything)
"""

from typing import Dict, List
from .core import ContextLevel

# Cumulative targets: each level includes previous levels
_CONTEXT_ALLOWED_TARGETS: Dict[ContextLevel, List[str]] = {
    ContextLevel.SYS: ["schema"],
    ContextLevel.ORG: ["schema", "module", "entity", "field"],
    ContextLevel.APP: ["schema", "module", "entity", "field", "app"],
}


def is_target_allowed_in_context(word_type_value: str, context_level: ContextLevel) -> bool:
    """
    Check if a word type is allowed in the given context.
    
    Cumulative model: higher levels include all lower level targets.
    
    Args:
        word_type_value: The WordType.value string (e.g., "entity", "app")
        context_level: Current context level
        
    Returns:
        True if allowed, False otherwise
    """
    allowed = _CONTEXT_ALLOWED_TARGETS.get(context_level, [])
    return word_type_value in allowed


def get_allowed_target_names_for_context(context_level: ContextLevel) -> List[str]:
    """Get list of allowed target type names for a context (cumulative)."""
    return _CONTEXT_ALLOWED_TARGETS.get(context_level, [])