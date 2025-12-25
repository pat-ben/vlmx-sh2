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
from ..storage.database import create_company, delete_company, list_companies, company_exists
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
            
            # Create new context at organization level (level 1) with the company name
            new_context = Context(
                level=1,  # ORG level
                org_id=1,  # Placeholder ID
                org_name=entity_name,
                org_db_path=None  # Could be set to the company folder path if needed
            )
            
            # Set context switch on the result
            cmd_result.set_context_switch(new_context)
            
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


@register_command(
    command_id="navigate",
    description="Navigate between contexts (SYS root or ORG company)",
    context=ContextLevel.SYS,  # Can be used from any level
    required_words={"cd"},
    optional_words=set(),
    examples=[
        "cd",  # Show current location
        "cd ~",  # Navigate to root (SYS level)  
        "cd ACME",  # Navigate to company ACME (ORG level)
        "cd ..",  # Navigate up one level (to parent)
    ]
)
async def navigate_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for context navigation using cd command.
    
    Commands:
    - cd          : Show current location
    - cd ~        : Navigate to root (SYS level)
    - cd ..       : Navigate up one level  
    - cd {company}: Navigate to company context (ORG level)
    """
    try:
        # Extract navigation target from tokens more robustly
        navigation_target = None
        
        # First check entity values (for company names)
        if parse_result.entity_values.get('company_name'):
            navigation_target = parse_result.entity_values['company_name']
        
        # If no entity values, look at all non-action tokens after 'cd'
        if not navigation_target:
            # Get all tokens that are not the 'cd' action word
            non_action_tokens = []
            for token in parse_result.tokens:
                # Skip the 'cd' token itself
                if token.text.lower() == 'cd':
                    continue
                # Include any other token (VALUE, UNKNOWN, or other word types)
                if token.text.strip():  # Make sure it's not empty
                    non_action_tokens.append(token.text)
            
            # Use the first non-action token as navigation target
            if non_action_tokens:
                navigation_target = non_action_tokens[0]
        
        # Handle different navigation patterns
        if not navigation_target:
            # Plain "cd" with no arguments - show current location or usage
            if context.level == 0:
                return create_success_result(
                    operation="current location",
                    entity_name="root (/VLMX)"
                )
            else:
                return create_success_result(
                    operation="current location", 
                    entity_name=f"company {context.org_name} (/VLMX/{context.org_name})"
                )
                
        elif navigation_target in ["root", "~", "/"]:
            # Explicit root navigation
            new_context = Context(level=0)
            
            result = create_success_result(
                operation="navigated",
                entity_name="root"
            )
            result.set_context_switch(new_context)
            return result
            
        elif navigation_target == "..":
            # Navigate up one level
            if context.level > 0:
                new_context = Context(level=context.level - 1)
                
                result = create_success_result(
                    operation="navigated",
                    entity_name="parent directory"
                )
                result.set_context_switch(new_context)
                return result
            else:
                return create_error_result(["Already at root level"])
                
        else:
            # Navigate to specific company (assuming it exists)
            company_name = navigation_target
            
            # Check if company exists
            if company_exists(company_name, context):
                new_context = Context(
                    level=1,  # ORG level
                    org_id=1,  # Placeholder ID
                    org_name=company_name
                )
                
                result = create_success_result(
                    operation="navigated",
                    entity_name=f"company {company_name}"
                )
                result.set_context_switch(new_context)
                return result
            else:
                return create_error_result([f"Company '{company_name}' not found"])
        
    except Exception as e:
        return create_error_result([f"Failed to navigate: {str(e)}"])


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
    expected_commands = ["create_company", "delete_company", "navigate"]
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