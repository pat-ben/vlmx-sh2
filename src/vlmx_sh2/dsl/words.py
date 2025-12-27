"""
Word registry and models for VLMX DSL.

Defines all word types (actions, entities, attributes, modifiers) and their
relationships to database models. The word registry serves as the vocabulary
foundation for natural language command parsing and validation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Type, Optional, Literal, List, Dict, Callable
from ..core.enums import WordType, OperationLevel, ActionCategory, CRUDOperation, ContextLevel
from ..core.models.entities import (
    CompanyEntity, 
    MetadataEntity, 
    BrandEntity, 
    OfferingEntity, 
    TargetEntity, 
    ValueEntity
)


# ==================== BASE WORD ====================

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


# ==================== ACTION WORD ====================

class ActionWord(BaseWord):
    """
    Action word - represents commands like create, update, delete, show.
    """
    
    word_type: Literal[WordType.ACTION] = WordType.ACTION
    handler: Callable[[ActionWord, List[str]], None] = Field(description="Function to handle this action")
    action_category: ActionCategory = Field(description="Broad category of what this action does (CRUD, NAVIGATION, SYSTEM, ANALYSIS, IMPORT_EXPORT)")
    crud_operation: CRUDOperation = Field(default=CRUDOperation.NONE, description="Specific CRUD operation type (only applicable if action_category=CRUD, otherwise use NONE)")
    database: bool = Field(default=False, description="Whether this action operates at the database level")
    requires_entity: bool = Field(default=True, description="Whether this action requires an entity to operate on")
    destructive: bool = Field(default=False, description="Whether this action permanently destroys data (e.g., delete, drop)")
    warning: Optional[str] = Field(default=None, description="Warning message to display when using this word")


# ==================== ENTITY WORD ====================

class EntityWord(BaseWord):
    """
    Entity word - represents business entities like company, milestone.
    """
    
    word_type: Literal[WordType.ENTITY] = WordType.ENTITY
    entity_model: Type[BaseModel] = Field(description="Reference to the Pydantic model representing this entity")
    wizard_widget: str | None = Field(default=None, description="Which Textual widget to use in wizard mode (e.g., 'form', 'table')")


# ==================== ATTRIBUTE WORD ====================

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

# ==================== WORD REGISTRATIONS ====================



# Define all words in a list
WORDS: List[Word] = [
    # ==================== ACTIONS ====================
    ActionWord(
        id="create",
        context=ContextLevel.SYS,
        description="Create a new entity (company, milestone, etc.)",
        aliases=["initialize","init", "new","c"],
        handler=create_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.CREATE,
        database=True,
    ),
    
    ActionWord(
        id="delete",
        context=ContextLevel.SYS,
        description="Delete an existing entity",
        aliases=["remove", "drop","d","rm"],
        handler=delete_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.DELETE,
        database=True,        
        destructive=True,
        warning="This action will permanently delete the entity"
    ),
    
    ActionWord(
        id="cd",
        context=ContextLevel.SYS,
        description="Navigate between contexts (SYS, ORG levels)",
        aliases=["navigate", "goto","change","nav"],
        handler=navigate_handler,
        action_category=ActionCategory.NAVIGATION,
        crud_operation=CRUDOperation.NONE,
        requires_entity=False
    ),
    
    ActionWord(
        id="add",
        context=ContextLevel.ORG,
        description="Add or set attribute values to entities",
        aliases=["set", "assign","a"],
        handler=add_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.CREATE,
    ),
    
    ActionWord(
        id="update",
        context=ContextLevel.ORG,
        description="Update existing attribute values for entities",
        aliases=["modify", "change","u"],
        handler=update_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.UPDATE,
    ),
    
    ActionWord(
        id="show",
        description="Display entity data or specific attributes",
        aliases=["display", "view", "get","read","s"],
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.READ,
        operation_level=OperationLevel.QUERY,
        requires_entity=False,  # Entity is optional, defaults to organization
        destructive=False,
    ),
    

    
    # ==================== ENTITIES ====================
    EntityWord(
        id="company",
        description="A business entity that can be managed in the terminal",
        aliases=["business", "firm"],
        abbreviations=["co"],
        entity_model=CompanyEntity
    ),
    
    EntityWord(
        id="metadata",
        description="Key-value metadata for extending company information",
        aliases=["meta", "info"],
        abbreviations=["md"],
        entity_model=MetadataEntity
    ),
    
    EntityWord(
        id="brand",
        description="Company brand identity (vision, mission, personality)",
        aliases=["branding", "identity"],
        abbreviations=["br"],
        entity_model=BrandEntity
    ),
    
    EntityWord(
        id="offering",
        description="Company product or service offerings",
        aliases=["product", "service"],
        abbreviations=["off"],
        entity_model=OfferingEntity
    ),
    
    EntityWord(
        id="target",
        description="Target audience or market segments",
        aliases=["audience", "segment"],
        abbreviations=["tgt"],
        entity_model=TargetEntity
    ),
    
    EntityWord(
        id="value",
        description="Company core values",
        aliases=["values", "principles"],
        abbreviations=["val"],
        entity_model=ValueEntity
    ),
    
    # ==================== ATTRIBUTES ====================
    
    # Common attributes across multiple entities
    AttributeWord(
        id="name",
        description="Name or title of the entity",
        aliases=["title"],
        abbreviations=["n"],
        entity_models=[CompanyEntity, BrandEntity, OfferingEntity, TargetEntity, ValueEntity]
    ),
    
    AttributeWord(
        id="key",
        description="Key identifier or category",
        aliases=["category", "type"],
        abbreviations=["k"],
        entity_models=[MetadataEntity, OfferingEntity, TargetEntity, ValueEntity]
    ),
    
    AttributeWord(
        id="value",
        description="Value or description content",
        aliases=["description", "content"],
        abbreviations=["v"],
        entity_models=[MetadataEntity, OfferingEntity, TargetEntity, ValueEntity]
    ),
    
    # Company-specific attributes
    AttributeWord(
        id="entity",
        description="Legal entity type (SA, LLC, INC, etc.)",
        aliases=["entity_type", "legal_entity"],
        abbreviations=["ent"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="type",
        description="Organization type (company, fund, foundation)",
        aliases=["org_type", "organization_type"],
        abbreviations=["typ"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="currency",
        description="Currency used for financial data (EUR, USD, GBP, etc.)",
        aliases=["curr"],
        abbreviations=["cur"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="unit",
        description="Unit for financial data (THOUSANDS, MILLIONS, etc.)",
        aliases=["financial_unit"],
        abbreviations=["u"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="closing",
        description="Fiscal year end month (1-12)",
        aliases=["fiscal_month", "fiscal_year_end"],
        abbreviations=["cl"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="incorporation",
        description="Date of incorporation",
        aliases=["incorporation_date", "founded"],
        abbreviations=["inc"],
        entity_models=[CompanyEntity]
    ),
    
    # Brand-specific attributes
    AttributeWord(
        id="vision",
        description="Company vision statement",
        aliases=["vision_statement"],
        abbreviations=["vis"],
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="mission",
        description="Company mission statement",
        aliases=["mission_statement"],
        abbreviations=["mis"],
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="personality",
        description="Brand personality description",
        aliases=["brand_personality"],
        abbreviations=["per"],
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="promise",
        description="Brand promise to customers",
        aliases=["brand_promise"],
        abbreviations=["prom"],
        entity_models=[BrandEntity]
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