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
from typing import Type, Optional, Literal, List, Dict
from .enums import KeywordType, OperationLevel, ActionCategory, CRUDOperation
from .models import CompanyModel


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
    action_category: ActionCategory = Field(description="Broad category of what this action does (CRUD, NAVIGATION, SYSTEM, ANALYSIS, IMPORT_EXPORT)")
    crud_operation: CRUDOperation = Field(default=CRUDOperation.NONE, description="Specific CRUD operation type (only applicable if action_category=CRUD, otherwise use NONE)")
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

# ==================== KEYWORD REGISTRATIONS ====================



# Define all keywords in a list
KEYWORDS: List[Keyword] = [
    # ==================== ACTIONS ====================
    ActionKeyword(
        id="create",
        description="Create a new entity (company, milestone, etc.)",
        aliases=["add", "new"],
        abbreviations=["c"],
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.CREATE,
        operation_level=OperationLevel.TABLE,
        requires_entity=True,
        destructive=False,
    ),
    
    ActionKeyword(
        id="delete",
        description="Delete an existing entity",
        aliases=["remove", "drop"],
        abbreviations=["d"],
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.DELETE,
        operation_level=OperationLevel.ROW,
        requires_entity=True,
        destructive=True,
        warning="This action will permanently delete the entity"
    ),
    
    # ==================== ENTITIES ====================
    EntityKeyword(
        id="company",
        description="A business entity that can be managed in the terminal",
        aliases=["business", "firm"],
        abbreviations=["co"],
        entity_model=CompanyModel
    ),
    
    # ==================== ATTRIBUTES ====================
    AttributeKeyword(
        id="entity",
        description="Legal entity type (SA, LLC, INC, etc.)",
        aliases=["entity_type", "legal_entity"],
        abbreviations=["ent"],
        entity_models=[CompanyModel]
    ),
    
    AttributeKeyword(
        id="currency",
        description="Currency used for financial data (EUR, USD, GBP, etc.)",
        aliases=["curr"],
        abbreviations=["cur"],
        entity_models=[CompanyModel]
    ),
]

# Auto-build the registry from the list (NO REPETITION!)
KEYWORD_REGISTRY: Dict[str, Keyword] = {
    keyword.id: keyword for keyword in KEYWORDS
}


# ==================== HELPER FUNCTIONS ====================

def get_keyword(keyword_id: str) -> Keyword | None:
    """Get a keyword by its ID"""
    return KEYWORD_REGISTRY.get(keyword_id)


def get_all_keywords() -> Dict[str, Keyword]:
    """Get all registered keywords"""
    return KEYWORD_REGISTRY


def get_keywords_by_type(keyword_type: KeywordType) -> Dict[str, Keyword]:
    """Get all keywords of a specific type"""
    return {
        k: v for k, v in KEYWORD_REGISTRY.items()
        if v.keyword_type == keyword_type
    }