"""
Word registry and models.

Auto-generates EntityWord and FieldWord objects from database schemas definitions
while maintaining manual ActionWord definitions. This eliminates duplication
between database models and DSL word registrations.
"""

from typing import Dict
from ...core.utils.context.rules import is_target_allowed_in_context    
from ...core.enums.core import ContextLevel
from ...core.models.words import Word, WordType, ToolWord, ViewWord
from ...core.registry import get_all_schema_configs
from .actions import ACTION_WORDS_LIST
from .generator import (
    generate_entity_words,
    generate_field_words,
    generate_module_words,
    generate_schema_words,
    generate_tool_words,
    generate_view_words,
)

# ==================== AUTO-GENERATED WORD REGISTRY ====================

# Generate all word types
SCHEMA_WORDS = generate_schema_words()
MODULE_WORDS = {}
ENTITY_WORDS = {}
FIELD_WORDS = {}

for _cfg in get_all_schema_configs():
    MODULE_WORDS.update(generate_module_words(_cfg.schema_id))
    ENTITY_WORDS.update(generate_entity_words(_cfg.schema_id))
    FIELD_WORDS.update(generate_field_words(_cfg.schema_id))

VIEW_WORDS = generate_view_words()
TOOL_WORDS = generate_tool_words()

ACTION_WORDS = {word.id: word for word in ACTION_WORDS_LIST}

# Full registry (all words regardless of context)
WORD_REGISTRY: Dict[str, Word] = {
    **ACTION_WORDS,  # 1st: Highest priority - verbs
    **SCHEMA_WORDS,  # 2nd: Database types (company, fund) - SYS context
    **MODULE_WORDS,  # 3rd: Entity groups (core, branding) - ORG context
    **ENTITY_WORDS,  # 4th: Table names (organization, brand) - ORG context
    **VIEW_WORDS,  # 5th: Report filters (neco, investor) - APP context
    **TOOL_WORDS,  # 6th: Calculators (dcf, captable) - APP context
    **FIELD_WORDS,  # 7th: Lowest priority - field names - ORG context
}

# ==================== HELPER FUNCTIONS ====================


def get_word(word_id: str) -> Word | None:
    """Get a word by its ID"""
    return WORD_REGISTRY.get(word_id)


def get_all_words() -> Dict[str, Word]:
    """Get all registered words"""
    return WORD_REGISTRY


def get_words_by_type(word_type: WordType) -> Dict[str, Word]:
    """Get all words of a specific type"""
    return {k: v for k, v in WORD_REGISTRY.items() if v.word_type == word_type}


def get_words_for_context(context_level: ContextLevel) -> Dict[str, Word]:
    """
    Get words available in a specific context.

    Cumulative model - Actions always available, targets cumulative:
    - SYS: Schema
    - ORG: Schema + Module + Entity + Field
    - APP: All targets
    """
    result = {}

    # Actions always available
    result.update(ACTION_WORDS)

    # Filter targets by context
    for word_id, word in WORD_REGISTRY.items():
        if word.word_type == WordType.ACTION:
            continue  # Already added
        if is_target_allowed_in_context(word.word_type.value, context_level):
            result[word_id] = word

    return result


def get_views(schema_id: str = "company") -> list[ViewWord]:
    """Return ViewWord instances for the given schema_id."""
    return [v for v in VIEW_WORDS.values() if v.schema_id == schema_id]


def get_tools() -> list[ToolWord]:
    """Return all ToolWord instances."""
    return list(TOOL_WORDS.values())


def get_entity_ids_for_view(view_id: str) -> list[str]:
    """Return the entity IDs associated with a view word."""
    view_word = VIEW_WORDS.get(view_id)
    if view_word is None:
        return []
    return view_word.entities


def get_entity_ids_for_tool(tool_id: str) -> list[str]:
    """Return the entity IDs associated with a tool word."""
    # TODO: wire tool dependencies when ToolWord exposes them
    return []



def get_schema_class(schema_type: str):
    """
    Get the database schema class for a given schema type.

    Args:
        schema_type: Schema type identifier (e.g., "company", "fund")

    Returns:
        Database schema class or None if not found

    Example:
        schema_class = get_schema_class("company")  # Returns CompanyDatabase
    """
    from ...core.registry import get_schema_config

    config = get_schema_config(schema_type.lower())
    return config.schema_class if config is not None else None
