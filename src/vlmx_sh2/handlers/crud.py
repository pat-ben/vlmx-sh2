"""
Truly dynamic CRUD handlers for VLMX DSL.

Each handler works with ANY entity type without hardcoded entity-specific logic.
Uses entity_model metadata and generic storage functions to provide
unified behavior across all entity-field combinations.
"""

from datetime import datetime
from ..models.context import ContextLevel
from ..models.results import CommandResult, ErrorResult


async def create_handler(
    entity_model=None, entity_value=None, fields=None, context=None, field_words=None, parsed_command=None
):
    """
    Truly dynamic create handler - works for ANY entity type.
    """
    from ..storage.database import create_entity

    if entity_model is None:
        raise ValueError("entity_model is required")
    entity_type = entity_model.__name__.replace("Entity", "").lower()

    try:
        # Prepare entity data with user-provided fields
        if fields is None:
            fields = {}
        
        entity_data = {
            "name": entity_value
            or f"{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        entity_data.update(fields)

        # Validate using the entity model (Pydantic validation applies defaults automatically)
        try:
            if entity_model is None:
                raise ValueError("entity_model is required for validation")
            entity_instance = entity_model(**entity_data)
            validated_data = entity_instance.model_dump()
        except Exception as e:
            return ErrorResult(
                errors=[f"Validation failed: {str(e)}"],
                suggestions=["Check field names and value formats"]
            )

        # Use generic storage - works for ANY entity
        if context is None:
            from ..models.context import Context
            context = Context(level=ContextLevel.SYS)  # Default system context
            
        storage_result = create_entity(
            entity_type=entity_type, data=validated_data, context=context
        )

        if storage_result is None or not storage_result.get("success", False):
            error_msg = storage_result.get("error", f"Failed to create {entity_type}") if storage_result else f"Failed to create {entity_type}"
            return ErrorResult(
                errors=[error_msg],
                suggestions=["Check database connection and permissions"]
            )

        # Handle context switch for company creation (navigation behavior)
        if entity_type == "company":
            from ..models.context import Context as NewContext

            # For company creation, include context switch information in data
            result = CommandResult(
                success=True,
                message=f"Created {entity_type} {validated_data['name']}",
                data={
                    "entity_type": entity_type,
                    "entity_name": validated_data['name'],
                    "fields": validated_data,
                    "context_switch": {
                        "level": "ORG",
                        "org_id": 1,
                        "org_name": validated_data["name"],
                        "org_db_path": None
                    }
                }
            )
            return result

        # Return generic success result
        return CommandResult(
            success=True,
            message=f"Created {entity_type} {validated_data['name']}",
            data={
                "entity_type": entity_type,
                "entity_name": validated_data['name'],
                "fields": validated_data
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create entity: {str(e)}"],
            suggestions=["Check input values and system status"]
        )


async def add_handler(
    entity_model, entity_value, fields, context, field_words=None, parsed_command=None
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
    # ErrorResult and CommandResult already imported at module level

    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return ErrorResult(
                errors=["Must be in organization context to add fields"],
                suggestions=["Navigate to an organization first"]
            )

        if not fields:
            return ErrorResult(
                errors=["No fields specified. Use format: add entity field=value"],
                suggestions=["Try: add brand name=value"]
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
                return ErrorResult(
                    errors=[f"Failed to create default entity: {str(e)}"],
                    suggestions=["Check entity model configuration"]
                )
                
            save_entity(entity_type, default_data, company_name, context)

        # Load current entity data
        current_data = load_entity(entity_type, company_name, context) or {}

        # Create updated data with new fields
        updated_data = current_data.copy()
        updated_data.update(fields)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = save_entity(entity_type, updated_data, company_name, context)
        if not save_result.get("success", False):
            return ErrorResult(
                errors=[save_result.get("error", f"Failed to save {entity_type} data")],
                suggestions=["Check database permissions and disk space"]
            )

        return CommandResult(
            success=True,
            message=f"Added fields to {entity_type}",
            data={
                "entity_type": entity_type,
                "added_fields": fields
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to add fields: {str(e)}"],
            suggestions=["Check input format and system status"]
        )


async def update_handler(
    entity_model, entity_value, fields, context, field_words=None, parsed_command=None
):
    """
    Truly dynamic update handler - works for ANY entity type.
    Updates existing fields on entities.
    """
    from ..handlers.utils import get_company_name_from_context
    from ..storage.database import entity_exists, load_entity, save_entity
    # ErrorResult and CommandResult already imported at module level

    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return ErrorResult(
                errors=["Must be in organization context to update fields"],
                suggestions=["Navigate to an organization first"]
            )

        if not fields:
            return ErrorResult(
                errors=["No fields specified. Use format: update entity field=value"],
                suggestions=["Try: update brand name=newvalue"]
            )

        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace("Entity", "").lower()

        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return ErrorResult(
                errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
                suggestions=[f"Create the {entity_type} first or check the entity name"]
            )

        # Load current entity data
        current_data = load_entity(entity_type, company_name, context)
        if current_data is None:
            return ErrorResult(
                errors=[f"No data found for {entity_type}"],
                suggestions=["Check entity exists and database connection"]
            )

        # Create updated data
        updated_data = current_data.copy()
        updated_data.update(fields)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = save_entity(entity_type, updated_data, company_name, context)
        if not save_result.get("success", False):
            return ErrorResult(
                errors=[save_result.get("error", f"Failed to save {entity_type} data")],
                suggestions=["Check database permissions and disk space"]
            )

        return CommandResult(
            success=True,
            message=f"Updated {entity_type}",
            data={
                "entity_type": entity_type,
                "updated_fields": fields
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to update fields: {str(e)}"],
            suggestions=["Check input format and system status"]
        )


async def show_handler(
    entity_model, entity_value, fields, context, field_words=None, parsed_command=None
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
    # ErrorResult and CommandResult already imported at module level

    try:
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return ErrorResult(
                errors=["Must be in organization context to view entities"],
                suggestions=["Navigate to an organization first"]
            )

        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace("Entity", "").lower()

        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return ErrorResult(
                errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
                suggestions=[f"Create the {entity_type} first or check the entity name"]
            )

        # Load entity data
        entity_data = load_entity(entity_type, company_name, context)
        if entity_data is None:
            return ErrorResult(
                errors=[f"No data found for {entity_type}"],
                suggestions=["Check entity exists and database connection"]
            )

        # Format data for display
        specific_fields = field_words if field_words else None
        formatted_data = format_entity_data_for_display(
            entity_data, specific_fields
        )

        return CommandResult(
            success=True,
            message=f"Displaying {entity_type} data",
            data={
                "entity_type": entity_type,
                "formatted_data": formatted_data,
                "raw_data": entity_data
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to show entity data: {str(e)}"],
            suggestions=["Check entity exists and database connection"]
        )


async def delete_handler(
    entity_model, entity_value, fields, context, field_words=None, parsed_command=None
):
    """
    Truly dynamic delete handler - works for ANY entity type.
    
    Behavior depends on context level:
    - SYS level: Deletes entire entity (e.g., delete company "ACME Corp")
    - ORG/APP level: Deletes specific fields from entity (e.g., delete company vision)
    """
    from ..handlers.utils import get_company_name_from_context
    from ..storage.database import entity_exists, load_entity, save_entity, delete_entity, find_company_by_name
    # ErrorResult and CommandResult already imported at module level

    try:
        # SYS LEVEL: Delete entire entity
        if context.level == ContextLevel.SYS:
            if not entity_value:
                return ErrorResult(
                    errors=["Entity name required for deletion at system level"],
                    suggestions=["Specify entity name: delete company 'CompanyName'"]
                )
            
            # Determine entity type from entity_model
            entity_type = entity_model.__name__.replace("Entity", "").lower()
            
            # For company deletion, use intelligent name matching
            if entity_type == "company":
                actual_company_name = find_company_by_name(entity_value, context)
                if not actual_company_name:
                    return ErrorResult(
                        errors=[f"Company '{entity_value}' not found"],
                        suggestions=["Check company name spelling or list existing companies"]
                    )
                entity_name_to_delete = actual_company_name
            else:
                entity_name_to_delete = entity_value
            
            # Delete the entire entity
            delete_result = delete_entity(entity_type, entity_name_to_delete, context)
            
            if delete_result.get("success", False):
                return CommandResult(
                    success=True,
                    message=f"Deleted {entity_type} {entity_name_to_delete}",
                    data={
                        "entity_type": entity_type,
                        "deleted_entity": entity_name_to_delete,
                        "delete_message": delete_result.get("message", "Successfully deleted")
                    }
                )
            else:
                return ErrorResult(
                    errors=[delete_result.get("error", f"Failed to delete {entity_type}")],
                    suggestions=["Check if entity exists and database permissions"]
                )
        
        # ORG/APP LEVEL: Delete specific fields from entity OR delete current company
        else:
            # Get current company name from context
            company_name = get_company_name_from_context(context)
            if not company_name:
                return ErrorResult(
                    errors=["Must be in organization context to delete fields"],
                    suggestions=["Navigate to an organization first"]
                )

            # Check if user wants to delete the entire current company
            if entity_value and (entity_value.lower() == company_name.lower() or 
                                find_company_by_name(entity_value, context) == company_name):
                # Delete the entire current company and return to SYS level
                delete_result = delete_entity("company", company_name, context)
                
                if delete_result.get("success", False):
                    result = CommandResult(
                        success=True,
                        message=f"Deleted company {company_name}",
                        data={
                            "entity_type": "company",
                            "deleted_entity": company_name,
                            "delete_message": delete_result.get("message", "Successfully deleted"),
                            "context_changed": "Returned to system level",
                            "context_switch": {
                                "level": "SYS",
                                "org_id": None,
                                "org_name": None,
                                "org_db_path": None
                            }
                        }
                    )
                    return result
                else:
                    return ErrorResult(
                        errors=[delete_result.get("error", "Failed to delete company")],
                        suggestions=["Check if company exists and database permissions"]
                    )

            # Check if we have specific fields to delete
            if not field_words:
                return ErrorResult(
                    errors=["No fields specified to delete. Use format: delete entity field"],
                    suggestions=["Try: delete brand vision"]
                )

            # Determine entity type from entity_model
            entity_type = entity_model.__name__.replace("Entity", "").lower()

            # Check if entity exists
            if not entity_exists(entity_type, company_name, context):
                return ErrorResult(
                    errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
                    suggestions=[f"Create the {entity_type} first or check the entity name"]
                )

            # Load current entity data
            current_data = load_entity(entity_type, company_name, context)
            if current_data is None:
                return ErrorResult(
                    errors=[f"No data found for {entity_type}"],
                    suggestions=["Check entity exists and database connection"]
                )

            # Remove the specified fields
            updated_data = current_data.copy()
            removed_fields = []

            for attr_name in field_words:
                if attr_name in updated_data:
                    if entity_type == "metadata":
                        # For metadata, remove the key entirely
                        del updated_data[attr_name]
                    else:
                        # For other entities, set to null
                        updated_data[attr_name] = None
                    removed_fields.append(attr_name)

            if not removed_fields:
                return ErrorResult(
                    errors=[f"None of the specified fields exist in {entity_type}: {', '.join(field_words)}"],
                    suggestions=["Check field names or show the entity to see available fields"]
                )

            # Update timestamp
            if "updated_at" in updated_data:
                updated_data["updated_at"] = datetime.now().isoformat()

            # Save the updated entity
            save_result = save_entity(entity_type, updated_data, company_name, context)
            if not save_result.get("success", False):
                return ErrorResult(
                    errors=[save_result.get("error", f"Failed to save {entity_type} data")],
                    suggestions=["Check database permissions and disk space"]
                )

            return CommandResult(
                success=True,
                message=f"Deleted fields from {entity_type}",
                data={
                    "entity_type": entity_type,
                    "removed_fields": removed_fields
                }
            )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to delete fields: {str(e)}"],
            suggestions=["Check input format and system status"]
        )

