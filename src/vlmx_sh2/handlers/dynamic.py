"""
Dynamic commands for VLMX DSL CRUD operations.

Provides universal add, update, show, and delete commands that work with any
entity-attribute combination. These commands are more flexible than the specific
attribute commands as they work dynamically based on user input.
"""

from typing import List
from ..core.context import Context
from ..core.enums import ContextLevel
from ..dsl.commands import register_command
from ..dsl.parser import ParseResult
from ..dsl.words import Word
from ..ui.results import CommandResult, create_success_result, create_error_result
from ..storage.database import (
    load_entity_json, 
    save_entity_json,
    entity_exists,
    create_default_entity_data
)
from ..handlers.company import validate_attribute_for_entity
from .utils import (
    extract_entity_from_parse_result,
    extract_attributes_from_parse_result,
    get_company_name_from_context,
    extract_specific_attributes_from_tokens,
    format_entity_data_for_display,
    create_updated_entity_data
)


# ==================== ADD COMMAND ====================

@register_command(
    command_id="add_dynamic",
    description="Add/set attribute values to any entity",
    context=ContextLevel.ORG,
    required_words={"add"},
    optional_words=set(),
    is_dynamic=True,
    examples=[
        "add brand vision=To revolutionize technology",
        "add metadata category=SaaS",
        "add offering name=Cloud_Platform"
    ]
)
async def add_dynamic_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for adding/setting attribute values to any entity.
    
    Command patterns:
    - add organization name TechCorp
    - add brand vision To revolutionize technology
    - add metadata key value
    - add offering name Cloud Platform
    """
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to add attributes"])
        
        # Extract entity and attributes from parse result
        entity_name = extract_entity_from_parse_result(parse_result)
        attributes = extract_attributes_from_parse_result(parse_result)
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: add entity attribute value"])
        
        # Validate attribute-entity combinations
        validation_errors = []
        for attr_name in attributes.keys():
            if not validate_attribute_for_entity(attr_name, entity_name):
                validation_errors.append(f"Attribute '{attr_name}' is not valid for entity '{entity_name}'")
        
        if validation_errors:
            return create_error_result(validation_errors)
        
        # Create entity if it doesn't exist
        if not entity_exists(entity_name, company_name, context):
            default_data = create_default_entity_data(entity_name)
            save_entity_json(entity_name, default_data, company_name, context)
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            current_data = {}
        
        # Create updated data with new attributes
        updated_data = create_updated_entity_data(current_data, attributes)
        
        # Save the updated entity
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_name} data")])
        
        # Create success message
        attr_list = [f"{name}={value}" for name, value in attributes.items()]
        return create_success_result(
            operation="added",
            entity_name=entity_name,
            attributes=attributes
        )
        
    except Exception as e:
        return create_error_result([f"Failed to add attributes: {str(e)}"])


# ==================== UPDATE COMMAND ====================

@register_command(
    command_id="update_dynamic",
    description="Update existing attribute values for any entity",
    context=ContextLevel.ORG,
    required_words={"update"},
    optional_words=set(),
    is_dynamic=True,
    examples=[
        "update organization name TechCorp Plus",
        "update brand mission To change the world",
        "update metadata category Enterprise",
        "update offering name Premium Platform"
    ]
)
async def update_dynamic_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for updating existing attribute values for any entity.
    
    Command patterns:
    - update organization name TechCorp Plus
    - update brand mission To change the world
    - update metadata category Enterprise
    - update offering name Premium Platform
    """
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to update attributes"])
        
        # Extract entity and attributes from parse result
        entity_name = extract_entity_from_parse_result(parse_result)
        attributes = extract_attributes_from_parse_result(parse_result)
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: update entity attribute value"])
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Validate attribute-entity combinations
        validation_errors = []
        for attr_name in attributes.keys():
            if not validate_attribute_for_entity(attr_name, entity_name):
                validation_errors.append(f"Attribute '{attr_name}' is not valid for entity '{entity_name}'")
        
        if validation_errors:
            return create_error_result(validation_errors)
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            return create_error_result([f"No data found for {entity_name}"])
        
        # Check if attributes exist (for updates, they should already exist)
        missing_attributes = []
        for attr_name in attributes.keys():
            if attr_name not in current_data:
                missing_attributes.append(attr_name)
        
        if missing_attributes:
            return create_error_result([
                f"Attributes do not exist and cannot be updated: {', '.join(missing_attributes)}. Use 'add' command instead."
            ])
        
        # Create updated data
        updated_data = create_updated_entity_data(current_data, attributes)
        
        # Save the updated entity
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_name} data")])
        
        # Create success message
        attr_list = [f"{name}={value}" for name, value in attributes.items()]
        return create_success_result(
            operation="updated",
            entity_name=entity_name,
            attributes=attributes
        )
        
    except Exception as e:
        return create_error_result([f"Failed to update attributes: {str(e)}"])


# ==================== SHOW COMMAND ====================

@register_command(
    command_id="show_dynamic",
    description="Display entity data or specific attributes for any entity",
    context=ContextLevel.ORG,
    required_words={"show"},
    optional_words=set(),
    is_dynamic=True,
    examples=[
        "show organization",
        "show brand",
        "show organization name",
        "show brand vision mission",
        "show metadata"
    ]
)
async def show_dynamic_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for displaying entity data or specific attributes.
    
    Command patterns:
    - show brand (shows all brand data)
    - show organization (shows all organization data)
    - show brand vision (shows only vision attribute)
    - show organization name currency (shows only name and currency attributes)
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
            return create_error_result([f"No data found for {entity_name}"])
        
        # Validate specific attributes if provided
        if specific_attributes:
            validation_errors = []
            for attr_name in specific_attributes:
                if not validate_attribute_for_entity(attr_name, entity_name):
                    validation_errors.append(f"Attribute '{attr_name}' is not valid for entity '{entity_name}'")
            
            if validation_errors:
                return create_error_result(validation_errors)
        
        # Format data for display
        formatted_data = format_entity_data_for_display(entity_data, specific_attributes)
        
        return create_success_result(
            operation="displayed",
            entity_name=entity_name
        )
        
    except Exception as e:
        return create_error_result([f"Failed to show entity data: {str(e)}"])


# ==================== DELETE COMMAND ====================

@register_command(
    command_id="delete_dynamic",
    description="Clear attribute values (set to null) for any entity",
    context=ContextLevel.ORG,
    required_words={"delete"},
    optional_words=set(),
    is_dynamic=True,
    examples=[
        "delete brand mission",
        "delete organization incorporation",
        "delete brand vision",
        "delete metadata key"
    ]
)
async def delete_dynamic_handler(parse_result: ParseResult, context: Context) -> CommandResult:
    """
    Handler for clearing/deleting attribute values (sets them to null).
    
    Command patterns:
    - delete brand mission (sets mission to null)
    - delete organization incorporation (sets incorporation to null)
    - delete brand vision (sets vision to null)
    - delete metadata key (removes the key-value pair)
    
    Note: For metadata entities, this removes the entire key-value pair.
    For other entities, this sets the attribute to null.
    """
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to delete attributes"])
        
        # Extract entity and specific attributes from parse result
        entity_name = extract_entity_from_parse_result(parse_result)
        specific_attributes = extract_specific_attributes_from_tokens(parse_result)
        
        if not specific_attributes:
            return create_error_result(["No attributes specified. Use format: delete entity attribute"])
        
        # Check if entity exists
        if not entity_exists(entity_name, company_name, context):
            return create_error_result([f"Entity '{entity_name}' does not exist for company '{company_name}'"])
        
        # Validate attribute-entity combinations
        validation_errors = []
        for attr_name in specific_attributes:
            if not validate_attribute_for_entity(attr_name, entity_name):
                validation_errors.append(f"Attribute '{attr_name}' is not valid for entity '{entity_name}'")
        
        if validation_errors:
            return create_error_result(validation_errors)
        
        # Load current entity data
        current_data = load_entity_json(entity_name, company_name, context)
        if current_data is None:
            return create_error_result([f"No data found for {entity_name}"])
        
        # Clear the specified attributes
        updated_data = current_data.copy()
        removed_attributes = []
        
        for attr_name in specific_attributes:
            if attr_name in updated_data:
                if entity_name == "metadata":
                    # For metadata, remove the key entirely
                    del updated_data[attr_name]
                else:
                    # For other entities, set to null
                    updated_data[attr_name] = None
                removed_attributes.append(attr_name)
        
        if not removed_attributes:
            return create_error_result([f"None of the specified attributes exist in {entity_name}"])
        
        # Save the updated entity
        save_result = save_entity_json(entity_name, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_name} data")])
        
        return create_success_result(
            operation="removed",
            entity_name=entity_name
        )
        
    except Exception as e:
        return create_error_result([f"Failed to remove attributes: {str(e)}"])


# ==================== REGISTRATION INFO ====================

def register_dynamic_commands():
    """
    Register all dynamic commands.
    
    This function is called automatically when this module is imported.
    Returns the number of commands registered.
    """
    # Commands are registered via decorators above
    return 4

# Auto-register when module is imported
_registered_count = register_dynamic_commands()