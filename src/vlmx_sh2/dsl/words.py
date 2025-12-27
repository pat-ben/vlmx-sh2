"""
Word registry and models for VLMX DSL.

Defines all word types (actions, entities, attributes, modifiers) and their
relationships to database models. The word registry serves as the vocabulary
foundation for natural language command parsing and validation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Type, Optional, Literal, List, Dict, Any, Callable
from ..core.enums import WordType, ActionCategory, CRUDOperation, ContextLevel
from ..core.models.entities import (
    CompanyEntity, 
    MetadataEntity, 
    BrandEntity, 
    OfferingEntity, 
    TargetEntity, 
    ValuesEntity
)

# Forward declarations for handlers - will be imported after registry is built
create_handler: Optional[Callable] = None
delete_handler: Optional[Callable] = None
navigate_handler: Optional[Callable] = None
add_handler: Optional[Callable] = None
update_handler: Optional[Callable] = None
show_handler: Optional[Callable] = None

# ==================== SHORTCUTS SYSTEM ====================

SHORTCUTS: Dict[str, List[str]] = {
    "cc": ["create", "company"],
    "cb": ["create", "brand"],
    "cm": ["create", "metadata"],
    "co": ["create", "offering"],
    "ct": ["create", "target"],
    "cv": ["create", "values"],
    "sb": ["show", "brand"],
    "sc": ["show", "company"],
    "sm": ["show", "metadata"],
    "so": ["show", "offering"],
    "st": ["show", "target"],
    "sv": ["show", "values"],
    "ub": ["update", "brand"],
    "uc": ["update", "company"],
    "um": ["update", "metadata"],
    "uo": ["update", "offering"],
    "ut": ["update", "target"],
    "uv": ["update", "values"],
    "ab": ["add", "brand"],
    "ac": ["add", "company"],
    "am": ["add", "metadata"],
    "ao": ["add", "offering"],
    "at": ["add", "target"],
    "av": ["add", "values"],
    "db": ["delete", "brand"],
    "dc": ["delete", "company"],
    "dm": ["delete", "metadata"],
    "do": ["delete", "offering"],
    "dt": ["delete", "target"],
    "dv": ["delete", "values"],
}

def expand_shortcuts(input_text: str) -> str:
    """
    Expand shortcuts in user input before parsing.
    
    Args:
        input_text: Original user input
        
    Returns:
        Input with shortcuts expanded to full words
    """
    tokens = input_text.strip().split()
    if not tokens:
        return input_text
    
    first_token = tokens[0].lower()
    if first_token in SHORTCUTS:
        expanded_words = SHORTCUTS[first_token]
        remaining_tokens = tokens[1:] if len(tokens) > 1 else []
        return " ".join(expanded_words + remaining_tokens)
    
    return input_text

# ==================== PLACEHOLDER HANDLERS ====================

async def create_handler_impl(entity_model, entity_value, attributes, context, attribute_words=None):
    """Dynamic create handler that works with any entity type"""
    try:
        from ..storage.database import create_company
        from datetime import datetime
        from ..core.enums import Currency, Legal, Unit, Type
        
        # For company creation, use the existing storage logic
        if entity_model.__name__ == 'CompanyEntity':
            # Set up default attributes
            entity_data = {
                "name": entity_value or f"Company_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "entity": Legal(attributes.get('entity', 'SA').upper()),
                "type": Type.COMPANY,
                "currency": Currency(attributes.get('currency', 'EUR').upper()),
                "unit": Unit.THOUSANDS,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "source_db": None,
                "last_synced_at": None
            }
            
            # Convert to dict for JSON storage
            entity_dict = {
                "name": entity_data["name"],
                "entity": entity_data["entity"].value,
                "type": entity_data["type"].value,
                "currency": entity_data["currency"].value,
                "unit": entity_data["unit"].value,
                "created_at": entity_data["created_at"].isoformat(),
                "updated_at": entity_data["updated_at"].isoformat(),
                "source_db": entity_data["source_db"],
                "last_synced_at": entity_data["last_synced_at"]
            }
            
            # Use storage module to create company
            storage_result = create_company(entity_dict, context)
            
            if storage_result.get("success", False):
                from ..ui.results import create_success_result
                from ..core.context import Context as NewContext
                
                # Create success result
                result = create_success_result(
                    operation="created",
                    entity_name=f"company {entity_data['name']}",
                    attributes={
                        "entity": entity_data["entity"].value,
                        "currency": entity_data["currency"].value,
                        "type": entity_data["type"].value
                    }
                )
                
                # Create new context at organization level
                new_context = NewContext(
                    level=1,
                    org_id=1,
                    org_name=entity_data["name"],
                    org_db_path=None
                )
                result.set_context_switch(new_context)
                
                return result
            else:
                from ..ui.results import create_error_result
                return create_error_result([storage_result.get("error", "Failed to create company")])
        
        else:
            # For other entity types, create a simple success result
            from ..ui.results import create_success_result
            return create_success_result(
                operation="created",
                entity_name=f"{entity_model.__name__.replace('Entity', '').lower()} {entity_value or 'unnamed'}",
                attributes=attributes
            )
    
    except Exception as e:
        from ..ui.results import create_error_result
        return create_error_result([f"Failed to create entity: {str(e)}"])

async def add_handler_impl(entity_model, entity_value, attributes, context, attribute_words=None):
    """Dynamic add handler for setting attributes on entities"""
    try:
        from ..ui.results import create_success_result, create_error_result
        from ..storage.database import save_entity_json, load_entity_json, entity_exists, create_default_entity_data
        from ..handlers.utils import get_company_name_from_context, create_updated_entity_data
        
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to add attributes"])
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: add entity attribute=value"])
        
        # Determine entity type from entity_model
        entity_name = entity_model.__name__.replace('Entity', '').lower()
        
        # Create entity if it doesn't exist
        if not entity_exists(entity_name, company_name, context):
            default_data = create_default_entity_data(entity_name)
            save_entity_json(entity_name, default_data, company_name, context)
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context) or {}
        
        # Create updated data with new attributes
        updated_data = create_updated_entity_data(current_data, attributes)
        
        # Save the updated entity
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_name} data")])
        
        return create_success_result(
            operation="added",
            entity_name=entity_name,
            attributes=attributes
        )
        
    except Exception as e:
        from ..ui.results import create_error_result
        return create_error_result([f"Failed to add attributes: {str(e)}"])

async def update_handler_impl(entity_model, entity_value, attributes, context, attribute_words=None):
    """Dynamic update handler for modifying existing attributes"""
    try:
        from ..ui.results import create_success_result, create_error_result
        from ..storage.database import save_entity_json, load_entity_json, entity_exists
        from ..handlers.utils import get_company_name_from_context, create_updated_entity_data
        
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to update attributes"])
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: update entity attribute=value"])
        
        # Determine entity type from entity_model
        entity_name = entity_model.__name__.replace('Entity', '').lower()
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            return create_error_result([f"No data found for {entity_name}"])
        
        # Create updated data
        updated_data = create_updated_entity_data(current_data, attributes)
        
        # Save the updated entity
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_name} data")])
        
        return create_success_result(
            operation="updated",
            entity_name=entity_name,
            attributes=attributes
        )
        
    except Exception as e:
        from ..ui.results import create_error_result
        return create_error_result([f"Failed to update attributes: {str(e)}"])

async def show_handler_impl(entity_model, entity_value, attributes, context, attribute_words=None):
    """Dynamic show handler for displaying entity data"""
    try:
        from ..ui.results import create_success_result, create_error_result
        from ..storage.database import load_entity_json, entity_exists
        from ..handlers.utils import get_company_name_from_context, format_entity_data_for_display
        
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to view entities"])
        
        # Determine entity type from entity_model
        entity_name = entity_model.__name__.replace('Entity', '').lower()
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Load entity data
        entity_data = load_entity_json(entity_name, company_name, context)
        if entity_data is None:
            return create_error_result([f"No data found for {entity_name}"])
        
        # Format data for display
        formatted_data = format_entity_data_for_display(entity_data)
        
        return create_success_result(
            operation="displayed",
            entity_name=entity_name,
            attributes={"data": formatted_data}
        )
        
    except Exception as e:
        from ..ui.results import create_error_result
        return create_error_result([f"Failed to show entity data: {str(e)}"])

async def delete_handler_impl(entity_model, entity_value, attributes, context, attribute_words=None):
    """Dynamic delete handler for removing attribute values"""
    try:
        from ..ui.results import create_success_result, create_error_result
        from ..storage.database import save_entity_json, load_entity_json, entity_exists
        from ..handlers.utils import get_company_name_from_context
        
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to delete attributes"])
        
        # Check if we have specific attributes to delete
        if not attribute_words:
            return create_error_result(["No attributes specified to delete. Use format: delete entity attribute"])
        
        # Determine entity type from entity_model
        entity_name = entity_model.__name__.replace('Entity', '').lower()
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            return create_error_result([f"No data found for {entity_name}"])
        
        # Remove the specified attributes
        updated_data = current_data.copy()
        removed_attributes = []
        
        for attr_name in attribute_words:
            if attr_name in updated_data:
                if entity_name == "metadata":
                    # For metadata, remove the key entirely
                    del updated_data[attr_name]
                else:
                    # For other entities, set to null
                    updated_data[attr_name] = None
                removed_attributes.append(attr_name)
        
        if not removed_attributes:
            return create_error_result([f"None of the specified attributes exist in {entity_name}: {', '.join(attribute_words)}"])
        
        # Update timestamp
        from datetime import datetime
        if 'updated_at' in updated_data:
            updated_data['updated_at'] = datetime.now().isoformat()
        
        # Save the updated entity
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_name} data")])
        
        return create_success_result(
            operation="deleted",
            entity_name=entity_name,
            attributes={"removed_attributes": ", ".join(removed_attributes)}
        )
        
    except Exception as e:
        from ..ui.results import create_error_result
        return create_error_result([f"Failed to delete attributes: {str(e)}"])

async def navigate_handler_impl(entity_model, entity_value, attributes, context, attribute_words=None):
    """Simplified navigate handler for dynamic commands"""
    # Basic navigation logic - this will be enhanced later
    if entity_value == "~" or entity_value == "root":
        # Navigate to root
        return {"success": True, "message": "Navigated to root"}
    elif entity_value:
        # Navigate to specific entity
        return {"success": True, "message": f"Navigated to {entity_value}"}
    else:
        # Show current location
        return {"success": True, "message": "Current location"}

# Set the handler references
create_handler = create_handler_impl
add_handler = add_handler_impl
update_handler = update_handler_impl
show_handler = show_handler_impl
delete_handler = delete_handler_impl
navigate_handler = navigate_handler_impl

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
    handler: Any = Field(description="Function to handle this action")
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
        context=ContextLevel.ORG,
        description="Display entity data or specific attributes",
        aliases=["display", "view", "get","read","s"],
        handler=show_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.READ        ,
    ),
    

    
    # ==================== ENTITIES ====================
   
    EntityWord(
        id="company",
        description="A business entity that can be managed in the terminal",
        aliases=["business", "firm","co"],
        entity_model=CompanyEntity        
    ),
    
    EntityWord(
        id="metadata",
        description="Key-value metadata for extending company information",
        aliases=["meta", "info","md"],
        entity_model=MetadataEntity
    ),
    
    EntityWord(
        id="brand",
        description="Company brand identity (vision, mission, personality)",
        aliases=["branding", "identity", "br"],
        entity_model=BrandEntity
    ),
    
    EntityWord(
        id="offering",
        description="Company product or service offerings",
        aliases=["product", "service","o"],
        entity_model=OfferingEntity
    ),
    
    EntityWord(
        id="target",
        description="Target audience or market segments",
        aliases=["audience", "segment","tgt"],
        entity_model=TargetEntity
    ),
    
    EntityWord(
        id="values",
        description="Company core values",
        aliases=["values", "principles","val"],
        entity_model=ValuesEntity
    ),
    
    # ==================== ATTRIBUTES ====================
    
    # Common attributes across multiple entities
    
    AttributeWord(
        id="name",
        description="Name or title of the entity",
        aliases=["n"],
        entity_models=[CompanyEntity, BrandEntity, OfferingEntity, TargetEntity, ValuesEntity]
    ),
    
    AttributeWord(
        id="key",
        description="Key identifier or category",
        aliases=["k"],
        entity_models=[MetadataEntity, OfferingEntity, TargetEntity, ValuesEntity]
    ),
    
    AttributeWord(
        id="value",
        description="Value or description content",
        aliases=[],
        entity_models=[MetadataEntity, OfferingEntity, TargetEntity, ValuesEntity]
    ),
    
    # Company-specific attributes
    AttributeWord(
        id="legal",
        description="Legal entity type (SA, LLC, INC, etc.)",
        aliases=["entity", "e"],   
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="type",
        description="Organization type (company, fund, foundation)",
        aliases=[],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="currency",
        description="Currency used for financial data (EUR, USD, GBP, etc.)",
        aliases=["curr"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="unit",
        description="Unit for financial data (THOUSANDS, MILLIONS, etc.)",
        aliases=["u"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="closing",
        description="Fiscal year end month (1-12)",
        aliases=["cl"],
        entity_models=[CompanyEntity]
    ),
    
    AttributeWord(
        id="incorporation",
        description="Date of incorporation",
        aliases=["inc", "founded"],
        entity_models=[CompanyEntity]
    ),
    
    # Brand-specific attributes
    AttributeWord(
        id="vision",
        description="Company vision statement",
        aliases=["vis"],
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="mission",
        description="Company mission statement",
        aliases=["miss"],
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="personality",
        description="Brand personality description",
        aliases=["perso"],
        entity_models=[BrandEntity]
    ),
    
    AttributeWord(
        id="promise",
        description="Brand promise to customers",
        aliases=["prom"],
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