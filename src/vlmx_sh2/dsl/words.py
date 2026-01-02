"""
Word registry and models for VLMX DSL.

Defines all word types (actions, entities, fields, modifiers) and their
relationships to database models. The word registry serves as the vocabulary
foundation for natural language command parsing and validation.
"""

from typing import List, Dict
from ..models.words import (
    WordType, ActionCategory, CRUDOperation, ContextLevel,
    ActionWord, EntityWord, AttributeWord, Word
)
from ..models.schema.company import (
    CompanyEntity, 
    MetadataEntity, 
    BrandEntity, 
    OfferingEntity, 
    TargetEntity, 
    ValuesEntity
)

# Import dynamic handlers from the handlers module
from ..handlers.crud import (
    create_handler,
    add_handler,
    update_handler,
    show_handler,
    delete_handler
)
from ..handlers.navigation import navigate_handler


# ==================== WORD REGISTRATIONS ====================



# Define all words in a list
WORDS: List[Word] = [
    # ==================== ACTIONS ====================
    ActionWord(
        id="create",
        context=ContextLevel.SYS,
        description="Create a new entity (company, milestone, etc.)",
        aliases=["c","post"],
        handler=create_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.CREATE,
        database=True,
    ),
    
    ActionWord(
        id="delete",
        context=ContextLevel.SYS,
        description="Delete an existing entity",
        aliases=["d","remove","rm"],
        handler=delete_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.DELETE,
        database=True,        
        destructive=True,
        warning="This action will permanently delete the entity"
    ),
    
    ActionWord(
        id="cd",
        context=ContextLevel.SYS,  # Available from SYS level and up (all levels)
        description="Navigate between contexts (SYS, ORG, APP levels)",
        aliases=[],
        handler=navigate_handler,
        action_category=ActionCategory.NAVIGATION,
        crud_operation=CRUDOperation.NONE,
        requires_entity=False
    ),
    
    ActionWord(
        id="add",
        context=ContextLevel.ORG,
        description="Add or set attribute values to entities",
        aliases=["a","set"],
        handler=add_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.CREATE,
    ),
    
    ActionWord(
        id="update",
        context=ContextLevel.ORG,
        description="Update existing attribute values for entities",
        aliases=["u","put", "patch"],
        handler=update_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.UPDATE,
    ),
    
    ActionWord(
        id="show",
        context=ContextLevel.ORG,
        description="Display entity data or specific attributes",
        aliases=["s","read","get"],
        handler=show_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.READ        ,
    ),
    

    
    # ==================== ENTITIES ====================
   
    EntityWord(
        id="company",
        description="A business entity that can be managed in the terminal",
        entity_model=CompanyEntity        
    ),
    
    EntityWord(
        id="metadata",
        description="Key-value metadata for extending company information",
        entity_model=MetadataEntity
    ),
    
    EntityWord(
        id="brand",
        description="Company brand identity (vision, mission, personality)",
        entity_model=BrandEntity
    ),
    
    EntityWord(
        id="offering",
        description="Company product or service offerings",
        entity_model=OfferingEntity
    ),
    
    EntityWord(
        id="target",
        description="Target audience or market segments",
        entity_model=TargetEntity
    ),
    
    EntityWord(
        id="values",
        description="Company core values",
        entity_model=ValuesEntity
    ),
    
    # ==================== FIELDS ====================
    
    # Common fields across multiple entities
    
    AttributeWord(
        id="name",
        description="Name or title of the entity",
        entity_models=[CompanyEntity, BrandEntity, OfferingEntity, TargetEntity, ValuesEntity]
    ),
    
    AttributeWord(
        id="key",
        description="Key identifier or category",
        entity_models=[MetadataEntity, OfferingEntity, TargetEntity, ValuesEntity]
    ),
    
    AttributeWord(
        id="value",
        description="Value or description content",
        entity_models=[MetadataEntity, OfferingEntity, TargetEntity, ValuesEntity]
    ),
    
    # Company-specific fields
    AttributeWord(
        id="legal",
        description="Legal entity type (SA, LLC, INC, etc.)",   
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="type",
        description="Organization type (company, fund, foundation)",
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="currency",
        description="Currency used for financial data (EUR, USD, GBP, etc.)",
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="unit",
        description="Unit for financial data (THOUSANDS, MILLIONS, etc.)",
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="closing",
        description="Fiscal year end month (1-12)",
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="incorporation",
        description="Date of incorporation",
        entity_models=[CompanyEntity]
    ),
    
    # Brand-specific fields
    AttributeWord(
        id="vision",
        description="Company vision statement",
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="mission",
        description="Company mission statement",
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="personality",
        description="Brand personality description",
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="promise",
        description="Brand promise to customers",
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