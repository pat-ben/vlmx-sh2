# src/vlmx_sh2/keyword_models.py
"""
Keyword models for VLMX terminal.

Defines the structure for all keyword types:
- ActionKeyword: Actions like create, update, delete, show
- ModifierKeyword: Modifiers like holding, operating
- EntityKeyword: Entities like company, milestone
- AttributeKeyword: Attributes like name, currency, revenue
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Type, Optional, Literal, List, Tuple
from .enums import KeywordType, OperationLevel


# ==================== BASE KEYWORD ====================

class BaseKeyword(BaseModel):
    """
    Base keyword model - shared fields for all keyword types.
    """
    
    id: str = Field(description="Unique keyword identifier (e.g., 'create', 'company', 'currency')")
    description: str = Field(description="Human-readable description of the keyword")
    aliases: List[str] = Field(default_factory=list, description="Alternative names for this keyword (e.g., ['add', 'new'] for 'create')")
    abbreviations: List[str] = Field(default_factory=list, description="Short forms of the keyword (e.g., ['c'] for 'create')")
    deprecated: bool = Field(default=False, description="Whether this keyword is deprecated and should not be used")
    replaced_by: Optional[str] = Field(default=None, description="If deprecated, which keyword replaces this one")    
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ==================== ACTION KEYWORD ====================

class ActionKeyword(BaseKeyword):
    """
    Action keyword - represents commands like create, update, delete, show.
    """
    
    keyword_type: Literal[KeywordType.ACTION] = KeywordType.ACTION
    operation_level: OperationLevel = Field(description="Level at which this action operates (database, table, row, query)")
    requires_entity: bool = Field(default=True, description="Whether this action requires an entity to operate on")
    destructive: bool = Field(default=False, description="Whether this action permanently destroys data (e.g., delete, drop)")
    warning: Optional[str] = Field(default=None, description="Warning message to display when using this keyword")


# ==================== MODIFIER KEYWORD ====================

class ModifierKeyword(BaseKeyword):
    """
    Modifier keyword - modifies entity behavior like holding, operating.
    """
    
    keyword_type: Literal[KeywordType.MODIFIER] = KeywordType.MODIFIER
    applies_to: List[str] = Field(default_factory=list, description="Entity IDs this modifier can apply to (e.g., ['company'])")
    mutually_exclusive_with: List[str] = Field(default_factory=list, description="Other modifier IDs that cannot be used together with this one")


# ==================== ENTITY KEYWORD ====================

class EntityKeyword(BaseKeyword):
    """
    Entity keyword - represents business entities like company, milestone.
    """
    
    keyword_type: Literal[KeywordType.ENTITY] = KeywordType.ENTITY
    entity_model: Type[BaseModel] = Field(description="Reference to the Pydantic model representing this entity")


# ==================== ATTRIBUTE KEYWORD ====================

class AttributeKeyword(BaseKeyword):
    """
    Attribute keyword - represents entity attributes like name, currency, revenue.
    
    Can belong to multiple entities (e.g., 'name' exists on both Company and Milestone).
    """
    
    keyword_type: Literal[KeywordType.ATTRIBUTE] = KeywordType.ATTRIBUTE
    entity_models: List[Type[BaseModel]] = Field(description="Reference to the Pydantic model representing this entity")
 

# ==================== UNION TYPE ====================

Keyword = ActionKeyword | EntityKeyword | AttributeKeyword | ModifierKeyword