"""
Word registry and models.

Auto-generates EntityWord and FieldWord objects from database entities definitions
while maintaining manual ActionWord definitions. This eliminates duplication
between database models and DSL word registrations.
"""

from typing import Dict

from ...models.words import WordType, Word
from .generator import generate_schema_words
from .actions import ACTION_WORDS
from ...models.entities.company import CompanyDatabase


# ==================== AUTO-GENERATED WORD REGISTRY ====================

# List of all database schemas to include in the word registry
SCHEMAS = [
    CompanyDatabase,
    # Add more database schemas here as they are created:
    # FundDatabase,
    # HoldingDatabase,
]

# Auto-generate entity and field words from all schemas
SCHEMA_WORDS = {}
for schema in SCHEMAS:
    schema_words = generate_schema_words(schema)
    SCHEMA_WORDS.update(schema_words)  # Later schemas override earlier ones if conflicts exist

# Convert action list to dict
ACTION_WORD_DICT = {word.id: word for word in ACTION_WORDS}

# Combine into final registry
WORD_REGISTRY: Dict[str, Word] = {
    **SCHEMA_WORDS,      # Auto-generated EntityWords and FieldWords
    **ACTION_WORD_DICT,  # Manual ActionWords
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