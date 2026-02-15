"""
Automatic word generation from database schemas.

This module implements the auto-generation of EntityWord and FieldWord objects
from database schemas definitions at runtime, eliminating manual duplication
between database models and DSL word registrations.
"""

from collections import defaultdict
from typing import Dict, List, Type

from ...core.enums.core import ContextLevel
from ...core.enums.forms import TypeOrg
from ...core.models.words import (
    EntityWord,
    FieldWord,
    ModuleWord,
    SchemaWord,
    ToolWord,
    ViewWord,
)
from ...core.schemas.base import EntityModel, SchemaModel


def generate_schema_words() -> Dict[str, SchemaWord]:
    """Generate SchemaWord objects for all organization types."""
    from ...core.schemas.company import CompanyDatabase

    schema_words = {}

    # Company schema
    schema_words["company"] = SchemaWord(
        id="company",
        description="Company organization type",
        aliases=["co"],  # ADD THIS
        type_value=TypeOrg.COMPANY,
        schema_class=CompanyDatabase,
    )

    # Future schemas can be added here:
    # schema_words["fund"] = SchemaWord(
    #     id="fund",
    #     description="Fund organization type",
    #     aliases=["f"],
    #     type_value=TypeOrg.FUND,
    #     schema_class=FundDatabase
    # )

    return schema_words


def generate_entity_words(schema: Type[SchemaModel]) -> Dict[str, EntityWord]:
    """
    Generate EntityWord objects from database schema's entity models.

    Args:
        schema: Database schema class (e.g., CompanyDatabase)

    Returns:
        Dictionary of entity_id → EntityWord
    """
    entity_words = {}

    for entity_cls in schema.tables:
        # Get aliases if entity defines them
        # NOTE: Aliases can be added via get_entity_aliases() class method
        # Example: OrganizationEntity.get_entity_aliases() → ["org", "o"]
        aliases = []
        if hasattr(entity_cls, "get_entity_aliases"):
            aliases = entity_cls.get_entity_aliases()

        entity_words[entity_cls.get_entity_word_id()] = EntityWord(
            id=entity_cls.get_entity_word_id(),
            description=entity_cls.get_entity_description(),
            aliases=aliases,  # Pass aliases
            context=entity_cls.context,
            entity_model=entity_cls,
        )

    return entity_words


def generate_field_words(schema: Type[SchemaModel]) -> Dict[str, FieldWord]:
    """
    Generate FieldWord objects from entity model fields.

    Args:
        schema: Database schema class

    Returns:
        Dictionary of field_name → FieldWord
    """
    # Group schemas by field name
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
        # NOTE: Field aliases could be defined in field metadata in the future
        # For now, no automatic aliases for fields
        aliases = []

        # If field appears in multiple schemas, use generic description
        if len(entities) > 1:
            description = f"{field_name.capitalize()} (common to multiple schemas)"
        else:
            description = field_to_descriptions[field_name]

        field_words[field_name] = FieldWord(
            id=field_name,
            description=description,
            aliases=aliases,  # Empty for now, ready for future use
            entity_models=entities,
        )

    return field_words


def generate_module_words(schema: Type[SchemaModel]) -> Dict[str, ModuleWord]:
    """
    Generate ModuleWord objects by grouping entities by their module ClassVar.

    Modules are available only in ORG context.

    Args:
        schema: Database schema class (e.g., CompanyDatabase)

    Returns:
        Dictionary of module_id → ModuleWord
    """
    from collections import defaultdict

    # Group entities by module
    module_entities: Dict[str, List[str]] = defaultdict(list)

    for entity_cls in schema.tables:
        module_name = getattr(entity_cls, "module", "core")
        entity_id = entity_cls.get_entity_word_id()
        module_entities[module_name].append(entity_id)

    # Build ModuleWords
    module_words = {}
    for module_name, entity_ids in module_entities.items():
        module_words[module_name] = ModuleWord(
            id=module_name,
            description=f"Module containing: {', '.join(entity_ids)}",
            context=ContextLevel.ORG,
            entities=entity_ids,
        )

    return module_words


def generate_view_words() -> Dict[str, ViewWord]:
    """
    Generate ViewWord objects from manual definitions.

    Views are available only in APP context.
    """
    from .views import VIEW_WORDS_LIST

    return {view.id: view for view in VIEW_WORDS_LIST}


def generate_tool_words() -> Dict[str, ToolWord]:
    """
    Generate ToolWord objects from manual definitions.

    Tools are available only in APP context.
    """
    from .tools import TOOL_WORDS_LIST

    return {tool.id: tool for tool in TOOL_WORDS_LIST}
