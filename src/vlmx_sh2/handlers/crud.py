"""
Truly dynamic CRUD handlers.

Each handler works with ANY entity type without hardcoded entity-specific logic.
Uses entity_model metadata and generic storage functions to provide
unified behavior across all entity-field combinations.
"""

from datetime import datetime
from typing import Type, Optional, Dict, Any, List
from pydantic import BaseModel

from ..models.context import Context, ContextLevel
from ..models.responses import CommandResult, ErrorResult, HandlerResult
from ..models.parser.parsed_command import ParsedCommand
from vlmx_sh2.enums import Cardinality
from ..handlers.utils import get_company_name_from_context, format_entity_data_for_display
from ..storage.database import StorageInterface, entity_exists, find_company_by_name, load_all_entities
from ..storage.filters import apply_filters


# Helper functions for delete_handler
def _delete_entity_at_sys_level(
    entity_model: Type[BaseModel], 
    entity_value: str, 
    context: Context
) -> HandlerResult:
    """
    Delete entire entity at system level.
    
    Args:
        entity_model: Entity model class
        entity_value: Entity name to delete
        context: Current context
        
    Returns:
        CommandResult on success, ErrorResult on failure
    """
    
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
    delete_result = StorageInterface.delete_entity(entity_type, entity_name_to_delete, context)
    
    if delete_result.success:
        return CommandResult(
            success=True,
            message=f"Deleted {entity_type} {entity_name_to_delete}",
            data={
                "entity_type": entity_type,
                "deleted_entity": entity_name_to_delete,
                "delete_message": delete_result.message or "Successfully deleted"
            }
        )
    else:
        return ErrorResult(
            errors=[delete_result.error or f"Failed to delete {entity_type}"],
            suggestions=["Check if entity exists and database permissions"]
        )


def _delete_current_company(company_name: str, entity_value: Optional[str], context: Context) -> Optional[HandlerResult]:
    """
    Check if user wants to delete current company and handle it.
    
    Args:
        company_name: Current company name
        entity_value: Target entity value
        context: Current context
        
    Returns:
        CommandResult if company deletion handled, None if not a company deletion request
    """
    
    # Check if user wants to delete the entire current company
    if entity_value and (entity_value.lower() == company_name.lower() or 
                        find_company_by_name(entity_value, context) == company_name):
        # Delete the entire current company and return to SYS level
        delete_result = StorageInterface.delete_entity("company", company_name, context)
        
        if delete_result.success:
            return CommandResult(
                success=True,
                message=f"Deleted company {company_name}",
                data={
                    "entity_type": "company",
                    "deleted_entity": company_name,
                    "delete_message": delete_result.message or "Successfully deleted",
                    "context_changed": "Returned to system level",
                    "context_switch": {
                        "level": "SYS",
                        "org_id": None,
                        "org_name": None,
                        "org_db_path": None
                    }
                }
            )
        else:
            return ErrorResult(
                errors=[delete_result.error or "Failed to delete company"],
                suggestions=["Check if company exists and database permissions"]
            )
    
    return None


def _delete_entity_fields(
    entity_model: Type[BaseModel],
    company_name: str,
    field_words: List[str],
    context: Context
) -> HandlerResult:
    """
    Delete specific fields from an entity.
    
    Args:
        entity_model: Entity model class
        company_name: Company name for context
        field_words: List of field names to delete
        context: Current context
        
    Returns:
        CommandResult on success, ErrorResult on failure
    """
    
    entity_type = entity_model.__name__.replace("Entity", "").lower()
    
    # Check if entity exists
    if not entity_exists(entity_type, company_name, context):
        return ErrorResult(
            errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
            suggestions=[f"Create the {entity_type} first or check the entity name"]
        )
    
    # Load current entity data
    load_result = StorageInterface.load_entity(entity_type, company_name, context)
    current_data = load_result.data if load_result.success else None
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
    save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
    if not save_result.success:
        return ErrorResult(
            errors=[save_result.error or f"Failed to save {entity_type} data"],
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


async def create_handler(
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    fields: Dict[str, Any],
    context: Context,
    field_words: Optional[List[str]] = None,
    parsed_command: Optional[ParsedCommand] = None
) -> HandlerResult:
    """
    Handler for 'create' command - creates new entity records.
    
    Creates entities using the provided field values. For single cardinality
    entities (metadata, identity), ensures only one record exists per company.
    For multi cardinality entities (offering, target, values), allows multiple records.
    
    Args:
        entity_model: Pydantic model class for the entity type
        entity_value: Optional entity name/identifier
        fields: Dictionary of field names to values for entity creation
        context: Current execution context (must be at ORG level)
        field_words: Optional list of field identifiers from parser
        parsed_command: Optional parsed command object with additional data
        
    Returns:
        CommandResult on successful creation, ErrorResult on failure
        
    Raises:
        Returns ErrorResult for validation errors, context errors, or storage failures
    """

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
            entity_instance = entity_model(**entity_data)
            validated_data = entity_instance.model_dump()
        except Exception as e:
            return ErrorResult(
                errors=[f"Validation failed: {str(e)}"],
                suggestions=["Check field names and value formats"]
            )

        # Use generic storage - works for ANY entity
            
        storage_result = StorageInterface.create_entity(
            entity_type=entity_type, data=validated_data, context=context
        )

        if not storage_result.success:
            return ErrorResult(
                errors=[storage_result.error or f"Failed to create {entity_type}"],
                suggestions=["Check database connection and permissions"]
            )

        # Handle context switch for company creation (navigation behavior)
        if entity_type == "company":
            from ..models.context import Context as NewContext

            # For company creation, include context switch information in data
            result = CommandResult(
                success=True,
                message=storage_result.message or f"Created {entity_type} {validated_data['name']}",
                data={
                    "entity_type": entity_type,
                    "entity_name": validated_data['name'],
                    "fields": validated_data,
                    "storage_result": storage_result.data,
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
            message=storage_result.message or f"Created {entity_type} {validated_data['name']}",
            data={
                "entity_type": entity_type,
                "entity_name": validated_data['name'],
                "fields": validated_data,
                "storage_result": storage_result.data
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create entity: {str(e)}"],
            suggestions=["Check input values and system status"]
        )


async def add_handler(
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    fields: Dict[str, Any],
    context: Context,
    field_words: Optional[List[str]] = None,
    parsed_command: Optional[ParsedCommand] = None
) -> HandlerResult:
    """
    Handler for 'add' command - adds or updates entity field values.
    
    Updates existing entity records by adding new field values or modifying
    existing ones. For single cardinality entities, updates the single record.
    For multi cardinality entities, may create new records if none match criteria.
    
    Args:
        entity_model: Pydantic model class for the entity type
        entity_value: Optional entity name/identifier for targeting specific records
        fields: Dictionary of field names to values for addition/update
        context: Current execution context (must be at ORG level)
        field_words: Optional list of field identifiers from parser
        parsed_command: Optional parsed command object with additional data
        
    Returns:
        CommandResult on successful addition, ErrorResult on failure
        
    Raises:
        Returns ErrorResult for context errors, missing entities, or storage failures
    """
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
                
            StorageInterface.save_entity(entity_type, default_data, company_name, context)

        # Load current entity data
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        current_data = load_result.data if load_result.success else {}
        
        # Ensure current_data is not None
        if current_data is None:
            current_data = {}

        # Create updated data with new fields
        updated_data = current_data.copy()
        updated_data.update(fields)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
        if not save_result.success:
            return ErrorResult(
                errors=[save_result.error or f"Failed to save {entity_type} data"],
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
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    fields: Dict[str, Any],
    context: Context,
    field_words: Optional[List[str]] = None,
    parsed_command: Optional[ParsedCommand] = None
) -> HandlerResult:
    """
    Handler for 'update' command - modifies existing entity field values.
    
    Updates existing entity records by modifying field values. Requires the
    entity to exist before updating. For single cardinality entities, updates
    the single record. For multi cardinality entities, updates matching records.
    
    Args:
        entity_model: Pydantic model class for the entity type
        entity_value: Optional entity name/identifier for targeting specific records
        fields: Dictionary of field names to new values for update
        context: Current execution context (must be at ORG level)
        field_words: Optional list of field identifiers from parser
        parsed_command: Optional parsed command object with filter criteria
        
    Returns:
        CommandResult on successful update, ErrorResult on failure
        
    Raises:
        Returns ErrorResult for context errors, missing entities, or storage failures
    """
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
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        if not load_result.success:
            return ErrorResult(
                errors=[load_result.error or f"No data found for {entity_type}"],
                suggestions=["Check entity exists and database connection"]
            )
        current_data = load_result.data

        # Create updated data
        updated_data = current_data.copy() if current_data else {}
        updated_data.update(fields)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
        if not save_result.success:
            return ErrorResult(
                errors=[save_result.error or f"Failed to save {entity_type} data"],
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
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    fields: Dict[str, Any],
    context: Context,
    field_words: Optional[List[str]] = None,
    parsed_command: Optional[ParsedCommand] = None
) -> HandlerResult:
    """
    Handler for 'show' command - displays entity data.
    
    Shows entity information with optional field filtering. For single cardinality
    entities, shows the single record. For multi cardinality entities, shows all
    records or filtered results if criteria are provided.
    
    Args:
        entity_model: Pydantic model class for the entity type
        entity_value: Optional entity name/identifier for filtering
        fields: Dictionary of field filters to apply
        context: Current execution context (must be at ORG level)
        field_words: Optional list of specific fields to display
        parsed_command: Optional parsed command object with filter criteria
        
    Returns:
        CommandResult with entity data on success, ErrorResult on failure
        
    Raises:
        Returns ErrorResult for context errors, missing entities, or storage failures
    """
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
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        entity_data = load_result.data if load_result.success else None
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


async def list_handler(
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    fields: Dict[str, Any],
    context: Context,
    field_words: Optional[List[str]] = None,
    parsed_command: Optional[ParsedCommand] = None
) -> HandlerResult:
    """
    Handler for 'list' command - lists all records of an entity type.
    
    Displays all records for multi cardinality entities with optional filtering.
    For single cardinality entities, behaves like show command. Supports
    field-based filtering and display customization.
    
    Args:
        entity_model: Pydantic model class for the entity type
        entity_value: Optional entity name/identifier for filtering
        fields: Dictionary of field filters to apply
        context: Current execution context (must be at ORG level)
        field_words: Optional list of specific fields to display
        parsed_command: Optional parsed command object with filter criteria
        
    Returns:
        CommandResult with list of entity records on success, ErrorResult on failure
        
    Raises:
        Returns ErrorResult for context errors or storage failures
    """
    try:
        # Check if this entity supports listing (MULTIPLE cardinality)
        if not hasattr(entity_model, 'cardinality') or getattr(entity_model, 'cardinality', None) != Cardinality.MULTIPLE:
            entity_type = entity_model.__name__.replace("Entity", "").lower()
            return ErrorResult(
                errors=[f"Entity '{entity_type}' does not support listing (single record entity)"],
                suggestions=[f"Use 'show {entity_type}' instead of 'list {entity_type}'"]
            )
        
        # Get current company name from context
        company_name = get_company_name_from_context(context)
        if not company_name:
            return ErrorResult(
                errors=["Must be in organization context to list entities"],
                suggestions=["Navigate to an organization first"]
            )

        # Determine entity type from entity_model
        entity_type = entity_model.__name__.replace("Entity", "").lower()

        # Load all records for this entity
        all_records = load_all_entities(entity_type, company_name, context)
        
        # Apply filters if present
        if parsed_command and parsed_command.has_filters and parsed_command.filters:
            try:
                filtered_records = apply_filters(all_records, parsed_command.filters)
            except Exception as filter_error:
                return ErrorResult(
                    errors=[f"Filter application failed: {str(filter_error)}"],
                    suggestions=["Check filter syntax and field names"]
                )
        else:
            filtered_records = all_records

        # Format results
        count = len(filtered_records)
        total_count = len(all_records)
        
        # Create display message
        if parsed_command and parsed_command.has_filters:
            message = f"Found {count} of {total_count} {entity_type} records matching filters"
        else:
            message = f"Found {count} {entity_type} records"

        return CommandResult(
            success=True,
            message=message,
            data={
                "entity_type": entity_type,
                "records": filtered_records,
                "count": count,
                "total_count": total_count,
                "filtered": parsed_command.has_filters if parsed_command else False,
                "filters": str(parsed_command.filters) if (parsed_command and parsed_command.has_filters) else None
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to list entities: {str(e)}"],
            suggestions=["Check entity type and database connection"]
        )


async def delete_handler(
    entity_model: Type[BaseModel],
    entity_value: Optional[str],
    fields: Dict[str, Any],
    context: Context,
    field_words: Optional[List[str]] = None,
    parsed_command: Optional[ParsedCommand] = None
) -> HandlerResult:
    """
    Handler for 'delete' command - removes entity records or specific fields.
    
    Supports both record deletion and field deletion. Can delete entire records
    based on criteria, or remove specific fields from existing records. For
    single cardinality entities, may delete the entire entity. For multi
    cardinality entities, can delete specific matching records.
    
    Args:
        entity_model: Pydantic model class for the entity type
        entity_value: Optional entity name/identifier for targeting specific records
        fields: Dictionary of field filters for record selection
        context: Current execution context (must be at ORG level)
        field_words: Optional list of specific fields to delete (for field deletion)
        parsed_command: Optional parsed command object with filter criteria
        
    Returns:
        CommandResult on successful deletion, ErrorResult on failure
        
    Raises:
        Returns ErrorResult for context errors, missing entities, or storage failures
    """
    try:
        # SYS LEVEL: Delete entire entity
        if context.level == ContextLevel.SYS:
            if not entity_value:
                return ErrorResult(
                    errors=["Entity name required for deletion at system level"],
                    suggestions=["Specify entity name: delete company 'CompanyName'"]
                )
            return _delete_entity_at_sys_level(entity_model, entity_value, context)
        
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
            if entity_value:  # Only call if entity_value is not None
                company_deletion_result = _delete_current_company(company_name, entity_value, context)
                if company_deletion_result:
                    return company_deletion_result

            # Check if we have specific fields to delete
            if not field_words:
                return ErrorResult(
                    errors=["No fields specified to delete. Use format: delete entity field"],
                    suggestions=["Try: delete brand vision"]
                )

            # Delete specific fields from entity
            return _delete_entity_fields(entity_model, company_name, field_words, context)

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to delete fields: {str(e)}"],
            suggestions=["Check input format and system status"]
        )

