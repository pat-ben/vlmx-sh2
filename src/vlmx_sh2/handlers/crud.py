"""
SQL-inspired CRUD handlers with clean, simple routing.

Refactored handlers using parsed command structure to eliminate all hardcoded
entity-specific logic and complex nested conditionals. Uses SQL-inspired
semantics with create/drop for structure and add/delete/reset for content.

Terminology:
- Schema: Organization database (e.g., company)
- Entity: Business entity (e.g., brand, news)  
- Field: Entity attribute (e.g., vision, mission)
"""

from datetime import datetime
from typing import Type, Optional, Dict, Any, List
from pydantic import BaseModel

from ..models.context import Context
from ..models.responses import CommandResult, ErrorResult, HandlerResult
from ..models.parser.parsed_command import ParsedCommand
from ..models.words import SchemaWord, EntityWord, FieldWord
from vlmx_sh2.enums import Cardinality
from ..handlers.utils import (
    format_entity_data_for_display,
    get_entity_type_string,
    get_target_id, 
    validate_target_exists,
    validate_org_context,
    validate_field_values_present,
    handle_storage_result
)
from ..utils.context_helpers import is_sys
from ..storage.database import StorageInterface, entity_exists, find_company_by_name, load_all_entities
from ..storage.filters import apply_filters


# ==================== HELPER FUNCTIONS ====================

def _create_default_entity_data(entity_model: Type[BaseModel], entity_type: str) -> Dict[str, Any]:
    """
    Create default entity data from Pydantic model.
    
    Args:
        entity_model: Pydantic model class
        entity_type: Entity type string (for default name)
        
    Returns:
        Dictionary with default entity data
        
    Raises:
        Exception: If model instantiation fails
    """
    default_entity_data = {
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    # For entities with a "name" field, set a default name
    if hasattr(entity_model, 'model_fields') and 'name' in entity_model.model_fields:
        default_entity_data["name"] = f"default_{entity_type}"
    
    # Create instance with minimal required data
    entity_instance = entity_model(**default_entity_data)
    
    # Get all model fields and create a complete data dict with explicit None for optional fields
    complete_data = {}
    for field_name, field_info in entity_model.model_fields.items():
        if hasattr(entity_instance, field_name):
            value = getattr(entity_instance, field_name)
            complete_data[field_name] = value
        else:
            # For fields not in the instance, explicitly set to None if they're optional
            if not field_info.is_required():
                complete_data[field_name] = None
    
    return complete_data


def _not_yet_supported_error(feature: str, suggestion: Optional[str] = None) -> ErrorResult:
    """Return standardized 'not yet supported' error."""
    return ErrorResult(
        errors=[f"{feature} not yet supported"],
        suggestions=[suggestion or f"{feature} may be available in future implementation"]
    )


def _entity_not_found_error(entity_type: str, company_name: str) -> ErrorResult:
    """Return standardized entity not found error."""
    return ErrorResult(
        errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
        suggestions=[f"Create the {entity_type} first or check the entity name"]
    )


def _validate_entity_exists(entity_type: str, company_name: str, context: Context) -> Optional[ErrorResult]:
    """
    Validate entity exists, return error if not.
    
    Returns:
        ErrorResult if entity doesn't exist, None if valid
    """
    if not entity_exists(entity_type, company_name, context):
        return _entity_not_found_error(entity_type, company_name)
    return None


def _resolve_company_name(name: Optional[str], context: Context) -> tuple[Optional[str], Optional[ErrorResult]]:
    """
    Resolve company name with intelligent matching.
    
    Returns:
        Tuple of (actual_company_name, error). If error is not None, operation failed.
    """
    if not name:
        return None, ErrorResult(
            errors=["Company name required"],
            suggestions=["Specify company name"]
        )
    
    actual_name = find_company_by_name(name, context)
    if not actual_name:
        return None, ErrorResult(
            errors=[f"Company '{name}' not found"],
            suggestions=["Check company name spelling or list existing companies"]
        )
    
    return actual_name, None


# ==================== STRUCTURE OPERATIONS ====================

async def create_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Create schema or entity structure."""
    
    error = validate_target_exists(parsed_command)
    if error:
        return error
    
    assert parsed_command.target is not None  # Validated by validate_target_exists
    target_id = get_target_id(parsed_command.target)
    target_name = parsed_command.target_name
    field_values = parsed_command.field_values
    
    if isinstance(parsed_command.target, SchemaWord):
        return await _create_schema(target_id, target_name, field_values, context)
    
    elif isinstance(parsed_command.target, EntityWord):
        return _not_yet_supported_error(
            "Entity structure creation", 
            "Entity structures are currently defined in code"
        )
    
    elif isinstance(parsed_command.target, FieldWord):
        return _not_yet_supported_error(
            "Field structure creation",
            "Field structures are currently defined in entity models"
        )
    
    else:
        return ErrorResult(errors=["Invalid target type for create operation"])


async def drop_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Drop schema or entity structure."""
    
    error = validate_target_exists(parsed_command)
    if error:
        return error
    
    assert parsed_command.target is not None  # Validated by validate_target_exists
    target_id = get_target_id(parsed_command.target)
    target_name = parsed_command.target_name
    
    if isinstance(parsed_command.target, SchemaWord):
        return await _drop_schema(target_id, target_name, context)
    
    elif isinstance(parsed_command.target, EntityWord):
        return _not_yet_supported_error(
            "Entity structure deletion",
            "Entity structures are currently defined in code"
        )
    
    elif isinstance(parsed_command.target, FieldWord):
        return _not_yet_supported_error(
            "Field structure deletion", 
            "Field structures are currently defined in entity models"
        )
    
    else:
        return ErrorResult(errors=["Invalid target type for drop operation"])


# ==================== CONTENT OPERATIONS ====================

async def add_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Add or set field values."""
    
    error = validate_field_values_present(parsed_command)
    if error:
        return error
    
    company_name, error = validate_org_context(context)
    if error:
        return error
    
    assert company_name is not None  # Validated by validate_org_context
    assert parsed_command.target_model is not None  # Required for add operations
    entity_type = get_entity_type_string(parsed_command.target_model)
    fields = parsed_command.field_values
    filters = parsed_command.filters
    
    return await _add_field_values(
        entity_type=entity_type,
        fields=fields,
        filters=filters,
        company_name=company_name,
        context=context,
        entity_model=parsed_command.target_model
    )


async def delete_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Delete data (content, not structure)."""
    
    company_name, error = validate_org_context(context)
    if error:
        return error
    
    assert company_name is not None  # Validated by validate_org_context
    assert parsed_command.target_model is not None  # Required for delete operations
    entity_type = get_entity_type_string(parsed_command.target_model)
    field_words = parsed_command.field_words
    filters = parsed_command.filters
    
    if field_words:
        return await _delete_field_values(
            entity_type=entity_type,
            field_names=field_words,
            filters=filters,
            company_name=company_name,
            context=context
        )
    
    elif filters:
        cardinality = getattr(parsed_command.target_model, 'cardinality', Cardinality.SINGLE) if parsed_command.target_model else Cardinality.SINGLE
        if cardinality == Cardinality.SINGLE:
            return ErrorResult(errors=["Cannot delete rows from single-record entity"])
        
        return await _delete_rows(
            entity_type=entity_type,
            filters=filters,
            company_name=company_name,
            context=context
        )
    
    else:
        return await _delete_entity_content(
            entity_type=entity_type,
            company_name=company_name,
            context=context
        )


async def reset_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Reset entity or fields to default values."""
    
    company_name, error = validate_org_context(context)
    if error:
        return error
    
    assert company_name is not None  # Validated by validate_org_context
    assert parsed_command.target_model is not None  # Required for reset operations
    entity_type = get_entity_type_string(parsed_command.target_model)
    field_words = parsed_command.field_words
    filters = parsed_command.filters
    
    if field_words:
        return await _reset_field_values(
            entity_type=entity_type,
            field_names=field_words,
            filters=filters,
            company_name=company_name,
            context=context,
            entity_model=parsed_command.target_model
        )
    else:
        return await _reset_entity_content(
            entity_type=entity_type,
            company_name=company_name,
            context=context,
            entity_model=parsed_command.target_model
        )


async def show_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Display data with optional field selection and filtering."""
    
    if isinstance(parsed_command.target, SchemaWord):
        assert parsed_command.target is not None  # Checked by isinstance
        target_id = get_target_id(parsed_command.target)
        target_name = parsed_command.target_name
        return await _show_schema_info(target_id, target_name, context)
    
    company_name, error = validate_org_context(context)
    if error:
        return error
    
    assert company_name is not None  # Validated by validate_org_context
    assert parsed_command.target_model is not None  # Required for show operations
    entity_type = get_entity_type_string(parsed_command.target_model)
    field_names = parsed_command.field_words
    filters = parsed_command.filters
    
    return await _show_entity(
        entity_type=entity_type,
        field_names=field_names,
        filters=filters,
        company_name=company_name,
        context=context,
        entity_model=parsed_command.target_model
    )


# ==================== SCHEMA OPERATION HELPERS ====================

async def _create_schema(
    target_id: str,
    name: Optional[str], 
    fields: Dict[str, Any], 
    context: Context
) -> HandlerResult:
    """Create schema (organization database)."""
    
    entity_type = target_id
    
    try:
        # Prepare entity data with user-provided fields
        entity_data = {
            "name": name or f"{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        entity_data.update(fields)

        # Use generic storage - simplified validation
        storage_result = StorageInterface.create_entity(
            entity_type=entity_type, 
            data=entity_data, 
            context=context
        )

        # Handle context switch for company creation (navigation behavior)
        if entity_type == "company":
            return handle_storage_result(
                storage_result,
                storage_result.message or f"Created {entity_type} {entity_data['name']}",
                entity_type,
                {
                    "entity_name": entity_data['name'],
                    "fields": entity_data,
                    "storage_result": storage_result.data,
                    "context_switch": {
                        "level": "ORG",
                        "org_id": 1,
                        "org_name": entity_data["name"],
                        "org_db_path": None
                    }
                }
            )

        # Return generic success result using utility
        return handle_storage_result(
            storage_result,
            storage_result.message or f"Created {entity_type} {entity_data['name']}",
            entity_type,
            {
                "entity_name": entity_data['name'],
                "fields": entity_data,
                "storage_result": storage_result.data
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create entity: {str(e)}"],
            suggestions=["Check input values and system status"]
        )


async def _drop_schema(target_id: str, name: Optional[str], context: Context) -> HandlerResult:
    """Drop schema (organization database)."""
    
    if not is_sys(context):
        return ErrorResult(
            errors=["Can only drop schemas from system level"],
            suggestions=["Use 'cd' to navigate to system level first"]
        )
    
    actual_company_name, error = _resolve_company_name(name, context)
    if error:
        return error
    
    assert actual_company_name is not None  # Guaranteed by _resolve_company_name success
    # Delete the entire entity
    delete_result = StorageInterface.delete_entity(target_id, actual_company_name, context)
    
    return handle_storage_result(
        delete_result,
        f"Dropped schema {actual_company_name}",
        target_id,
        {
            "deleted_entity": actual_company_name,
            "delete_message": delete_result.message or "Successfully deleted"
        }
    )


async def _show_schema_info(target_id: str, name: Optional[str], context: Context) -> HandlerResult:
    """Show schema information."""
    
    actual_company_name, error = _resolve_company_name(name, context)
    if error:
        return error
    
    assert actual_company_name is not None  # Guaranteed by _resolve_company_name success
    # Load schema data
    load_result = StorageInterface.load_entity(target_id, actual_company_name, context)
    if not load_result.success or not load_result.data:
        return ErrorResult(
            errors=[f"Failed to load {target_id} data"],
            suggestions=["Check if schema exists and database connection"]
        )
    
    return CommandResult(
        success=True,
        message=f"Schema information for {actual_company_name}",
        data={
            "entity_type": target_id,
            "entity_name": actual_company_name,
            "schema_info": load_result.data,
            "formatted_data": format_entity_data_for_display(load_result.data)
        }
    )


async def _create_entity_structure(entity_word: EntityWord, context: Context) -> HandlerResult:
    """Create entity structure (future implementation)."""
    return _not_yet_supported_error(
        "Entity structure creation", 
        "Use existing entity types or wait for future implementation"
    )


async def _drop_entity_structure(entity_word: EntityWord, context: Context) -> HandlerResult:
    """Drop entity structure (future implementation)."""
    return _not_yet_supported_error(
        "Entity structure deletion",
        "Use existing entity types or wait for future implementation"
    )


# ==================== ENTITY CONTENT OPERATION HELPERS ====================

async def _add_field_values(
    entity_type: str,
    fields: Dict[str, str],
    filters: Optional[Any],
    company_name: str,
    context: Context,
    entity_model: Optional[Type[BaseModel]] = None
) -> HandlerResult:
    """Add/update field values, optionally filtered."""
    
    try:
        
        # Create entity if it doesn't exist using Pydantic model defaults
        if not entity_exists(entity_type, company_name, context):
            try:
                if entity_model is None:
                    return ErrorResult(
                        errors=["Entity model is required for default creation"],
                        suggestions=["Check entity model configuration"]
                    )
                
                default_data = _create_default_entity_data(entity_model, entity_type)
            except Exception as e:
                return ErrorResult(
                    errors=[f"Failed to create default entity: {str(e)}"],
                    suggestions=["Check entity model configuration"]
                )
                
            StorageInterface.save_entity(entity_type, default_data, company_name, context)

        # Load current entity data
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        current_data = load_result.data if (load_result.success and load_result.data) else {}

        # Create updated data with new fields
        updated_data = current_data.copy()
        updated_data.update(fields)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
        
        return handle_storage_result(
            save_result,
            f"Added fields to {entity_type}",
            entity_type,
            {"added_fields": fields}
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to add fields: {str(e)}"],
            suggestions=["Check input format and system status"]
        )


async def _delete_field_values(
    entity_type: str,
    field_names: List[str],
    filters: Optional[Any],
    company_name: str,
    context: Context
) -> HandlerResult:
    """Delete specific field values, optionally filtered."""
    
    error = _validate_entity_exists(entity_type, company_name, context)
    if error:
        return error
    
    # Load current entity data
    load_result = StorageInterface.load_entity(entity_type, company_name, context)
    current_data = load_result.data if (load_result.success and load_result.data) else {}
    if not current_data:
        return ErrorResult(
            errors=[f"No data found for {entity_type}"],
            suggestions=["Check entity exists and database connection"]
        )
    
    # Remove the specified fields
    updated_data = current_data.copy()
    removed_fields = [field for field in field_names if field in updated_data]
    
    if not removed_fields:
        return ErrorResult(
            errors=[f"None of the specified fields exist in {entity_type}: {', '.join(field_names)}"],
            suggestions=["Check field names or show the entity to see available fields"]
        )
    
    for field_name in removed_fields:
        updated_data[field_name] = None
    
    # Update timestamp
    if "updated_at" in updated_data:
        updated_data["updated_at"] = datetime.now().isoformat()
    
    # Save the updated entity
    save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
    
    return handle_storage_result(
        save_result,
        f"Deleted fields from {entity_type}",
        entity_type,
        {"removed_fields": removed_fields}
    )


async def _delete_rows(
    entity_type: str,
    filters: Any,
    company_name: str,
    context: Context
) -> HandlerResult:
    """Delete rows matching filters."""
    
    return _not_yet_supported_error(
        "Row deletion with filters",
        "Use field deletion or reset entity for now"
    )


async def _delete_entity_content(
    entity_type: str,
    company_name: str,
    context: Context
) -> HandlerResult:
    """Delete all entity content."""
    
    # Delete all entity content
    delete_result = StorageInterface.delete_entity(entity_type, company_name, context)
    
    return handle_storage_result(
        delete_result,
        f"Deleted all {entity_type} data",
        entity_type,
        {"operation": "delete_all"}
    )


async def _reset_entity_content(
    entity_type: str,
    company_name: str,
    context: Context,
    entity_model: Type[BaseModel]
) -> HandlerResult:
    """Reset entity to defaults."""
    
    try:
        default_data = _create_default_entity_data(entity_model, entity_type)
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to generate defaults: {str(e)}"],
            suggestions=["Check entity model configuration"]
        )
    
    # Save the default entity
    save_result = StorageInterface.save_entity(entity_type, default_data, company_name, context)
    
    return handle_storage_result(
        save_result,
        f"Reset {entity_type} to defaults",
        entity_type,
        {"operation": "reset_to_defaults"}
    )


async def _reset_field_values(
    entity_type: str,
    field_names: List[str],
    filters: Optional[Any],
    company_name: str,
    context: Context,
    entity_model: Type[BaseModel]
) -> HandlerResult:
    """Reset specific fields to defaults."""
    
    # Get default values for the fields from the model
    try:
        default_instance = entity_model()
        default_data = default_instance.model_dump()
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to get default values: {str(e)}"],
            suggestions=["Check entity model configuration"]
        )
    
    # Load current entity data
    load_result = StorageInterface.load_entity(entity_type, company_name, context)
    current_data = load_result.data if (load_result.success and load_result.data) else {}
    
    # Reset specified fields to defaults
    updated_data = current_data.copy()
    reset_fields = [field for field in field_names if field in default_data]
    
    if not reset_fields:
        return ErrorResult(
            errors=[f"None of the specified fields have default values: {', '.join(field_names)}"],
            suggestions=["Check field names or use delete to clear fields"]
        )
    
    updated_data.update({field: default_data[field] for field in reset_fields})
    
    # Update timestamp
    updated_data["updated_at"] = datetime.now().isoformat()
    
    # Save the updated entity
    save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
    
    return handle_storage_result(
        save_result,
        f"Reset fields in {entity_type} to defaults",
        entity_type,
        {"reset_fields": reset_fields}
    )


async def _show_entity(
    entity_type: str,
    field_names: Optional[List[str]],
    filters: Optional[Any],
    company_name: str,
    context: Context,
    entity_model: Optional[Type[BaseModel]] = None
) -> HandlerResult:
    """Show entity data with optional field/row filtering."""
    
    try:

        error = _validate_entity_exists(entity_type, company_name, context)
        if error:
            return error

        # Load entity data
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        entity_data = load_result.data if load_result.success else None
        if entity_data is None:
            return ErrorResult(
                errors=[f"No data found for {entity_type}"],
                suggestions=["Check entity exists and database connection"]
            )

        # For multi-cardinality entities, we might want to show multiple records
        cardinality = getattr(entity_model, 'cardinality', Cardinality.SINGLE) if entity_model else Cardinality.SINGLE
        if cardinality == Cardinality.MULTIPLE:
            # Load all records and apply filtering
            all_records = load_all_entities(entity_type, company_name, context)
            
            # Apply filters if present
            if filters:
                try:
                    filtered_records = apply_filters(all_records, filters)
                except Exception as filter_error:
                    return ErrorResult(
                        errors=[f"Filter application failed: {str(filter_error)}"],
                        suggestions=["Check filter syntax and field names"]
                    )
            else:
                filtered_records = all_records
            
            # Format multiple records
            count = len(filtered_records)
            total_count = len(all_records)
            
            message = f"Found {count} of {total_count} {entity_type} records" if filters else f"Found {count} {entity_type} records"
            
            return CommandResult(
                success=True,
                message=message,
                data={
                    "entity_type": entity_type,
                    "records": filtered_records,
                    "count": count,
                    "total_count": total_count,
                    "filtered": bool(filters)
                }
            )
        else:
            # Single record - format data for display
            specific_fields = field_names if field_names else None
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