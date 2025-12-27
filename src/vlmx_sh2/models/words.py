"""
Word models for VLMX DSL.

Defines pydantic models for word types (actions, entities, attributes) used in
the DSL vocabulary foundation. These models represent the structure and behavior
of different word categories in natural language command parsing.
"""

from pydantic import BaseModel, Field, ConfigDict
from enum import Enum, IntEnum
from typing import Type, Optional, Literal, List, Any


# ==================== BASE WORD MODEL====================

class WordType(Enum):
    ACTION = "action"  # verbs only (eg. create, update, delete)
    ENTITY = "entity"  # noun only :An entity is an Pydantic model which corresponds to a SQL table (eg. MetadataModel => metadata table)
    FIELD = "field"  # noun or adjective: Pydantic model's fields which correspond to SQL table columns (eg. currency field => currency column)
    
class ContextLevel(IntEnum):
    SYS = 0 # system / root level
    ORG = 1 # organization level (most of the time company)
    APP = 2 # application level (could be plugin)


class BaseWord(BaseModel):
    """
    Base word model - shared fields for all word types.
    """
    
    id: str = Field(description="Unique word identifier (e.g., 'create', 'company', 'currency')")
    context: ContextLevel = Field(default=ContextLevel.SYS, description="Minimum context level required: SYS(0), ORG(1), or APP(2)")
    description: str = Field(description="Human-readable description of the word")
    aliases: List[str] = Field(default_factory=list, description="Alternative names for this word (e.g., ['add', 'new'] for 'create')")
    deprecated: bool = Field(default=False, description="Whether this word is deprecated and should not be used")
    replaced_by: Optional[str] = Field(default=None, description="If deprecated, which word replaces this one")    
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ==================== ACTION WORD MODEL ====================

class ActionCategory(str, Enum):
    """ Broad category of what an action does. """
    CRUD = "crud"
    NAVIGATION = "navigation"
    SYSTEM = "system"
    ANALYSIS = "analysis"
    IMPORT_EXPORT = "import_export"

class CRUDOperation(str, Enum):
    """ Specific CRUD operation type."""    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    NONE = "none"


class ActionWord(BaseWord):
    """
    Action word - represents commands like create, update, delete, show.
    """
    
    word_type: Literal[WordType.ACTION] = WordType.ACTION
    handler: Any = Field(description="Function to handle this action")
    action_category: ActionCategory = Field(description="Broad category of what this action does (CRUD, NAVIGATION, SYSTEM, ANALYSIS, IMPORT_EXPORT)")
    crud_operation: CRUDOperation = Field(default=CRUDOperation.NONE, description="Specific CRUD operation type (only applicable if action_category=CRUD, otherwise use NONE)")
    database: bool = Field(default=False, description="Whether this action operates at the database level")
    requires_entity: bool = Field(default=True, description="Whether this action requires an entity to operate on")
    destructive: bool = Field(default=False, description="Whether this action permanently destroys data (e.g., delete, drop)")
    warning: Optional[str] = Field(default=None, description="Warning message to display when using this word")


# ==================== ENTITY WORD MODEL ====================

class EntityWord(BaseWord):
    """
    Entity word - represents business entities like company, milestone.
    """
    
    word_type: Literal[WordType.ENTITY] = WordType.ENTITY
    entity_model: Type[BaseModel] = Field(description="Reference to the Pydantic model representing this entity")
    wizard_widget: str | None = Field(default=None, description="Which Textual widget to use in wizard mode (e.g., 'form', 'table')")


# ==================== ATTRIBUTE WORD MODEL ====================

class AttributeWord(BaseWord):
    """
    Attribute word - represents entity attributes like name, currency, revenue.
    
    Can belong to multiple entities (e.g., 'name' exists on both Company and Milestone).
    """
    
    word_type: Literal[WordType.FIELD] = WordType.FIELD
    entity_models: List[Type[BaseModel]] = Field(description="Reference to the Pydantic model representing this entity")
    number_format_mode: str = Field(default="not_applicable", description="Number formatting mode for this attribute")
    currency_mode: str = Field(default="not_applicable", description="Currency mode for this attribute")
 

# ==================== UNION TYPE ====================

Word = ActionWord | EntityWord | AttributeWord