"""
Automatic word generation from database schemas.

This module implements the auto-generation of EntityWord and FieldWord objects
from database schemas definitions at runtime, eliminating manual duplication
between database models and DSL word registrations.
"""

from collections import defaultdict
from typing import Dict, List, Type

from ...core.enums.core import ContextLevel
from ...core.models.words import (
    EntityWord,
    FieldWord,
    ModuleWord,
    SchemaWord,
    ToolWord,
    ViewWord,
)
from ...core.schemas.base import EntityModel


def generate_schema_words() -> Dict[str, SchemaWord]:
    """Generate SchemaWord objects from the core registry."""
    from ...core.registry import get_all_schema_configs

    schema_words = {}
    for config in get_all_schema_configs():
        schema_words[config.schema_id] = SchemaWord(
            id=config.schema_id,
            description=config.description,
            aliases=config.aliases,
            type_value=config.org_type,
            schema_class=config.schema_class,
        )

    return schema_words


def generate_entity_words(schema_id: str) -> Dict[str, EntityWord]:
    """
    Generate EntityWord objects from registry entity list.

    Args:
        schema_id: Schema identifier (e.g., "company")

    Returns:
        Dictionary of entity_id → EntityWord
    """
    from ...core.registry import get_entities_for_schema

    entity_words = {}

    for entity_cls in get_entities_for_schema(schema_id):
        aliases = []
        if hasattr(entity_cls, "get_entity_aliases"):
            aliases = entity_cls.get_entity_aliases()

        entity_words[entity_cls.get_entity_word_id()] = EntityWord(
            id=entity_cls.get_entity_word_id(),
            description=entity_cls.get_entity_description(),
            aliases=aliases,
            context=entity_cls.context,
            entity_model=entity_cls,
        )

    return entity_words


def generate_field_words(schema_id: str) -> Dict[str, FieldWord]:
    """
    Generate FieldWord objects from entity model fields.

    Args:
        schema_id: Schema identifier (e.g., "company")

    Returns:
        Dictionary of field_name → FieldWord
    """
    from ...core.registry import get_entities_for_schema

    # Group entities by field name
    field_to_entities: Dict[str, List[Type[EntityModel]]] = defaultdict(list)
    field_to_descriptions: Dict[str, str] = {}

    for entity_cls in get_entities_for_schema(schema_id):
        system_fields = entity_cls.get_all_system_fields()

        for field_name, field_info in entity_cls.model_fields.items():
            if field_name in system_fields:
                continue

            field_to_entities[field_name].append(entity_cls)

            if field_name not in field_to_descriptions:
                field_description = field_info.description or ""
                field_to_descriptions[field_name] = (
                    field_description or f"Field '{field_name}'"
                )

    field_words = {}

    for field_name, entities in field_to_entities.items():
        aliases = []

        if len(entities) > 1:
            description = f"{field_name.capitalize()} (common to multiple schemas)"
        else:
            description = field_to_descriptions[field_name]

        field_words[field_name] = FieldWord(
            id=field_name,
            description=description,
            aliases=aliases,
            entity_models=entities,
        )

    return field_words


def generate_module_words(schema_id: str) -> Dict[str, ModuleWord]:
    """
    Generate ModuleWord objects by grouping entities by their module ClassVar.

    Args:
        schema_id: Schema identifier (e.g., "company")

    Returns:
        Dictionary of module_id → ModuleWord
    """
    from collections import defaultdict
    from ...core.registry import get_entities_for_schema

    module_entities: Dict[str, List[str]] = defaultdict(list)

    for entity_cls in get_entities_for_schema(schema_id):
        module_name = getattr(entity_cls, "module", "core")
        entity_id = entity_cls.get_entity_word_id()
        module_entities[module_name].append(entity_id)

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
    Generate ViewWord objects from TOML configuration files.

    Views are available only in APP context.
    """
    from importlib.resources import files
    from pathlib import Path
    from .view_loader import load_views_from_directory

    views_dir = Path(str(files("vlmx_sh2.shell.app") / "views"))
    views = load_views_from_directory(views_dir)
    return {view.id: view for view in views}


def generate_tool_words() -> Dict[str, ToolWord]:
    """
    Generate ToolWord objects from TOML configuration files.

    Tools are available only in APP context.
    """
    from importlib.resources import files
    from pathlib import Path
    from .tool_loader import load_tools_from_directory

    tools_dir = Path(str(files("vlmx_sh2.shell.app") / "tools"))
    tools = load_tools_from_directory(tools_dir)
    return {tool.id: tool for tool in tools}
