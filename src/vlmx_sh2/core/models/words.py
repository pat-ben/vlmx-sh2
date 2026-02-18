"""
Word models.

Defines pydantic models for word types (actions, schemas, fields) used in
the DSL vocabulary foundation. These models represent the structure and behavior
of different word categories in natural language command parsing.
"""

from enum import Enum
from typing import Any, List, Literal, Optional, Sequence, Type

from pydantic import BaseModel, ConfigDict, Field

from ..enums import ContextLevel, TypeOrg
from ..schemas.base import SchemaModel

# ==================== BASE WORD MODEL====================


class WordType(Enum):
    ACTION = "action"  # verbs only (eg. create, update, delete)
    SCHEMA = "schema"  # database-level operations (company, fund, holding, etc.)
    ENTITY = "entity"  # An entity is an Pydantic model which corresponds to a SQL table (eg. MetadataModel => metadata table)
    FIELD = "field"  # Pydantic model's fields which correspond to SQL table columns (eg. currency field => currency column)
    MODULE = "module"  # Entity groupings
    APP = "app"  # Views and tools


class BaseWord(BaseModel):
    """
    Base word model - shared fields for all word types.
    """

    id: str = Field(
        description="Unique word identifier (e.g., 'create', 'company', 'currency')"
    )
    description: str = Field(description="Human-readable description of the word")
    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative names for this word (e.g., ['del', 'rm'] for 'delete', ['org'] for 'organization')",
    )
    deprecated: bool = Field(
        default=False,
        description="Whether this word is deprecated and should not be used",
    )
    replaced_by: Optional[str] = Field(
        default=None, description="If deprecated, which word replaces this one"
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ==================== TARGET WORD MODEL ====================


class TargetWord(BaseWord):
    """
    Base class for all noun types (targets of actions).

    Separates verbs (ActionWord) from nouns (everything else).
    Provides shared fields like context level.

    Cumulative Context Model:
    - SYS: Schema only
    - ORG: Schema + Module + Entity + Field
    - APP: All targets (everything)
    """

    # NOTE: Kept broad for runtime and to avoid invariant override errors in subclasses
    # that narrow to Literal[WordType.*]. Concrete subclasses still set the actual value.
    word_type: Any

    context: ContextLevel = Field(
        default=ContextLevel.ORG,
        description="Context level where this target is available",
    )


# ==================== ACTION WORD MODEL ====================


class ActionCategory(str, Enum):
    """Broad category of what an action does."""

    CRUD = "crud"
    NAVIGATION = "navigation"
    SYSTEM = "system"
    ANALYSIS = "analysis"
    IMPORT_EXPORT = "import_export"


class CRUDOperation(str, Enum):
    """Specific CRUD operation type."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    NONE = "none"


class ExecutionType(str, Enum):
    STANDARD = "standard"  # Direct execution → result
    WIZARD = "wizard"  # Show widget → await input → execute


class ActionWord(BaseWord):
    """
    Action word - represents commands like create, update, delete, show.
    """

    # aliases field removed - now inherited from BaseWord
    word_type: Literal[WordType.ACTION] = WordType.ACTION
    execution_type: ExecutionType = Field(
        default=ExecutionType.STANDARD, description="Type of execution for this action"
    )
    handler: Any = Field(default=None, description="Function to handle this action")
    action_category: ActionCategory = Field(
        default=ActionCategory.CRUD,
        description="Broad category of what this action does (CRUD, NAVIGATION, SYSTEM, ANALYSIS, IMPORT_EXPORT)",
    )
    crud_operation: CRUDOperation = Field(
        default=CRUDOperation.NONE,
        description="Specific CRUD operation type (only applicable if action_category=CRUD, otherwise use NONE)",
    )
    destructive: bool = Field(
        default=False,
        description="Whether this action permanently destroys data (e.g., delete, drop)",
    )
    warning: Optional[str] = Field(
        default=None, description="Warning message to display when using this word"
    )
    standalone: bool = Field(
        default=False,
        description="Whether this command works independently without schema context (e.g., help, exit, cd .., cd ~)",
    )

    # requires_entity: bool = Field(default=True, description="Whether this action requires an entity to operate on")
    # database: bool = Field(default=False, description="Whether this action operates at the database level")


# ==================== SCHEMA WORD MODEL ====================


class SchemaWord(TargetWord):
    """
    Schema word - represents organization types for database creation.

    These trigger database-level operations: company, fund, holding, etc.
    Each SchemaWord maps to a TypeOrg value and a DatabaseModel schema class.
    """

    word_type: Literal[WordType.SCHEMA] = WordType.SCHEMA
    context: ContextLevel = Field(
        default=ContextLevel.SYS, description="Schemas only available at SYS level"
    )
    type_value: TypeOrg = Field(description="The TypeOrg enum value")
    schema_class: Type[SchemaModel] = Field(
        description="Database schema class for this org type"
    )


# ==================== ENTITY WORD MODEL ====================


class EntityWord(TargetWord):
    """
    Entity word - represents business schemas like company, milestone.
    """

    word_type: Literal[WordType.ENTITY] = WordType.ENTITY
    entity_model: Type[BaseModel] = Field(
        description="Reference to the Pydantic model representing this entity"
    )

    # wizard_widget: str | None = Field(default=None, description="Which Textual widget to use in wizard mode (e.g., 'form', 'table')")


# ==================== FIELD WORD MODEL ====================


class FieldWord(TargetWord):
    """
    Field word - represents entity fields like name, currency, revenue.

    Can belong to multiple schemas (e.g., 'name' exists on both Company and Milestone).
    """

    word_type: Literal[WordType.FIELD] = WordType.FIELD
    entity_models: Sequence[Type[BaseModel]] = Field(
        description="Reference to the Pydantic model representing this entity"
    )
    # number_format_mode: str = Field(default="not_applicable", description="Number formatting mode for this field")
    # currency_mode: str = Field(default="not_applicable", description="Currency mode for this field")


# ==================== MODULE WORD MODEL ====================


class ModuleWord(TargetWord):
    """
    Module word - represents logical groupings of entities.

    Examples: "core", "branding", "market"
    Modules group related entities for easier navigation and filtering.

    Available only in ORG context.
    """

    word_type: Literal[WordType.MODULE] = WordType.MODULE
    context: ContextLevel = Field(
        default=ContextLevel.ORG, description="Modules only available at ORG level"
    )
    entities: List[str] = Field(
        default_factory=list, description="Entity IDs belonging to this module"
    )


# ==================== VIEW WORD MODEL ====================


class ViewWord(TargetWord):
    """
    View word - represents report filters/templates.

    Examples: "neco", "investor", "duediligence"
    Views filter which entities are displayed together.

    Available only in APP context.
    """

    word_type: Literal[WordType.APP] = WordType.APP
    context: ContextLevel = Field(
        default=ContextLevel.APP, description="Views only available at APP level"
    )
    app_type: Literal["view"] = "view"
    name: str = Field(default="", description="Display name for UI rendering")
    entities: List[str] = Field(
        default_factory=list, description="Entity IDs this view displays"
    )
    schema_id: str = Field(
        default="company",
        description="Which schema type this view applies to (e.g. company, fund)",
    )


# ==================== TOOL WORD MODEL ====================


class ToolWord(TargetWord):
    """
    Tool word - represents calculation tools.

    Examples: "dcf", "captable", "forecast"
    Tools perform calculations with required parameters.

    Available only in APP context.
    """

    word_type: Literal[WordType.APP] = WordType.APP
    context: ContextLevel = Field(
        default=ContextLevel.APP, description="Tools only available at APP level"
    )
    app_type: Literal["tool"] = "tool"
    name: str = Field(default="", description="Display name for UI rendering")
    parameters: List[str] = Field(
        default_factory=list, description="Required input parameter names"
    )


# ==================== UNION TYPES ====================

# Union types for type checking
TargetWordUnion = SchemaWord | EntityWord | FieldWord | ModuleWord | ViewWord | ToolWord
Word = ActionWord | TargetWordUnion


# ==================== EXPORTS ====================

__all__ = [
    "WordType",
    "BaseWord",
    "TargetWord",
    "ActionWord",
    "SchemaWord",
    "EntityWord",
    "FieldWord",
    "ModuleWord",
    "ViewWord",
    "ToolWord",
    "Word",
    "TargetWordUnion",
    "ActionCategory",
    "CRUDOperation",
    "ExecutionType",
]
