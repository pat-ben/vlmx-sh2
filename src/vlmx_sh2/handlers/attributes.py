"""
Generic attribute command handlers for VLMX DSL.

Implements dynamic command handlers that work with any entity-attribute combination.
These handlers replace the need for hardcoded entity-specific commands by extracting
entity and attribute information dynamically from parse results.
"""

from typing import Dict, Any
from ..dsl.commands import register_command
from ..core.context import Context
from ..core.enums import ContextLevel
from ..dsl.parser import ParseResult
from ..ui.results import CommandResult, create_success_result, create_error_result
from ..storage.database import (
    load_entity_json, save_entity_json, entity_exists, create_default_entity_data
)
from .utils import (
    extract_entity_from_parse_result,
    extract_attributes_from_parse_result,
    get_company_name_from_context,
    extract_specific_attributes_from_tokens,
    format_entity_data_for_display,
    create_updated_entity_data,
    validate_entity_attribute_combination
)

# ==================== GENERIC ATTRIBUTE HANDLERS ====================

@register_command(
    command_id="add_attribute",
    description="Add or set attribute values to any entity",
    context=ContextLevel.ORG,  # Must be in organization context
    required_words={"add"},
    optional_words=set(),  # Empty - parser validates via Word Registry
    examples=[
        "add brand vision=\"Empower entrepreneurs globally\"",
        "add organization currency=USD",
        "add brand mission=\"Transform business innovation\"",
    ]
)
async def add_attribute_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for adding/setting attribute values to any entity.
    
    Command patterns:
    - add brand vision="value"
    - add organization currency=USD
    - add metadata key=value
    """
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to modify entities"])
        
        # Extract entity and attributes from parse result
        entity_name = extract_entity_from_parse_result(parse_result)
        attributes = extract_attributes_from_parse_result(parse_result)
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: add entity attribute=value"])
        
        # Validate entity-attribute combinations
        for attr_name in attributes.keys():
            if not validate_entity_attribute_combination(entity_name, attr_name):
                return create_error_result([f"Attribute '{attr_name}' is not valid for entity '{entity_name}'"])
        
        # Load current entity data or create default
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            current_data = create_default_entity_data(entity_name)
        
        # Create updated data
        updated_data = create_updated_entity_data(current_data, attributes)
        
        # Save the updated data
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        
        if save_result.get("success", False):
            # Create success result
            result = create_success_result(
                operation="added",
                entity_name=f"{entity_name} attributes"
            )
            
            # Add details about what was updated
            for attr_name, attr_value in attributes.items():
                result.add_attribute(attr_name, attr_value)
            
            return result
        else:
            return create_error_result([save_result.get("error", "Failed to save entity data")])
    
    except Exception as e:
        return create_error_result([f"Failed to add attributes: {str(e)}"])

@register_command(
    command_id="update_attribute",
    description="Update existing attribute values for any entity",
    context=ContextLevel.ORG,  # Must be in organization context
    required_words={"update"},
    optional_words=set(),  # Empty - parser validates via Word Registry
    examples=[
        "update brand vision=\"New vision statement\"",
        "update organization currency=EUR",
        "update brand personality=\"Innovative and bold\"",
    ]
)
async def update_attribute_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for updating existing attribute values for any entity.
    
    Command patterns:
    - update brand vision="new value"
    - update organization currency=EUR
    - update metadata key=new_value
    """
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to modify entities"])
        
        # Extract entity and attributes from parse result
        entity_name = extract_entity_from_parse_result(parse_result)
        attributes = extract_attributes_from_parse_result(parse_result)
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: update entity attribute=value"])
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Validate entity-attribute combinations
        for attr_name in attributes.keys():
            if not validate_entity_attribute_combination(entity_name, attr_name):
                return create_error_result([f"Attribute '{attr_name}' is not valid for entity '{entity_name}'"])
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            return create_error_result([f"Could not load {entity_name} data"])
        
        # Create updated data
        updated_data = create_updated_entity_data(current_data, attributes)
        
        # Save the updated data
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        
        if save_result.get("success", False):
            # Create success result
            result = create_success_result(
                operation="updated",
                entity_name=f"{entity_name} attributes"
            )
            
            # Add details about what was updated
            for attr_name, attr_value in attributes.items():
                result.add_attribute(attr_name, attr_value)
            
            return result
        else:
            return create_error_result([save_result.get("error", "Failed to save entity data")])
    
    except Exception as e:
        return create_error_result([f"Failed to update attributes: {str(e)}"])

@register_command(
    command_id="show_attribute",
    description="Display entity data or specific attributes",
    context=ContextLevel.ORG,  # Must be in organization context
    required_words={"show"},
    optional_words=set(),  # Empty - parser validates via Word Registry
    examples=[
        "show brand",
        "show organization",
        "show brand vision",
        "show organization currency",
    ]
)
async def show_attribute_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for displaying entity data or specific attributes.
    
    Command patterns:
    - show brand (shows all brand data)
    - show organization (shows all organization data)
    - show brand vision (shows only vision attribute)
    - show organization currency (shows only currency attribute)
    """
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to view entities"])
        
        # Extract entity and specific attributes from parse result
        entity_name = extract_entity_from_parse_result(parse_result)
        specific_attributes = extract_specific_attributes_from_tokens(parse_result)
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Load entity data
        entity_data = load_entity_json(entity_name, company_name, context)
        if entity_data is None:
            return create_error_result([f"Could not load {entity_name} data"])
        
        # Format data for display
        formatted_data = format_entity_data_for_display(entity_data, specific_attributes)
        
        # Create success result
        if specific_attributes:
            entity_description = f"{entity_name} {', '.join(specific_attributes)}"
        else:
            entity_description = f"{entity_name} data"
        
        result = create_success_result(
            operation="displayed",
            entity_name=entity_description
        )
        
        # Add the formatted data as an attribute
        result.add_attribute("data", formatted_data)
        
        return result
    
    except Exception as e:
        return create_error_result([f"Failed to show entity data: {str(e)}"])

@register_command(
    command_id="remove_attribute",
    description="Clear attribute values (set to null) for any entity",
    context=ContextLevel.ORG,  # Must be in organization context
    required_words={"delete"},
    optional_words=set(),  # Empty - parser validates via Word Registry
    examples=[
        "remove brand mission",
        "remove organization incorporation",
        "remove brand vision",
    ]
)
async def remove_attribute_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for clearing/removing attribute values from any entity.
    
    Command patterns:
    - remove brand mission (sets mission to null)
    - remove organization incorporation (sets incorporation to null)
    - remove metadata key (removes the key-value pair)
    """
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to modify entities"])
        
        # Extract entity and specific attributes from parse result
        entity_name = extract_entity_from_parse_result(parse_result)
        specific_attributes = extract_specific_attributes_from_tokens(parse_result)
        
        if not specific_attributes:
            return create_error_result(["No attributes specified. Use format: remove entity attribute"])
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Validate entity-attribute combinations
        for attr_name in specific_attributes:
            if not validate_entity_attribute_combination(entity_name, attr_name):
                return create_error_result([f"Attribute '{attr_name}' is not valid for entity '{entity_name}'"])
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            return create_error_result([f"Could not load {entity_name} data"])
        
        # Clear the specified attributes (set to null)
        attributes_to_clear = {attr: None for attr in specific_attributes}
        updated_data = create_updated_entity_data(current_data, attributes_to_clear)
        
        # Save the updated data
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        
        if save_result.get("success", False):
            # Create success result
            result = create_success_result(
                operation="removed",
                entity_name=f"{entity_name} attributes"
            )
            
            # Add details about what was cleared
            for attr_name in specific_attributes:
                result.add_attribute(f"cleared_{attr_name}", "null")
            
            return result
        else:
            return create_error_result([save_result.get("error", "Failed to save entity data")])
    
    except Exception as e:
        return create_error_result([f"Failed to remove attributes: {str(e)}"])

# ==================== COMMAND REGISTRATION ====================

def register_all_commands():
    """
    Explicitly register all attribute command handlers.
    
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
    expected_commands = ["add_attribute", "update_attribute", "show_attribute", "remove_attribute"]
    missing_commands = [cmd for cmd in expected_commands if cmd not in registered_commands]
    
    if missing_commands:
        raise RuntimeError(f"Expected attribute commands not registered: {missing_commands}")
    
    return len([cmd for cmd in registered_commands if cmd in expected_commands])

# ==================== DEBUG INFO ====================

def get_attribute_handler_info() -> dict:
    """Get information about registered attribute handlers."""
    return {
        "handlers": [
            {
                "command_id": "add_attribute",
                "description": "Add or set attribute values to any entity",
                "required_words": ["add"],
                "context_level": "ORG"
            },
            {
                "command_id": "update_attribute", 
                "description": "Update existing attribute values for any entity",
                "required_words": ["update"],
                "context_level": "ORG"
            },
            {
                "command_id": "show_attribute",
                "description": "Display entity data or specific attributes", 
                "required_words": ["show"],
                "context_level": "ORG"
            },
            {
                "command_id": "remove_attribute",
                "description": "Clear attribute values for any entity",
                "required_words": ["delete"],
                "context_level": "ORG"
            }
        ],
        "storage": "Generic JSON entity files",
        "utilities": ["extract_entity_from_parse_result", "extract_attributes_from_parse_result"],
        "registered_commands": register_all_commands()
    }