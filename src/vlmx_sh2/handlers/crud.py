"""
Truly dynamic CRUD handlers for VLMX DSL.

Each handler works with ANY entity type without hardcoded entity-specific logic.
Uses entity_model metadata and generic storage functions to provide
unified behavior across all entity-attribute combinations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

async def create_handler(entity_model, entity_value, attributes, context, attribute_words=None):
    """
    Truly dynamic create handler - works for ANY entity type.
    No hardcoded entity-specific logic.
    """
    from ..ui.results import create_success_result, create_error_result
    from ..storage.database import create_entity
    
    try:
        # 1. Determine entity type from model
        entity_type = entity_model.__name__.replace('Entity', '').lower()
        
        # 2. Prepare entity data with defaults
        entity_data = {
            "name": entity_value or f"{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            **attributes,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 3. Add entity-specific defaults based on entity type
        if entity_type == 'company':
            try:
                from ..models.schema.enums import Legal, Currency, Unit, Type
                entity_data.update({
                    "entity": Legal(attributes.get('entity', 'SA').upper()),
                    "type": Type.COMPANY,
                    "currency": Currency(attributes.get('currency', 'EUR').upper()),
                    "unit": Unit.THOUSANDS,
                    "source_db": None,
                    "last_synced_at": None
                })
                
                # Convert enums to values for JSON storage
                entity_dict = entity_data.copy()
                for key, value in entity_dict.items():
                    if hasattr(value, 'value'):
                        entity_dict[key] = value.value
            except ImportError:
                # Fallback to string values if enums not available
                entity_data.update({
                    "entity": attributes.get('entity', 'SA').upper(),
                    "type": "COMPANY",
                    "currency": attributes.get('currency', 'EUR').upper(),
                    "unit": "THOUSANDS",
                    "source_db": None,
                    "last_synced_at": None
                })
                entity_dict = entity_data
        else:
            entity_dict = entity_data
        
        # 4. Validate using the entity model (Pydantic validation)
        try:
            entity_instance = entity_model(**entity_dict)
            validated_data = entity_instance.model_dump()
        except Exception as e:
            return create_error_result([f"Validation failed: {str(e)}"])
        
        # 5. Use generic storage - works for ANY entity
        storage_result = create_entity(
            entity_type=entity_type,
            data=validated_data,
            context=context
        )
        
        if not storage_result.get("success", False):
            return create_error_result([storage_result.get("error", f"Failed to create {entity_type}")])
        
        # 6. Handle context switch for company creation
        if entity_type == 'company':
            from ..models.context import Context as NewContext
            result = create_success_result(
                operation="created",
                entity_name=f"{entity_type} {validated_data['name']}",
                attributes=validated_data
            )
            
            # Create new context at organization level
            new_context = NewContext(
                level=1,
                org_id=1,
                org_name=validated_data["name"],
                org_db_path=None
            )
            result.set_context_switch(new_context)
            return result
        
        # 7. Return generic success result
        return create_success_result(
            operation="created",
            entity_name=f"{entity_type} {validated_data['name']}",
            attributes=validated_data
        )
        
    except Exception as e:
        return create_error_result([f"Failed to create entity: {str(e)}"])


async def add_handler(entity_model, entity_value, attributes, context, attribute_words=None):
    """
    Truly dynamic add handler - works for ANY entity type.
    Adds/sets attributes on existing entities.
    """
    from ..ui.results import create_success_result, create_error_result
    from ..storage.database import load_entity, save_entity, entity_exists, create_default_entity_data
    from ..handlers.utils import get_company_name_from_context
    
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to add attributes"])
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: add entity attribute=value"])
        
        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace('Entity', '').lower()
        
        # Create entity if it doesn't exist
        if not entity_exists(entity_type, company_name, context):
            default_data = create_default_entity_data(entity_type)
            save_entity(entity_type, default_data, company_name, context)
        
        # Load current entity data
        current_data = load_entity(entity_type, company_name, context) or {}
        
        # Create updated data with new attributes
        updated_data = current_data.copy()
        updated_data.update(attributes)
        updated_data['updated_at'] = datetime.now().isoformat()
        
        # Save the updated entity
        save_result = save_entity(entity_type, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_type} data")])
        
        return create_success_result(
            operation="added",
            entity_name=entity_type,
            attributes=attributes
        )
        
    except Exception as e:
        return create_error_result([f"Failed to add attributes: {str(e)}"])


async def update_handler(entity_model, entity_value, attributes, context, attribute_words=None):
    """
    Truly dynamic update handler - works for ANY entity type.
    Updates existing attributes on entities.
    """
    from ..ui.results import create_success_result, create_error_result
    from ..storage.database import load_entity, save_entity, entity_exists
    from ..handlers.utils import get_company_name_from_context
    
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to update attributes"])
        
        if not attributes:
            return create_error_result(["No attributes specified. Use format: update entity attribute=value"])
        
        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace('Entity', '').lower()
        
        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return create_error_result([f"Entity '{entity_type}' does not exist for company '{company_name}'"])
        
        # Load current entity data
        current_data = load_entity(entity_type, company_name, context)
        if current_data is None:
            return create_error_result([f"No data found for {entity_type}"])
        
        # Create updated data
        updated_data = current_data.copy()
        updated_data.update(attributes)
        updated_data['updated_at'] = datetime.now().isoformat()
        
        # Save the updated entity
        save_result = save_entity(entity_type, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_type} data")])
        
        return create_success_result(
            operation="updated",
            entity_name=entity_type,
            attributes=attributes
        )
        
    except Exception as e:
        return create_error_result([f"Failed to update attributes: {str(e)}"])


async def show_handler(entity_model, entity_value, attributes, context, attribute_words=None):
    """
    Truly dynamic show handler - works for ANY entity type.
    Displays entity data or specific attributes.
    """
    from ..ui.results import create_success_result, create_error_result
    from ..storage.database import load_entity, entity_exists
    from ..handlers.utils import get_company_name_from_context, format_entity_data_for_display
    
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to view entities"])
        
        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace('Entity', '').lower()
        
        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return create_error_result([f"Entity '{entity_type}' does not exist for company '{company_name}'"])
        
        # Load entity data
        entity_data = load_entity(entity_type, company_name, context)
        if entity_data is None:
            return create_error_result([f"No data found for {entity_type}"])
        
        # Format data for display
        specific_attributes = attribute_words if attribute_words else None
        formatted_data = format_entity_data_for_display(entity_data, specific_attributes)
        
        return create_success_result(
            operation="displayed",
            entity_name=entity_type,
            attributes={"data": formatted_data}
        )
        
    except Exception as e:
        return create_error_result([f"Failed to show entity data: {str(e)}"])


async def delete_handler(entity_model, entity_value, attributes, context, attribute_words=None):
    """
    Truly dynamic delete handler - works for ANY entity type.
    Removes attribute values from entities.
    """
    from ..ui.results import create_success_result, create_error_result
    from ..storage.database import load_entity, save_entity, entity_exists
    from ..handlers.utils import get_company_name_from_context
    
    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(["Must be in organization context to delete attributes"])
        
        # Check if we have specific attributes to delete
        if not attribute_words:
            return create_error_result(["No attributes specified to delete. Use format: delete entity attribute"])
        
        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace('Entity', '').lower()
        
        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return create_error_result([f"Entity '{entity_type}' does not exist for company '{company_name}'"])
        
        # Load current entity data
        current_data = load_entity(entity_type, company_name, context)
        if current_data is None:
            return create_error_result([f"No data found for {entity_type}"])
        
        # Remove the specified attributes
        updated_data = current_data.copy()
        removed_attributes = []
        
        for attr_name in attribute_words:
            if attr_name in updated_data:
                if entity_type == "metadata":
                    # For metadata, remove the key entirely
                    del updated_data[attr_name]
                else:
                    # For other entities, set to null
                    updated_data[attr_name] = None
                removed_attributes.append(attr_name)
        
        if not removed_attributes:
            return create_error_result([f"None of the specified attributes exist in {entity_type}: {', '.join(attribute_words)}"])
        
        # Update timestamp
        if 'updated_at' in updated_data:
            updated_data['updated_at'] = datetime.now().isoformat()
        
        # Save the updated entity
        save_result = save_entity(entity_type, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result([save_result.get("error", f"Failed to save {entity_type} data")])
        
        return create_success_result(
            operation="deleted",
            entity_name=entity_type,
            attributes={"removed_attributes": ", ".join(removed_attributes)}
        )
        
    except Exception as e:
        return create_error_result([f"Failed to delete attributes: {str(e)}"])