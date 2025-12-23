# src/vlmx_sh2/words.py
"""
Word models for VLMX terminal.

Defines the structure for all word types:
- ActionWord: Actions like create, update, delete, show
- ModifierWord: Modifiers like holding, operating
- EntityWord: Entities like company, milestone
- AttributeWord: Attributes like name, currency, revenue
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Type, Optional, Literal, List, Dict
from .enums import WordType, OperationLevel, ActionCategory, CRUDOperation
from .entities import CompanyEntity


# ==================== BASE WORD ====================

class BaseWord(BaseModel):
    """
    Base word model - shared fields for all word types.
    """
    
    id: str = Field(description="Unique word identifier (e.g., 'create', 'company', 'currency')")
    description: str = Field(description="Human-readable description of the word")
    aliases: List[str] = Field(default_factory=list, description="Alternative names for this word (e.g., ['add', 'new'] for 'create')")
    abbreviations: List[str] = Field(default_factory=list, description="Short forms of the word (e.g., ['c'] for 'create')")
    deprecated: bool = Field(default=False, description="Whether this word is deprecated and should not be used")
    replaced_by: Optional[str] = Field(default=None, description="If deprecated, which word replaces this one")    
    model_config = ConfigDict(arbitrary_types_allowed=True)


# ==================== ACTION WORD ====================

class ActionWord(BaseWord):
    """
    Action word - represents commands like create, update, delete, show.
    """
    
    word_type: Literal[WordType.ACTION] = WordType.ACTION
    action_category: ActionCategory = Field(description="Broad category of what this action does (CRUD, NAVIGATION, SYSTEM, ANALYSIS, IMPORT_EXPORT)")
    crud_operation: CRUDOperation = Field(default=CRUDOperation.NONE, description="Specific CRUD operation type (only applicable if action_category=CRUD, otherwise use NONE)")
    operation_level: OperationLevel = Field(description="Level at which this action operates (database, table, row, query)")
    requires_entity: bool = Field(default=True, description="Whether this action requires an entity to operate on")
    destructive: bool = Field(default=False, description="Whether this action permanently destroys data (e.g., delete, drop)")
    warning: Optional[str] = Field(default=None, description="Warning message to display when using this word")


# ==================== MODIFIER WORD ====================

class ModifierWord(BaseWord):
    """
    Modifier word - modifies entity behavior like holding, operating.
    Could be used to change organization track (eg. operating or holding company)
    """
    
    word_type: Literal[WordType.MODIFIER] = WordType.MODIFIER
    applies_to: List[str] = Field(default_factory=list, description="Entity IDs this modifier can apply to (e.g., ['company'])")
    mutually_exclusive_with: List[str] = Field(default_factory=list, description="Other modifier IDs that cannot be used together with this one")


# ==================== ENTITY WORD ====================

class EntityWord(BaseWord):
    """
    Entity word - represents business entities like company, milestone.
    """
    
    word_type: Literal[WordType.ENTITY] = WordType.ENTITY
    entity_model: Type[BaseModel] = Field(description="Reference to the Pydantic model representing this entity")


# ==================== ATTRIBUTE WORD ====================

class AttributeWord(BaseWord):
    """
    Attribute word - represents entity attributes like name, currency, revenue.
    
    Can belong to multiple entities (e.g., 'name' exists on both Company and Milestone).
    """
    
    word_type: Literal[WordType.ATTRIBUTE] = WordType.ATTRIBUTE
    entity_models: List[Type[BaseModel]] = Field(description="Reference to the Pydantic model representing this entity")
    number_format_mode: str = Field(default="not_applicable", description="Number formatting mode for this attribute")
    currency_mode: str = Field(default="not_applicable", description="Currency mode for this attribute")
 

# ==================== UNION TYPE ====================

Word = ActionWord | EntityWord | AttributeWord | ModifierWord

# ==================== WORD REGISTRATIONS ====================



# Define all words in a list
WORDS: List[Word] = [
    # ==================== ACTIONS ====================
    ActionWord(
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
    
    ActionWord(
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
    EntityWord(
        id="company",
        description="A business entity that can be managed in the terminal",
        aliases=["business", "firm"],
        abbreviations=["co"],
        entity_model=CompanyEntity
    ),
    
    # ==================== ATTRIBUTES ====================
    AttributeWord(
        id="entity",
        description="Legal entity type (SA, LLC, INC, etc.)",
        aliases=["entity_type", "legal_entity"],
        abbreviations=["ent"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="currency",
        description="Currency used for financial data (EUR, USD, GBP, etc.)",
        aliases=["curr"],
        abbreviations=["cur"],
        entity_models=[CompanyEntity]
    ),
]

# Auto-build the registry from the list (NO REPETITION!)
WORD_REGISTRY: Dict[str, Word] = {
    word.id: word for word in WORDS
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