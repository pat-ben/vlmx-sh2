"""
Word registry and models.

Auto-generates EntityWord and FieldWord objects from database entities definitions
while maintaining manual ActionWord definitions. This eliminates duplication
between database models and DSL word registrations.
"""

from typing import Dict

from ...models.words import WordType, Word
from .generator import generate_schema_words, generate_entity_words, generate_field_words
from .actions import ACTION_WORDS_LIST
from ...models.entities.company import CompanyDatabase


# ==================== AUTO-GENERATED WORD REGISTRY ====================

# List of all database schemas to include in the word registry
SCHEMAS = [
    CompanyDatabase,
    # Add more database schemas here as they are created:
    # FundDatabase,
    # HoldingDatabase,
]

# Generate SchemaWords (highest priority), EntityWords, FieldWords
SCHEMA_WORDS = generate_schema_words()
ENTITY_WORDS = {}
FIELD_WORDS = {}

for schema in SCHEMAS:
    entity_words = generate_entity_words(schema)
    field_words = generate_field_words(schema)
    ENTITY_WORDS.update(entity_words)
    FIELD_WORDS.update(field_words)

# Convert action list to dict
ACTION_WORDS = {word.id: word for word in ACTION_WORDS_LIST}

# Combine into final registry with proper priority order
WORD_REGISTRY: Dict[str, Word] = {
    **ACTION_WORDS,# 1st: Highest priority - actions can't be overridden
    **SCHEMA_WORDS,    # 2nd: Database types (company, fund, holding)
    **ENTITY_WORDS,    # 3rd: Table names (organization, brand, news)
    **FIELD_WORDS,     # 4th: Lowest priority - most common, most conflicts
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
    return {
        k: v for k, v in WORD_REGISTRY.items()
        if v.word_type == word_type
    }