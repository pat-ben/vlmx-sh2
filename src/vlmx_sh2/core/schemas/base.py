"""
Base classes for database schemas and models.

Defines common base classes that all database schemas and entity models inherit from.
Provides shared functionality for table naming, configuration, and schemas organization.
"""

import re
from typing import ClassVar, List, Set, Type

from pydantic import ConfigDict
from sqlmodel import SQLModel

from ..enums import Cardinality, ContextLevel

# ============================================
# BASE MODEL
# ============================================


class EntityModel(SQLModel):
    """Base class for all entity (= table) models"""

    # Entity cardinality classification
    cardinality: ClassVar[Cardinality] = Cardinality.SINGLE
    context: ClassVar[ContextLevel] = ContextLevel.ORG
    module: ClassVar[str] = "core"  # Default module grouping

    # ==================== DEFAULT SYSTEM FIELDS ====================
    # These fields are excluded from word registry by default
    _system_fields: ClassVar[Set[str]] = {
        "id",
        "created_at",
        "updated_at",
        "source_db",
        "last_synced_at",
    }

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)  # pyright: ignore[reportAssignmentType]

    # ==================== CLASS METHODS ====================

    @classmethod
    def get_entity_word_id(cls) -> str:
        """
        Auto-derive word ID from class name.
        OrganizationEntity → 'organization'
        NewsEntity → 'news'
        BrandEntity → 'brand'
        """
        return cls.__name__.replace("Entity", "").lower()

    @classmethod
    def get_entity_aliases(cls) -> List[str]:
        """
        Get word aliases for this entity.
        Override in subclasses to provide custom aliases.

        Returns:
            List of alias words that map to this entity
        """
        return []

    @classmethod
    def get_entity_description(cls) -> str:
        """Get entity description from docstring."""
        return cls.__doc__.strip() if cls.__doc__ else ""

    @classmethod
    def get_all_system_fields(cls) -> Set[str]:
        """Get system fields including auto-detected foreign keys."""
        system_fields = cls._system_fields.copy()

        # Auto-detect foreign keys
        for field_name in cls.model_fields.keys():
            if re.match(r".*_id$", field_name):
                system_fields.add(field_name)

        return system_fields

    @classmethod
    def table_name(cls) -> str:
        """
        Returns the SQL table name for this model.

        Default implementation uses the same logic as get_entity_word_id().
        Subclasses can override this for custom table naming (e.g., "brand_offerings").
        """
        return cls.__name__.replace("Entity", "").lower()


# ============================================
# SCHEMA / DATABASE MODEL
# ============================================


class SchemaModel(SQLModel):
    """Base class for database schemas"""

    name: str
    description: str
    tables: ClassVar[List[Type[EntityModel]]] = []
