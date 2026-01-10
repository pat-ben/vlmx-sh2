"""
Automatic word generation from database schemas.

This module implements the auto-generation of EntityWord and FieldWord objects
from database entities definitions at runtime, eliminating manual duplication
between database models and DSL word registrations.
"""

from collections import defaultdict
from typing import Dict, List, Type

from ...models.entities.base import DatabaseModel, EntityModel
from ...models.words import EntityWord, FieldWord, Word


def generate_entity_words(schema: Type[DatabaseModel]) -> Dict[str, EntityWord]:
    """
    Generate EntityWord objects from entities.

    Args:
        schema: Database entities containing entity definitions

    Returns:
        Dictionary mapping entity word IDs to EntityWord objects
    """
    entity_words = {}

    for entity_cls in schema.tables:
        word_id = entity_cls.get_entity_word_id()
        description = entity_cls.get_entity_description()
        context = entity_cls.context

        entity_word = EntityWord(
            id=word_id,
            description=description,
            context=context,
            entity_model=entity_cls,
        )

        entity_words[word_id] = entity_word

    return entity_words


# File: D:\Code\vlmx-sh2\src\vlmx_sh2\dsl\words\generator.py

def generate_field_words(schema: Type[DatabaseModel]) -> Dict[str, FieldWord]:
    """
    Generate FieldWord objects from entity fields.

    Aggregates fields by name across all entities, creating one FieldWord
    per unique field name that references all entities containing that field.
    
    For fields appearing in multiple entities, uses a generic description
    to indicate the field is shared across entities.

    Args:
        schema: Database entities containing entity definitions

    Returns:
        Dictionary mapping field word IDs to FieldWord objects
    """
    # Group entities by field name
    field_to_entities: Dict[str, List[Type[EntityModel]]] = defaultdict(list)
    field_to_descriptions: Dict[str, str] = {}

    # Process each entity class in the schema
    for entity_cls in schema.tables:
        # Get system fields once per entity (includes auto-detected foreign keys)
        system_fields = entity_cls.get_all_system_fields()
        
        # Process each field in the entity
        for field_name, field_info in entity_cls.model_fields.items():
            # Skip system fields (id, created_at, updated_at, *_id, etc.)
            if field_name in system_fields:
                continue
            
            # Add entity to field mapping
            field_to_entities[field_name].append(entity_cls)
            
            # Extract field description (only once per field name - first wins)
            if field_name not in field_to_descriptions:
                # Pydantic v2: description is directly on field_info
                field_description = field_info.description or ""
                
                field_to_descriptions[field_name] = (
                    field_description or f"Field '{field_name}'"
                )

    # Create FieldWord objects
    field_words = {}

    for field_name, entities in field_to_entities.items():
        # If field appears in multiple entities, use generic description
        if len(entities) > 1:
            description = f"{field_name.capitalize()} (common to multiple entities)"
        else:
            description = field_to_descriptions[field_name]

        field_word = FieldWord(
            id=field_name,
            description=description,
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