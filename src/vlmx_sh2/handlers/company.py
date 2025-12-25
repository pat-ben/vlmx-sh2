"""
Command handlers and business logic for VLMX DSL.

Implements the actual execution logic for registered commands. Handles entity
creation, validation, data transformation, and result formatting. Integrates
with the storage layer for data persistence.
"""

from datetime import datetime

from ..dsl.commands import register_command
from ..core.context import Context
from ..dsl.words import get_word, EntityWord
from ..core.enums import ContextLevel
from ..dsl.parser import ParseResult
from ..storage.database import create_company, delete_company, list_companies
from ..ui.results import CommandResult, create_success_result, create_error_result


# ==================== BUSINESS LOGIC UTILITIES ====================

def validate_attribute_for_entity(attribute_id: str, entity_id: str) -> bool:
    """
    Validate if an attribute exists on an entity using the Words Registry.
    
    Args:
        attribute_id: ID of the attribute word
        entity_id: ID of the entity word
        
    Returns:
        True if the attribute exists on the entity, False otherwise
    """
    from ..dsl.words import AttributeWord
    
    # Get the attribute word
    attribute_word = get_word(attribute_id)
    if not attribute_word or not isinstance(attribute_word, AttributeWord):
        return False
    
    # Get the entity word
    entity_word = get_word(entity_id)
    if not entity_word or not isinstance(entity_word, EntityWord):
        return False
    
    # Check if the entity model is in the attribute's entity_models list
    return entity_word.entity_model in attribute_word.entity_models


def get_entity_model_from_registry(entity_id: str):
    """
    Get entity model from Words Registry with validation.
    
    Args:
        entity_id: ID of the entity word
        
    Returns:
        Entity model class or None if not found
    """
    entity_word = get_word(entity_id)
    if entity_word and isinstance(entity_word, EntityWord):
        return entity_word.entity_model
    return None

def extract_company_name_from_parse_result(parse_result: ParseResult) -> str:
    """Extract company name from parse result with fallback logic."""
    company_name = parse_result.entity_values.get('company_name')
    
    if company_name:
        return company_name
    
    # Fallback: generate timestamp-based name for demo purposes
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Company_{timestamp}"


def extract_company_attributes_from_parse_result(parse_result: ParseResult) -> dict:
    """Extract company attributes from parse result with defaults and validation."""
    from ..core.enums import Currency, Entity, Unit, Type
    
    attributes = {}
    
    # Extract entity from attributes (entity=SA)
    entity_str = parse_result.attribute_values.get('entity', 'SA')
    try:
        attributes['entity'] = Entity(entity_str.upper())
    except ValueError:
        attributes['entity'] = Entity.SA  # Default fallback
    
    # Extract currency from attributes (currency=EUR)  
    currency_str = parse_result.attribute_values.get('currency', 'EUR')
    try:
        attributes['currency'] = Currency(currency_str.upper())
    except ValueError:
        attributes['currency'] = Currency.EUR  # Default fallback
    
    # Set default type and unit (required fields)
    attributes['type'] = Type.COMPANY  # Default to company type
    attributes['unit'] = Unit.THOUSANDS
    
    return attributes


# ==================== COMMAND HANDLERS ====================

@register_command(
    command_id="create_company",
    description="Create a new company entity with specified attributes",
    context=ContextLevel.SYS,
    required_words={"create", "company"},
    optional_words={"entity", "currency", "type", "unit", "closing", "incorporation"},
    examples=[
        "create company ACME entity=SA type=company currency=EUR",
        "create company HoldCo entity=HOLDING currency=USD",
        "create company TestCorp entity=SA type=company currency=EUR incorporation=2024-12-31"
    ]
)
async def create_company_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for creating companies.
    
    Command: create company [company_name] --entity=[entity] --currency=[currency]
    """
    try:
        # Infer entity type from parsed words
        entity_words = [word for word in parse_result.recognized_words 
                       if hasattr(word, 'word_type') and word.word_type.value == 'entity']
        
        if not entity_words:
            return create_error_result(["No entity word found in command"])
        
        entity_word = entity_words[0]  # Take the first entity word
        EntityModel = get_entity_model_from_registry(entity_word.id)
        
        if not EntityModel:
            return create_error_result([f"Entity '{entity_word.id}' not found in Words Registry"])
        
        # Extract entity name from parse result
        entity_name = extract_company_name_from_parse_result(parse_result)
        
        # Extract attributes from parse result
        attributes = extract_company_attributes_from_parse_result(parse_result)
        
        # Create entity dynamically using inferred model from Words Registry
        entity_instance = EntityModel(
            name=entity_name,
            entity=attributes["entity"],
            type=attributes["type"],
            currency=attributes["currency"],
            unit=attributes["unit"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_db=None,  # Optional field for portfolio tracking
            last_synced_at=None  # Optional field for portfolio sync tracking
        )
        
        # Convert to dict for JSON storage with datetime serialization
        entity_dict = entity_instance.model_dump(mode='json')
        
        # Ensure datetime fields are properly serialized as ISO strings
        for field_name in ['created_at', 'updated_at']:
            if field_name in entity_dict and hasattr(entity_instance, field_name):
                field_value = getattr(entity_instance, field_name)
                if field_value and hasattr(field_value, 'isoformat'):
                    entity_dict[field_name] = field_value.isoformat()
        
        # Use storage module to create entity
        storage_result = create_company(entity_dict, context)  # TODO: Make this dynamic too
        
        if storage_result.get("success", False):
            # Create success result with entity details
            cmd_result = create_success_result(
                operation="created",
                entity_name=f"{entity_word.id} {entity_name}",
                attributes={
                    "type": attributes["type"].value,
                    "entity": attributes["entity"].value,
                    "currency": attributes["currency"].value,
                    "unit": attributes["unit"].value,
                    "created_at": entity_dict.get("created_at", "N/A")
                }
            )
            return cmd_result
        else:
            # Create error result
            return create_error_result([storage_result.get("error", "Failed to create entity")])
        
    except Exception as e:
        return create_error_result([f"Failed to create entity: {str(e)}"])


@register_command(
    command_id="delete_company",
    description="Delete an existing company entity",
    context=ContextLevel.SYS,
    required_words={"delete", "company"},
    examples=[
        "delete company ACME-SA",
        "delete company HoldCo"
    ]
)
async def delete_company_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for deleting companies.
    
    Command: delete company [company_name]
    """
    try:
        # Extract company name from parse result
        company_name = extract_company_name_from_parse_result(parse_result)
        
        # If no specific company name was provided, try to delete the first available company
        if company_name.startswith("Company_"):  # This is our generated fallback name
            companies_info = list_companies(context)
            if not companies_info["success"] or companies_info["count"] == 0:
                return create_error_result(["No companies found to delete"])
            
            # Use the first company if no specific name was provided
            companies = companies_info["companies"]
            if companies:
                first_company = companies[0]
                company_name = first_company.get("name", "Unknown")
            else:
                return create_error_result(["No companies found to delete"])
        
        # Use storage module to delete company
        storage_result = delete_company(company_name, context)
        
        if storage_result.get("success", False):
            # Create success result
            return create_success_result(
                operation="deleted",
                entity_name=f"company {company_name}"
            )
        else:
            # Create error result
            return create_error_result([storage_result.get("error", "Failed to delete company")])
            
    except Exception as e:
        return create_error_result([f"Failed to delete company: {str(e)}"])


# ==================== UTILITY FUNCTIONS ====================
# Note: list_companies and get_company_by_name are imported from storage module


# ==================== COMMAND REGISTRATION ====================

def register_all_commands():
    """
    Explicitly register all command handlers.
    
    This function ensures all commands are registered when called.
    The @register_command decorators above have already executed
    during module import, but this function serves as an explicit
    entry point for command registration and makes dependencies clear.
    
    Returns:
        int: Number of commands registered
    """
    # Commands are already registered via decorators, but we can verify
    from ..dsl.commands import _command_registry
    
    registered_commands = list(_command_registry.get_all_commands().keys())
    
    # Verify expected commands are registered
    expected_commands = ["create_company", "delete_company"]
    missing_commands = [cmd for cmd in expected_commands if cmd not in registered_commands]
    
    if missing_commands:
        raise RuntimeError(f"Expected commands not registered: {missing_commands}")
    
    return len(registered_commands)


# ==================== DEBUG INFO ====================

def get_handler_info() -> dict:
    """Get information about registered handlers."""
    return {
        "handlers": [
            {
                "command_id": "create_company",
                "description": "Create a new company entity",
                "required_words": ["create", "company"],
                "optional_words": ["entity", "currency"],
                "context_level": "SYS"
            },
            {
                "command_id": "delete_company", 
                "description": "Delete an existing company entity",
                "required_words": ["delete", "company"],
                "optional_words": [],
                "context_level": "SYS"
            }
        ],
        "storage": "JSON files",
        "utilities": ["list_companies", "get_company_by_name"],
        "registered_commands": register_all_commands()
    }