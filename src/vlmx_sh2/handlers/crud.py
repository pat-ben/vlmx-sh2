"""
Truly dynamic CRUD handlers for VLMX DSL.

Each handler works with ANY entity type without hardcoded entity-specific logic.
Uses entity_model metadata and generic storage functions to provide
unified behavior across all entity-field combinations.
"""

from datetime import datetime
from ..models.context import ContextLevel


async def create_handler(
    entity_model=None, entity_value=None, attributes=None, context=None, attribute_words=None
):
    """
    Truly dynamic create handler - works for ANY entity type.
    """
    from ..storage.database import create_entity
    from ..ui.results import create_error_result, create_success_result

    if entity_model is None:
        raise ValueError("entity_model is required")
    entity_type = entity_model.__name__.replace("Entity", "").lower()

    try:
        # Prepare entity data with user-provided attributes
        if attributes is None:
            attributes = {}
        
        entity_data = {
            "name": entity_value
            or f"{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        entity_data.update(attributes)

        # Validate using the entity model (Pydantic validation applies defaults automatically)
        try:
            if entity_model is None:
                raise ValueError("entity_model is required for validation")
            entity_instance = entity_model(**entity_data)
            validated_data = entity_instance.model_dump()
        except Exception as e:
            return create_error_result([f"Validation failed: {str(e)}"])

        # Use generic storage - works for ANY entity
        if context is None:
            from ..models.context import Context
            context = Context(level=ContextLevel.SYS)  # Default system context
            
        storage_result = create_entity(
            entity_type=entity_type, data=validated_data, context=context
        )

        if storage_result is None or not storage_result.get("success", False):
            error_msg = storage_result.get("error", f"Failed to create {entity_type}") if storage_result else f"Failed to create {entity_type}"
            return create_error_result([error_msg])

        # Handle context switch for company creation (navigation behavior)
        if entity_type == "company":
            from ..models.context import Context as NewContext

            result = create_success_result(
                operation="created",
                entity_name=f"{entity_type} {validated_data['name']}",
                attributes=validated_data,
            )

            # Create new context at organization level
            new_context = NewContext(
                level=ContextLevel.ORG, org_id=1, org_name=validated_data["name"], org_db_path=None
            )
            result.set_context_switch(new_context)
            return result

        # Return generic success result
        return create_success_result(
            operation="created",
            entity_name=f"{entity_type} {validated_data['name']}",
            attributes=validated_data,
        )

    except Exception as e:
        return create_error_result([f"Failed to create entity: {str(e)}"])


async def add_handler(
    entity_model, entity_value, attributes, context, attribute_words=None
):
    """
    Truly dynamic add handler - works for ANY entity type.
    Adds/sets fields on existing entities.
    """
    from ..handlers.utils import get_company_name_from_context
    from ..storage.database import (
        entity_exists,
        load_entity,
        save_entity,
    )
    from ..ui.results import create_error_result, create_success_result

    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(
                ["Must be in organization context to add fields"]
            )

        if not attributes:
            return create_error_result(
                ["No fields specified. Use format: add entity field=value"]
            )

        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace("Entity", "").lower()

        # Create entity if it doesn't exist using Pydantic model defaults
        if not entity_exists(entity_type, company_name, context):
            # Create default entity data using the entity model's Pydantic defaults
            default_entity_data = {
                "name": f"default_{entity_type}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            # Validate and apply model defaults
            try:
                entity_instance = entity_model(**default_entity_data)
                default_data = entity_instance.model_dump()
            except Exception as e:
                return create_error_result([f"Failed to create default entity: {str(e)}"])
                
            save_entity(entity_type, default_data, company_name, context)

        # Load current entity data
        current_data = load_entity(entity_type, company_name, context) or {}

        # Create updated data with new fields
        updated_data = current_data.copy()
        updated_data.update(attributes)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = save_entity(entity_type, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result(
                [save_result.get("error", f"Failed to save {entity_type} data")]
            )

        return create_success_result(
            operation="added", entity_name=entity_type, attributes=attributes
        )

    except Exception as e:
        return create_error_result([f"Failed to add fields: {str(e)}"])


async def update_handler(
    entity_model, entity_value, attributes, context, attribute_words=None
):
    """
    Truly dynamic update handler - works for ANY entity type.
    Updates existing fields on entities.
    """
    from ..handlers.utils import get_company_name_from_context
    from ..storage.database import entity_exists, load_entity, save_entity
    from ..ui.results import create_error_result, create_success_result

    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(
                ["Must be in organization context to update fields"]
            )

        if not attributes:
            return create_error_result(
                ["No fields specified. Use format: update entity field=value"]
            )

        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace("Entity", "").lower()

        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return create_error_result(
                [f"Entity '{entity_type}' does not exist for company '{company_name}'"]
            )

        # Load current entity data
        current_data = load_entity(entity_type, company_name, context)
        if current_data is None:
            return create_error_result([f"No data found for {entity_type}"])

        # Create updated data
        updated_data = current_data.copy()
        updated_data.update(attributes)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = save_entity(entity_type, updated_data, company_name, context)
        if not save_result.get("success", False):
            return create_error_result(
                [save_result.get("error", f"Failed to save {entity_type} data")]
            )

        return create_success_result(
            operation="updated", entity_name=entity_type, attributes=attributes
        )

    except Exception as e:
        return create_error_result([f"Failed to update fields: {str(e)}"])


async def show_handler(
    entity_model, entity_value, attributes, context, attribute_words=None
):
    """
    Truly dynamic show handler - works for ANY entity type.
    Displays entity data or specific fields.
    """
    from ..handlers.utils import (
        format_entity_data_for_display,
        get_company_name_from_context,
    )
    from ..storage.database import entity_exists, load_entity
    from ..ui.results import create_error_result, create_success_result

    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return create_error_result(
                ["Must be in organization context to view entities"]
            )

        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace("Entity", "").lower()

        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return create_error_result(
                [f"Entity '{entity_type}' does not exist for company '{company_name}'"]
            )

        # Load entity data
        entity_data = load_entity(entity_type, company_name, context)
        if entity_data is None:
            return create_error_result([f"No data found for {entity_type}"])

        # Format data for display
        specific_fields = attribute_words if attribute_words else None
        formatted_data = format_entity_data_for_display(
            entity_data, specific_fields
        )

        return create_success_result(
            operation="displayed",
            entity_name=entity_type,
            attributes={"data": formatted_data},
        )

    except Exception as e:
        return create_error_result([f"Failed to show entity data: {str(e)}"])


async def delete_handler(
    entity_model, entity_value, attributes, context, attribute_words=None
):
    """
    Truly dynamic delete handler - works for ANY entity type.
    
    Behavior depends on context level:
    - SYS level: Deletes entire entity (e.g., delete company "ACME Corp")
    - ORG/APP level: Deletes specific fields from entity (e.g., delete company vision)
    """
    from ..handlers.utils import get_company_name_from_context
    from ..storage.database import entity_exists, load_entity, save_entity, delete_entity, find_company_by_name
    from ..ui.results import create_error_result, create_success_result

    try:
        # SYS LEVEL: Delete entire entity
        if context.level == ContextLevel.SYS:
            if not entity_value:
                return create_error_result(["Entity name required for deletion at system level"])
            
            # Determine entity type from entity_model
            entity_type = entity_model.__name__.replace("Entity", "").lower()
            
            # For company deletion, use intelligent name matching
            if entity_type == "company":
                actual_company_name = find_company_by_name(entity_value, context)
                if not actual_company_name:
                    return create_error_result([f"Company '{entity_value}' not found"])
                entity_name_to_delete = actual_company_name
            else:
                entity_name_to_delete = entity_value
            
            # Delete the entire entity
            delete_result = delete_entity(entity_type, entity_name_to_delete, context)
            
            if delete_result.get("success", False):
                return create_success_result(
                    operation="deleted",
                    entity_name=f"{entity_type} {entity_name_to_delete}",
                    attributes={
                        "type": entity_type,
                        "deleted_entity": entity_name_to_delete,
                        "message": delete_result.get("message", "Successfully deleted")
                    }
                )
            else:
                return create_error_result([delete_result.get("error", f"Failed to delete {entity_type}")])
        
        # ORG/APP LEVEL: Delete specific fields from entity OR delete current company
        else:
            # Get current company name from context
            company_name = get_company_name_from_context(context)
            if not company_name:
                return create_error_result(
                    ["Must be in organization context to delete fields"]
                )

            # Check if user wants to delete the entire current company
            if entity_value and (entity_value.lower() == company_name.lower() or 
                                find_company_by_name(entity_value, context) == company_name):
                # Delete the entire current company and return to SYS level
                delete_result = delete_entity("company", company_name, context)
                
                if delete_result.get("success", False):
                    result = create_success_result(
                        operation="deleted",
                        entity_name=f"company {company_name}",
                        attributes={
                            "type": "company",
                            "deleted_entity": company_name,
                            "message": delete_result.get("message", "Successfully deleted"),
                            "context_changed": "Returned to system level"
                        }
                    )
                    # Set context switch back to SYS level since company no longer exists
                    from ..models.context import Context as NewContext
                    new_context = NewContext(
                        level=ContextLevel.SYS,
                        org_id=None,
                        org_name=None,
                        org_db_path=None
                    )
                    result.set_context_switch(new_context)
                    return result
                else:
                    return create_error_result([delete_result.get("error", "Failed to delete company")])

            # Check if we have specific fields to delete
            if not attribute_words:
                return create_error_result(
                    [
                        "No fields specified to delete. Use format: delete entity field"
                    ]
                )

            # Determine entity type from entity_model
            entity_type = entity_model.__name__.replace("Entity", "").lower()

            # Check if entity exists
            if not entity_exists(entity_type, company_name, context):
                return create_error_result(
                    [f"Entity '{entity_type}' does not exist for company '{company_name}'"]
                )

            # Load current entity data
            current_data = load_entity(entity_type, company_name, context)
            if current_data is None:
                return create_error_result([f"No data found for {entity_type}"])

            # Remove the specified fields
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
                return create_error_result(
                    [
                        f"None of the specified fields exist in {entity_type}: {', '.join(attribute_words)}"
                    ]
                )

            # Update timestamp
            if "updated_at" in updated_data:
                updated_data["updated_at"] = datetime.now().isoformat()

            # Save the updated entity
            save_result = save_entity(entity_type, updated_data, company_name, context)
            if not save_result.get("success", False):
                return create_error_result(
                    [save_result.get("error", f"Failed to save {entity_type} data")]
                )

            return create_success_result(
                operation="deleted",
                entity_name=entity_type,
                attributes={"removed_attributes": ", ".join(removed_attributes)},
            )

    except Exception as e:
        return create_error_result([f"Failed to delete fields: {str(e)}"])

