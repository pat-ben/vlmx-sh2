"""
Automatic word generation from database schemas.

This module implements the auto-generation of EntityWord and FieldWord objects
from database entities definitions at runtime, eliminating manual duplication
between database models and DSL word registrations.
"""

from collections import defaultdict
from typing import Dict, List, Set, Type

from ...models.context import ContextLevel
from ...models.entities.base import DatabaseModel, EntityModel
from ...models.words import EntityWord, FieldWord, Word


def generate_entity_words(schema: Type[DatabaseModel]) -> Dict[str, EntityWord]:
    """
    Generate EntityWord objects from entities entities.

    Args:
        schema: Database entities containing entity definitions

    Returns:
        Dictionary mapping entity word IDs to EntityWord objects
    """
    entity_words = {}

    for entity_cls in schema.tables:
        if not issubclass(entity_cls, EntityModel):
            continue

        word_id = entity_cls.get_entity_word_id()
        description = entity_cls.get_entity_description()
        context = getattr(entity_cls, "context", ContextLevel.ORG)

        entity_word = EntityWord(
            id=word_id,
            description=description,
            context=context,
            entity_model=entity_cls,
        )

        entity_words[word_id] = entity_word

    return entity_words


def generate_field_words(schema: Type[DatabaseModel]) -> Dict[str, FieldWord]:
    """
    Generate FieldWord objects from entities entity fields.

    Aggregates fields by name across all entities, creating one FieldWord
    per unique field name that references all entities containing that field.

    Args:
        schema: Database entities containing entity definitions

    Returns:
        Dictionary mapping field word IDs to FieldWord objects
    """
    # Group entities by field name
    field_to_entities: Dict[str, List[Type[EntityModel]]] = defaultdict(list)
    field_to_descriptions: Dict[str, str] = {}
    field_to_contexts: Dict[str, List[ContextLevel]] = defaultdict(list)

    for entity_cls in schema.tables:
        if not issubclass(entity_cls, EntityModel):
            continue

        # Get system fields to exclude
        system_fields = entity_cls.get_all_system_fields()
        entity_context = getattr(entity_cls, "context", ContextLevel.ORG)

        # Process each field in the entity
        for field_name, field_info in entity_cls.model_fields.items():
            # Skip system fields
            if field_name in system_fields:
                continue

            # Add entity to field mapping
            field_to_entities[field_name].append(entity_cls)
            field_to_contexts[field_name].append(entity_context)

            # Extract field description
            if field_name not in field_to_descriptions:
                field_description = ""
                if hasattr(field_info, "description") and field_info.description:
                    field_description = field_info.description
                elif hasattr(field_info, "field_info") and hasattr(
                    field_info.field_info, "description"
                ):
                    field_description = field_info.field_info.description or ""

                field_to_descriptions[field_name] = (
                    field_description or f"Field '{field_name}'"
                )

    # Create FieldWord objects
    field_words = {}

    for field_name, entities in field_to_entities.items():
        description = field_to_descriptions[field_name]
        contexts = field_to_contexts[field_name]

        # Use minimum context level across all entities with this field
        min_context = min(contexts) if contexts else ContextLevel.ORG

        field_word = FieldWord(
            id=field_name,
            description=description,
            context=min_context,
            entity_models=entities,
        )

        field_words[field_name] = field_word

    return field_words


def generate_schema_words(schema: Type[DatabaseModel]) -> Dict[str, Word]:
    """
    Generate all EntityWord and FieldWord objects from a database entities.

    Args:
        schema: Database entities containing entity definitions

    Returns:
        Dictionary mapping word IDs to Word objects (EntityWords + FieldWords)
    """
    entity_words = generate_entity_words(schema)
    field_words = generate_field_words(schema)

    # Combine into single dictionary, with EntityWords taking precedence over FieldWords
    # This handles naming conflicts where an entity name matches a field name
    all_words = {}
    all_words.update(field_words)  # Add field words first
    all_words.update(entity_words)  # Add entity words second (overwrites conflicts)

    return all_words