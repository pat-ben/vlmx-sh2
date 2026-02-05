"""
Word registry and models.

Auto-generates EntityWord and FieldWord objects from database schemas definitions
while maintaining manual ActionWord definitions. This eliminates duplication
between database models and DSL word registrations.
"""

from typing import Dict

from ..models.words import WordType, Word
from .generator import (
    generate_schema_words, 
    generate_entity_words, 
    generate_field_words,
    generate_module_words,
    generate_view_words,
    generate_tool_words
)
from .actions import ACTION_WORDS_LIST
from ..schemas.company import CompanyDatabase
from ..enums.core import ContextLevel
from ..enums.context_rules import is_target_allowed_in_context


# ==================== AUTO-GENERATED WORD REGISTRY ====================

# List of all database schemas to include in the word registry
SCHEMAS = [
    CompanyDatabase,
    # Add more database schemas here as they are created:
    # FundDatabase,
    # HoldingDatabase,
]

# Generate all word types
SCHEMA_WORDS = generate_schema_words()
MODULE_WORDS = {}
ENTITY_WORDS = {}
FIELD_WORDS = {}

for schema in SCHEMAS:
    MODULE_WORDS.update(generate_module_words(schema))
    ENTITY_WORDS.update(generate_entity_words(schema))
    FIELD_WORDS.update(generate_field_words(schema))

VIEW_WORDS = generate_view_words()
TOOL_WORDS = generate_tool_words()

ACTION_WORDS = {word.id: word for word in ACTION_WORDS_LIST}

# Full registry (all words regardless of context)
WORD_REGISTRY: Dict[str, Word] = {
    **ACTION_WORDS,    # 1st: Highest priority - verbs
    **SCHEMA_WORDS,    # 2nd: Database types (company, fund) - SYS context
    **MODULE_WORDS,    # 3rd: Entity groups (core, branding) - ORG context
    **ENTITY_WORDS,    # 4th: Table names (organization, brand) - ORG context
    **VIEW_WORDS,      # 5th: Report filters (neco, investor) - APP context
    **TOOL_WORDS,      # 6th: Calculators (dcf, captable) - APP context
    **FIELD_WORDS,     # 7th: Lowest priority - field names - ORG context
}

# ==================== HELPER FUNCTIONS ====================

def get_word(word_id: str) -> Word | None:
    """Get a word by its ID"""
    return WORD_REGISTRY.get(word_id)


def get_all_words() -> Dict[str, Word]:
    """Get all registered dsl"""
    return WORD_REGISTRY


def get_words_by_type(word_type: WordType) -> Dict[str, Word]:
    """Get all dsl of a specific type"""
    return {
        k: v for k, v in WORD_REGISTRY.items()
        if v.word_type == word_type
    }


def get_words_for_context(context_level: ContextLevel) -> Dict[str, Word]:
    """
    Get words available in a specific context.
    
    Actions are always available. Targets are filtered by context rules:
    - SYS: Schema only
    - ORG: Module, Entity, Field
    - APP: View, Tool
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